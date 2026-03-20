#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

STATUS_PENDING = "未上线"
STATUS_RELEASED = "已上线"
VALID_STATUSES = {STATUS_PENDING, STATUS_RELEASED}

DEFAULT_DATA_ROOT = Path(
    os.environ.get(
        "BRANCH_WORKLOG_HOME",
        Path.home() / ".agents" / "data" / "branch-worklog",
    )
).expanduser()
CONTEXT_STATE_FILENAME = "ui-context.json"
BRANCH_METADATA_FILENAME = "branch-metadata.json"


class WorklogError(Exception):
    """Base exception for branch worklog operations."""


class ContextError(WorklogError):
    """Raised when Git context cannot be resolved."""


class ValidationError(WorklogError):
    """Raised when input or record data is invalid."""


class NotFoundError(WorklogError):
    """Raised when a record cannot be found."""


@dataclass
class GitContext:
    project: str
    branch: str
    repo_root: str

    def to_dict(self) -> dict[str, str]:
        return {
            "project": self.project,
            "branch": self.branch,
            "repo_root": self.repo_root,
        }


@dataclass
class Record:
    id: str
    project: str
    branch: str
    local_path: str
    status: str
    created_at: str
    updated_at: str
    summary: str
    detail_markdown: str
    feature_points: list[str]
    modified_files: list[str]
    api_changes: list[str]
    test_notes: list[str]
    remarks: list[str]
    file_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project": self.project,
            "branch": self.branch,
            "local_path": self.local_path,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "summary": self.summary,
            "detail_markdown": self.detail_markdown,
            "feature_points": self.feature_points,
            "modified_files": self.modified_files,
            "api_changes": self.api_changes,
            "test_notes": self.test_notes,
            "remarks": self.remarks,
            "file_path": self.file_path,
        }


def now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def timestamp_token() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "item"


def validate_status(status: str) -> str:
    status = status.strip()
    if status not in VALID_STATUSES:
        allowed = ", ".join(sorted(VALID_STATUSES))
        raise ValidationError(f"status must be one of: {allowed}")
    return status


def validate_non_empty(name: str, value: str) -> str:
    value = value.strip()
    if not value:
        raise ValidationError(f"{name} cannot be empty")
    return value


def normalize_local_path(local_path: str | None) -> str:
    if local_path is None:
        return ""
    candidate = local_path.strip()
    if not candidate:
        return ""
    return str(Path(candidate).expanduser())


def normalize_text_block(value: str | None) -> str:
    if value is None:
        return ""
    lines = [line.rstrip() for line in str(value).strip().splitlines()]
    return "\n".join(lines).strip()


def normalize_item_collection(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = split_multiline_items(value)
    elif isinstance(value, (list, tuple, set)):
        items = []
        for item in value:
            items.extend(split_multiline_items(str(item)))
    else:
        items = split_multiline_items(str(value))
    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = item.strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(normalized)
    return deduped


def split_multiline_items(text: str | None) -> list[str]:
    if not text:
        return []
    items: list[str] = []
    for raw_line in str(text).splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", raw_line).strip()
        if line:
            items.append(line)
    return items


def summarize_text(text: str, max_length: int = 80) -> str:
    cleaned = " ".join(split_multiline_items(text) or [normalize_text_block(text)])
    cleaned = cleaned.strip()
    if not cleaned:
        return ""
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[: max_length - 1].rstrip() + "…"


SECTION_ALIASES = {
    "feature_points": ("功能点", "功能", "变更点", "修改点", "实现内容"),
    "modified_files": ("修改文件", "文件", "改动文件", "涉及文件"),
    "api_changes": ("接口变更", "接口", "API变更", "API", "路由变更"),
    "test_notes": ("测试情况", "测试", "验证", "联调情况"),
    "remarks": ("备注", "注意事项", "风险", "说明", "待办"),
}

FILE_PATH_PATTERN = re.compile(
    r"(?P<path>[A-Za-z0-9_./\\\\-]+\.(?:py|js|ts|tsx|jsx|vue|md|json|ya?ml|css|scss|html|java|go|rs|sh|sql))"
)


def detect_section(line: str) -> tuple[str | None, str]:
    stripped = line.strip()
    for field, aliases in SECTION_ALIASES.items():
        for alias in aliases:
            match = re.match(rf"^{re.escape(alias)}\s*[:：]\s*(.*)$", stripped, re.IGNORECASE)
            if match:
                return field, match.group(1).strip()
    return None, stripped


def classify_detail_line(line: str) -> str:
    lowered = line.lower()
    if FILE_PATH_PATTERN.search(line):
        return "modified_files"
    if any(keyword in lowered for keyword in ("api", "接口", "endpoint", "route", "路由", "字段", "参数", "请求", "响应")):
        return "api_changes"
    if any(keyword in lowered for keyword in ("测试", "验证", "联调", "回归", "test", "unit", "e2e", "自测")):
        return "test_notes"
    if any(keyword in lowered for keyword in ("备注", "注意", "风险", "todo", "待办", "兼容", "说明")):
        return "remarks"
    return "feature_points"


def extract_file_paths(text: str) -> list[str]:
    matches = [match.group("path") for match in FILE_PATH_PATTERN.finditer(text)]
    return normalize_item_collection(matches)


def infer_structured_fields(summary: str, detail_markdown: str) -> dict[str, list[str]]:
    extracted = {
        "feature_points": [],
        "modified_files": [],
        "api_changes": [],
        "test_notes": [],
        "remarks": [],
    }
    current_section: str | None = None

    for raw_line in detail_markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        section, remainder = detect_section(line)
        if section:
            current_section = section
            if remainder:
                target = extracted[current_section]
                if current_section == "modified_files":
                    target.extend(extract_file_paths(remainder) or split_multiline_items(remainder))
                else:
                    target.extend(split_multiline_items(remainder) or [remainder])
            continue

        target_section = current_section or classify_detail_line(line)
        if target_section == "modified_files":
            extracted[target_section].extend(extract_file_paths(line) or split_multiline_items(line))
        else:
            extracted[target_section].extend(split_multiline_items(line) or [line])

    for field, items in extracted.items():
        extracted[field] = normalize_item_collection(items)

    if not extracted["feature_points"] and summary:
        extracted["feature_points"] = [summary]
    return extracted


def prepare_record_content(
    *,
    summary: str,
    detail_markdown: str | None = None,
    feature_points: Any = None,
    modified_files: Any = None,
    api_changes: Any = None,
    test_notes: Any = None,
    remarks: Any = None,
) -> dict[str, Any]:
    normalized_summary = normalize_text_block(summary)
    normalized_detail = normalize_text_block(detail_markdown)

    if not normalized_summary and normalized_detail:
        normalized_summary = summarize_text(normalized_detail)
    if not normalized_detail and normalized_summary:
        normalized_detail = normalized_summary
    if not normalized_summary and not normalized_detail:
        raise ValidationError("summary or detail_markdown cannot be empty")

    provided = {
        "feature_points": normalize_item_collection(feature_points),
        "modified_files": normalize_item_collection(modified_files),
        "api_changes": normalize_item_collection(api_changes),
        "test_notes": normalize_item_collection(test_notes),
        "remarks": normalize_item_collection(remarks),
    }

    if not any(provided.values()):
        provided = infer_structured_fields(normalized_summary, normalized_detail)
        provided["api_changes"] = []
        provided["test_notes"] = []
    elif not provided["feature_points"] and normalized_summary:
        provided["feature_points"] = [normalized_summary]

    return {
        "summary": normalized_summary,
        "detail_markdown": normalized_detail,
        **provided,
    }


def resolve_data_root(data_root: str | Path | None = None) -> Path:
    root = Path(data_root) if data_root else DEFAULT_DATA_ROOT
    records_dir = root / "records"
    records_dir.mkdir(parents=True, exist_ok=True)
    return root


def context_state_path(data_root: str | Path | None = None) -> Path:
    return resolve_data_root(data_root) / CONTEXT_STATE_FILENAME


def branch_metadata_path(data_root: str | Path | None = None) -> Path:
    return resolve_data_root(data_root) / BRANCH_METADATA_FILENAME


def branch_group_key(project: str, branch: str) -> str:
    return f"{project}||{branch}"


def infer_branch_release_status(
    project: str,
    branch: str,
    data_root: str | Path | None = None,
) -> str:
    records, _ = list_records(
        data_root,
        project=project,
        branch=branch,
    )
    if not records:
        return STATUS_PENDING
    latest = records[0]
    try:
        return validate_status(latest.status)
    except ValidationError:
        return STATUS_PENDING


def get_branch_metadata_entry(
    project: str,
    branch: str,
    data_root: str | Path | None = None,
) -> dict[str, Any]:
    validated_project = validate_non_empty("project", project)
    validated_branch = validate_non_empty("branch", branch)
    metadata = read_branch_metadata(data_root)
    key = branch_group_key(validated_project, validated_branch)
    current = metadata.get(key, {})
    release_status = current.get("release_status")
    if release_status not in VALID_STATUSES:
        release_status = infer_branch_release_status(validated_project, validated_branch, data_root)
    return {
        "project": validated_project,
        "branch": validated_branch,
        "release_status": release_status,
        "archived": bool(current.get("archived", False)),
        "archived_at": current.get("archived_at"),
    }


def read_branch_metadata(data_root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    path = branch_metadata_path(data_root)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): value for key, value in payload.items() if isinstance(value, dict)}


def write_branch_metadata(metadata: dict[str, dict[str, Any]], data_root: str | Path | None = None) -> None:
    path = branch_metadata_path(data_root)
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def set_branch_archived(
    *,
    project: str,
    branch: str,
    archived: bool,
    data_root: str | Path | None = None,
) -> dict[str, Any]:
    current = get_branch_metadata_entry(project, branch, data_root)
    existing_records, _ = list_records(
        data_root,
        project=current["project"],
        branch=current["branch"],
    )
    if not existing_records:
        raise NotFoundError(f"no records found for project={current['project']}, branch={current['branch']}")
    if archived and current["release_status"] != STATUS_RELEASED:
        raise ValidationError("only released branches can be archived")

    metadata = read_branch_metadata(data_root)
    key = branch_group_key(current["project"], current["branch"])
    current["archived"] = bool(archived)
    current["archived_at"] = now_iso() if archived else None
    metadata[key] = current
    write_branch_metadata(metadata, data_root)
    return current


def set_branch_release_status(
    *,
    project: str,
    branch: str,
    release_status: str,
    data_root: str | Path | None = None,
) -> dict[str, Any]:
    validated_status = validate_status(release_status)
    current = get_branch_metadata_entry(project, branch, data_root)
    existing_records, _ = list_records(
        data_root,
        project=current["project"],
        branch=current["branch"],
    )
    if not existing_records:
        raise NotFoundError(f"no records found for project={current['project']}, branch={current['branch']}")

    metadata = read_branch_metadata(data_root)
    key = branch_group_key(current["project"], current["branch"])
    current["release_status"] = validated_status
    if validated_status != STATUS_RELEASED:
        current["archived"] = False
        current["archived_at"] = None
    metadata[key] = current
    write_branch_metadata(metadata, data_root)
    return current


def records_root(data_root: str | Path | None = None) -> Path:
    return resolve_data_root(data_root) / "records"


def project_dir(project: str, data_root: str | Path | None = None) -> Path:
    return records_root(data_root) / slugify(project)


def run_git(args: list[str], cwd: str | Path | None = None) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "git command failed"
        raise ContextError(message)
    return completed.stdout.strip()


def detect_git_context(cwd: str | Path | None = None) -> GitContext:
    try:
        repo_root = run_git(["rev-parse", "--show-toplevel"], cwd=cwd)
        branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    except FileNotFoundError as exc:
        raise ContextError("git is not available on PATH") from exc
    if not repo_root:
        raise ContextError("failed to resolve repository root")
    if not branch or branch == "HEAD":
        raise ContextError("detached HEAD is not supported for implicit branch tracking")
    project = Path(repo_root).name
    return GitContext(project=project, branch=branch, repo_root=repo_root)


def resolve_project_and_branch(
    project: str | None = None,
    branch: str | None = None,
    cwd: str | Path | None = None,
) -> tuple[str, str, GitContext | None]:
    resolved_project = project.strip() if project else ""
    resolved_branch = branch.strip() if branch else ""
    context: GitContext | None = None
    if not resolved_project or not resolved_branch:
        context = detect_git_context(cwd)
        resolved_project = resolved_project or context.project
        resolved_branch = resolved_branch or context.branch
    return (
        validate_non_empty("project", resolved_project),
        validate_non_empty("branch", resolved_branch),
        context,
    )


def build_record_id(branch: str) -> str:
    return f"{timestamp_token()}-{slugify(branch)}-{uuid4().hex[:6]}"


def record_path_for(project: str, record_id: str, data_root: str | Path | None = None) -> Path:
    target_dir = project_dir(project, data_root)
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"{record_id}.md"


def serialize_record(record: Record) -> str:
    lines = [
        "---",
        f'id: {json.dumps(record.id, ensure_ascii=False)}',
        f'project: {json.dumps(record.project, ensure_ascii=False)}',
        f'branch: {json.dumps(record.branch, ensure_ascii=False)}',
        f'local_path: {json.dumps(record.local_path, ensure_ascii=False)}',
        f'status: {json.dumps(record.status, ensure_ascii=False)}',
        f'created_at: {json.dumps(record.created_at, ensure_ascii=False)}',
        f'updated_at: {json.dumps(record.updated_at, ensure_ascii=False)}',
        f'summary: {json.dumps(record.summary, ensure_ascii=False)}',
        f'feature_points: {json.dumps(record.feature_points, ensure_ascii=False)}',
        f'modified_files: {json.dumps(record.modified_files, ensure_ascii=False)}',
        f'api_changes: {json.dumps(record.api_changes, ensure_ascii=False)}',
        f'test_notes: {json.dumps(record.test_notes, ensure_ascii=False)}',
        f'remarks: {json.dumps(record.remarks, ensure_ascii=False)}',
        "---",
    ]
    detail_markdown = record.detail_markdown.rstrip()
    if detail_markdown:
        lines.append(detail_markdown)
    return "\n".join(lines) + "\n"


def parse_frontmatter_value(raw_value: str) -> Any:
    raw_value = raw_value.strip()
    if not raw_value:
        return ""
    if raw_value.startswith('"') or raw_value.startswith("[") or raw_value.startswith("{"):
        return json.loads(raw_value)
    return raw_value.strip("'")


def load_record(path: str | Path) -> Record:
    raw_text = Path(path).read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", raw_text, re.DOTALL)
    if not match:
        raise ValidationError(f"invalid frontmatter in {path}")

    frontmatter_text, body = match.groups()
    data: dict[str, Any] = {}
    for raw_line in frontmatter_text.splitlines():
        if not raw_line.strip():
            continue
        if ":" not in raw_line:
            raise ValidationError(f"invalid frontmatter line in {path}: {raw_line}")
        key, value = raw_line.split(":", 1)
        data[key.strip()] = parse_frontmatter_value(value)

    required_keys = {"id", "project", "branch", "status", "created_at", "updated_at"}
    missing = required_keys - set(data)
    if missing:
        raise ValidationError(f"missing keys in {path}: {', '.join(sorted(missing))}")

    status = validate_status(str(data["status"]))
    detail_markdown = normalize_text_block(body)
    summary = normalize_text_block(str(data.get("summary", ""))) or summarize_text(detail_markdown)
    if not detail_markdown:
        detail_markdown = summary
    structured = prepare_record_content(
        summary=summary,
        detail_markdown=detail_markdown,
        feature_points=data.get("feature_points"),
        modified_files=data.get("modified_files"),
        api_changes=data.get("api_changes"),
        test_notes=data.get("test_notes"),
        remarks=data.get("remarks"),
    )
    record = Record(
        id=validate_non_empty("id", str(data["id"])),
        project=validate_non_empty("project", str(data["project"])),
        branch=validate_non_empty("branch", str(data["branch"])),
        local_path=normalize_local_path(str(data.get("local_path", ""))),
        status=status,
        created_at=validate_non_empty("created_at", str(data["created_at"])),
        updated_at=validate_non_empty("updated_at", str(data["updated_at"])),
        summary=structured["summary"],
        detail_markdown=structured["detail_markdown"],
        feature_points=structured["feature_points"],
        modified_files=structured["modified_files"],
        api_changes=structured["api_changes"],
        test_notes=structured["test_notes"],
        remarks=structured["remarks"],
        file_path=str(Path(path).resolve()),
    )
    return record


def write_record(record: Record, data_root: str | Path | None = None) -> Record:
    target_path = record_path_for(record.project, record.id, data_root)
    temporary_path = target_path.with_suffix(".tmp")
    temporary_path.write_text(serialize_record(record), encoding="utf-8")
    temporary_path.replace(target_path)
    record.file_path = str(target_path.resolve())
    return record


def delete_record_file(path: str | Path) -> None:
    record_path = Path(path)
    if record_path.exists():
        record_path.unlink()


def parse_iso(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"invalid ISO timestamp: {value}") from exc


def sort_records(records: list[Record]) -> list[Record]:
    return sorted(
        records,
        key=lambda record: (parse_iso(record.updated_at), parse_iso(record.created_at), record.id),
        reverse=True,
    )


def iter_record_paths(data_root: str | Path | None = None) -> list[Path]:
    root = records_root(data_root)
    if not root.exists():
        return []
    return sorted(root.glob("*/*.md"))


def list_records(
    data_root: str | Path | None = None,
    *,
    project: str | None = None,
    branch: str | None = None,
    status: str | None = None,
    query: str | None = None,
) -> tuple[list[Record], list[dict[str, str]]]:
    filtered_project = project.strip() if project else ""
    filtered_branch = branch.strip() if branch else ""
    filtered_status = status.strip() if status else ""
    lowered_query = query.strip().lower() if query else ""

    records: list[Record] = []
    errors: list[dict[str, str]] = []

    for path in iter_record_paths(data_root):
        try:
            record = load_record(path)
        except WorklogError as exc:
            errors.append({"path": str(path.resolve()), "error": str(exc)})
            continue

        if filtered_project and record.project != filtered_project:
            continue
        if filtered_branch and record.branch != filtered_branch:
            continue
        if filtered_status and record.status != filtered_status:
            continue
        if lowered_query:
            haystack = "\n".join(
                [
                    record.project,
                    record.branch,
                    record.local_path,
                    record.status,
                    record.summary,
                    record.detail_markdown,
                    "\n".join(record.feature_points),
                    "\n".join(record.modified_files),
                    "\n".join(record.api_changes),
                    "\n".join(record.test_notes),
                    "\n".join(record.remarks),
                ]
            ).lower()
            if lowered_query not in haystack:
                continue

        records.append(record)

    return sort_records(records), errors


def get_record(record_id: str, data_root: str | Path | None = None) -> Record:
    target_id = validate_non_empty("record_id", record_id)
    records, _ = list_records(data_root)
    for record in records:
        if record.id == target_id:
            return record
    raise NotFoundError(f"record not found: {target_id}")


def find_latest_record(
    project: str,
    branch: str,
    *,
    status: str | None = None,
    data_root: str | Path | None = None,
) -> Record:
    records, _ = list_records(
        data_root,
        project=project,
        branch=branch,
        status=status,
    )
    if not records:
        raise NotFoundError(f"no record found for project={project}, branch={branch}")
    return records[0]


def create_record(
    *,
    project: str,
    branch: str,
    local_path: str = "",
    summary: str,
    detail_markdown: str | None = None,
    feature_points: Any = None,
    modified_files: Any = None,
    api_changes: Any = None,
    test_notes: Any = None,
    remarks: Any = None,
    status: str = STATUS_PENDING,
    data_root: str | Path | None = None,
) -> Record:
    validated_project = validate_non_empty("project", project)
    validated_branch = validate_non_empty("branch", branch)
    normalized_local_path = normalize_local_path(local_path)
    validated_status = validate_status(status)
    prepared = prepare_record_content(
        summary=summary,
        detail_markdown=detail_markdown,
        feature_points=feature_points,
        modified_files=modified_files,
        api_changes=api_changes,
        test_notes=test_notes,
        remarks=remarks,
    )
    created_at = now_iso()
    record = Record(
        id=build_record_id(validated_branch),
        project=validated_project,
        branch=validated_branch,
        local_path=normalized_local_path,
        status=validated_status,
        created_at=created_at,
        updated_at=created_at,
        summary=prepared["summary"],
        detail_markdown=prepared["detail_markdown"],
        feature_points=prepared["feature_points"],
        modified_files=prepared["modified_files"],
        api_changes=prepared["api_changes"],
        test_notes=prepared["test_notes"],
        remarks=prepared["remarks"],
    )
    return write_record(record, data_root)


def append_branch_change(
    *,
    project: str,
    branch: str,
    local_path: str = "",
    summary: str,
    detail_markdown: str | None = None,
    feature_points: Any = None,
    modified_files: Any = None,
    api_changes: Any = None,
    test_notes: Any = None,
    remarks: Any = None,
    status: str = STATUS_PENDING,
    data_root: str | Path | None = None,
) -> tuple[str, Record]:
    validated_project = validate_non_empty("project", project)
    validated_branch = validate_non_empty("branch", branch)
    normalized_local_path = normalize_local_path(local_path)
    validated_status = validate_status(status)
    prepared = prepare_record_content(
        summary=summary,
        detail_markdown=detail_markdown,
        feature_points=feature_points,
        modified_files=modified_files,
        api_changes=api_changes,
        test_notes=test_notes,
        remarks=remarks,
    )

    try:
        latest = find_latest_record(
            project=validated_project,
            branch=validated_branch,
            data_root=data_root,
        )
    except NotFoundError:
        return "created", create_record(
            project=validated_project,
            branch=validated_branch,
            local_path=normalized_local_path,
            summary=prepared["summary"],
            detail_markdown=prepared["detail_markdown"],
            feature_points=prepared["feature_points"],
            modified_files=prepared["modified_files"],
            api_changes=prepared["api_changes"],
            test_notes=prepared["test_notes"],
            remarks=prepared["remarks"],
            status=validated_status,
            data_root=data_root,
        )

    if (
        latest.summary == prepared["summary"]
        and latest.status == validated_status
        and normalize_local_path(latest.local_path) == normalized_local_path
        and latest.detail_markdown == prepared["detail_markdown"]
        and latest.feature_points == prepared["feature_points"]
        and latest.modified_files == prepared["modified_files"]
        and latest.api_changes == prepared["api_changes"]
        and latest.test_notes == prepared["test_notes"]
        and latest.remarks == prepared["remarks"]
    ):
        return "unchanged", latest

    return "created", create_record(
        project=validated_project,
        branch=validated_branch,
        local_path=normalized_local_path,
        summary=prepared["summary"],
        detail_markdown=prepared["detail_markdown"],
        feature_points=prepared["feature_points"],
        modified_files=prepared["modified_files"],
        api_changes=prepared["api_changes"],
        test_notes=prepared["test_notes"],
        remarks=prepared["remarks"],
        status=validated_status,
        data_root=data_root,
    )


def update_record(
    record_id: str,
    *,
    project: str | None = None,
    branch: str | None = None,
    local_path: str | None = None,
    summary: str | None = None,
    detail_markdown: str | None = None,
    feature_points: Any = None,
    modified_files: Any = None,
    api_changes: Any = None,
    test_notes: Any = None,
    remarks: Any = None,
    status: str | None = None,
    data_root: str | Path | None = None,
) -> Record:
    record = get_record(record_id, data_root)
    old_path = Path(record.file_path) if record.file_path else None

    if project is not None:
        record.project = validate_non_empty("project", project)
    if branch is not None:
        record.branch = validate_non_empty("branch", branch)
    if local_path is not None:
        record.local_path = normalize_local_path(local_path)
    if (
        summary is not None
        or detail_markdown is not None
        or feature_points is not None
        or modified_files is not None
        or api_changes is not None
        or test_notes is not None
        or remarks is not None
    ):
        prepared = prepare_record_content(
            summary=summary if summary is not None else record.summary,
            detail_markdown=detail_markdown if detail_markdown is not None else record.detail_markdown,
            feature_points=feature_points if feature_points is not None else record.feature_points,
            modified_files=modified_files if modified_files is not None else record.modified_files,
            api_changes=api_changes if api_changes is not None else record.api_changes,
            test_notes=test_notes if test_notes is not None else record.test_notes,
            remarks=remarks if remarks is not None else record.remarks,
        )
        record.summary = prepared["summary"]
        record.detail_markdown = prepared["detail_markdown"]
        record.feature_points = prepared["feature_points"]
        record.modified_files = prepared["modified_files"]
        record.api_changes = prepared["api_changes"]
        record.test_notes = prepared["test_notes"]
        record.remarks = prepared["remarks"]
    if status is not None:
        record.status = validate_status(status)

    record.updated_at = now_iso()
    updated_record = write_record(record, data_root)

    if old_path and old_path.resolve() != Path(updated_record.file_path).resolve():
        delete_record_file(old_path)
    return updated_record


def upsert_branch_record(
    *,
    project: str,
    branch: str,
    local_path: str = "",
    summary: str,
    detail_markdown: str | None = None,
    feature_points: Any = None,
    modified_files: Any = None,
    api_changes: Any = None,
    test_notes: Any = None,
    remarks: Any = None,
    status: str = STATUS_PENDING,
    data_root: str | Path | None = None,
) -> tuple[str, Record]:
    validated_status = validate_status(status)
    if validated_status != STATUS_PENDING:
        raise ValidationError("upsert only supports the default 未上线 state")
    return append_branch_change(
        project=project,
        branch=branch,
        local_path=local_path,
        summary=summary,
        detail_markdown=detail_markdown,
        feature_points=feature_points,
        modified_files=modified_files,
        api_changes=api_changes,
        test_notes=test_notes,
        remarks=remarks,
        status=validated_status,
        data_root=data_root,
    )


def update_status_by_branch(
    *,
    project: str,
    branch: str,
    status: str,
    data_root: str | Path | None = None,
) -> tuple[str, dict[str, Any]]:
    current = get_branch_metadata_entry(project, branch, data_root)
    validated_status = validate_status(status)
    if current["release_status"] == validated_status:
        return "unchanged", current
    updated = set_branch_release_status(
        project=current["project"],
        branch=current["branch"],
        release_status=validated_status,
        data_root=data_root,
    )
    return "updated", updated


def delete_record(record_id: str, data_root: str | Path | None = None) -> Record:
    record = get_record(record_id, data_root)
    if record.file_path:
        delete_record_file(record.file_path)
    return record


def delete_branch_records(
    *,
    project: str,
    branch: str,
    data_root: str | Path | None = None,
) -> list[Record]:
    validated_project = validate_non_empty("project", project)
    validated_branch = validate_non_empty("branch", branch)
    records, _ = list_records(
        data_root,
        project=validated_project,
        branch=validated_branch,
    )
    if not records:
        raise NotFoundError(f"no records found for project={validated_project}, branch={validated_branch}")

    for record in records:
        if record.file_path:
            delete_record_file(record.file_path)
    return records


def record_counts(records: list[Record]) -> dict[str, int]:
    projects = {record.project for record in records}
    return {
        "total": len(records),
        "未上线": sum(1 for record in records if record.status == STATUS_PENDING),
        "已上线": sum(1 for record in records if record.status == STATUS_RELEASED),
        "projects": len(projects),
    }


def project_counts(data_root: str | Path | None = None) -> list[dict[str, Any]]:
    groups = list_branch_groups(data_root)
    counts: dict[str, dict[str, Any]] = {}
    for group in groups:
        project = counts.setdefault(
            group["project"],
            {
                "project": group["project"],
                "total": 0,
                STATUS_PENDING: 0,
                STATUS_RELEASED: 0,
                "latest_updated_at": group["latest_updated_at"],
            },
        )
        project["total"] += 1
        project[group["release_status"]] += 1
        if group["latest_updated_at"] > project["latest_updated_at"]:
            project["latest_updated_at"] = group["latest_updated_at"]

    return sorted(
        counts.values(),
        key=lambda item: (item["latest_updated_at"], item["project"]),
        reverse=True,
    )


def list_branch_groups(
    data_root: str | Path | None = None,
    *,
    project: str | None = None,
    branch: str | None = None,
    status: str | None = None,
    query: str | None = None,
    include_archived: bool = False,
    archived_only: bool = False,
) -> list[dict[str, Any]]:
    records, _ = list_records(data_root, query=query)
    metadata = read_branch_metadata(data_root)
    grouped: dict[tuple[str, str], list[Record]] = {}
    for record in records:
        key = (record.project, record.branch)
        grouped.setdefault(key, []).append(record)

    groups: list[dict[str, Any]] = []
    filtered_project = project.strip() if project else ""
    filtered_branch = branch.strip() if branch else ""
    filtered_status = status.strip() if status else ""

    for (record_project, record_branch), timeline in grouped.items():
        latest = timeline[0]
        branch_meta = get_branch_metadata_entry(record_project, record_branch, data_root)
        is_archived = bool(branch_meta.get("archived", False))
        if filtered_project and record_project != filtered_project:
            continue
        if filtered_branch and record_branch != filtered_branch:
            continue
        if filtered_status and branch_meta["release_status"] != filtered_status:
            continue
        if archived_only and not is_archived:
            continue
        if not archived_only and not include_archived and is_archived:
            continue

        groups.append(
            {
                "group_id": branch_group_key(record_project, record_branch),
                "project": record_project,
                "branch": record_branch,
                "release_status": branch_meta["release_status"],
                "latest_summary": latest.summary,
                "latest_local_path": latest.local_path,
                "latest_updated_at": latest.updated_at,
                "latest_created_at": latest.created_at,
                "archived": is_archived,
                "archived_at": branch_meta.get("archived_at"),
                "entries_count": len(timeline),
                "timeline": [item.to_dict() for item in timeline],
            }
        )

    return sorted(
        groups,
        key=lambda item: (parse_iso(item["latest_updated_at"]), item["project"], item["branch"]),
        reverse=True,
    )


def branch_counts(data_root: str | Path | None = None) -> dict[str, int]:
    groups = list_branch_groups(data_root)
    archived_groups = list_branch_groups(data_root, archived_only=True)
    return {
        "total": len(groups),
        "released": sum(1 for group in groups if group["release_status"] == STATUS_RELEASED),
        "pending": sum(1 for group in groups if group["release_status"] == STATUS_PENDING),
        "archived": len(archived_groups),
        "projects": len({group["project"] for group in groups}),
    }


def safe_context(cwd: str | Path | None = None) -> dict[str, Any]:
    try:
        context = detect_git_context(cwd)
    except ContextError as exc:
        return {"available": False, "error": str(exc), "context": None}
    return {"available": True, "error": None, "context": context.to_dict()}


def write_context_snapshot(cwd: str | Path | None = None, data_root: str | Path | None = None) -> dict[str, Any]:
    snapshot = safe_context(cwd)
    snapshot["cwd"] = str(Path(cwd).resolve()) if cwd else str(Path.cwd().resolve())
    path = context_state_path(data_root)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return snapshot


def read_context_snapshot(
    data_root: str | Path | None = None,
    fallback_cwd: str | Path | None = None,
) -> dict[str, Any]:
    path = context_state_path(data_root)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return write_context_snapshot(fallback_cwd, data_root)
