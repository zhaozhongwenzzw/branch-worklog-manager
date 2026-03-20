#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import webbrowser
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from branch_worklog_lib import (
    DEFAULT_DATA_ROOT,
    STATUS_PENDING,
    append_branch_change,
    branch_counts,
    ContextError,
    NotFoundError,
    set_branch_release_status,
    set_branch_archived,
    ValidationError,
    create_record,
    delete_branch_records,
    delete_record,
    get_record,
    list_branch_groups,
    list_records,
    project_counts,
    read_context_snapshot,
    record_counts,
    resolve_data_root,
    update_record,
    write_context_snapshot,
)


class BranchWorklogHandler(BaseHTTPRequestHandler):
    server_version = "BranchWorklogServer/1.0"

    def __init__(self, *args, data_root: Path, static_dir: Path, context_cwd: str, **kwargs):
        self.data_root = data_root
        self.static_dir = static_dir
        self.context_cwd = context_cwd
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/"):
                self.handle_api_get(parsed)
                return
            self.serve_static(parsed.path)
        except Exception as exc:  # pragma: no cover
            self.write_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": str(exc)},
            )

    def do_POST(self) -> None:
        self.dispatch_api_write("POST")

    def do_PUT(self) -> None:
        self.dispatch_api_write("PUT")

    def do_PATCH(self) -> None:
        self.dispatch_api_write("PATCH")

    def do_DELETE(self) -> None:
        self.dispatch_api_write("DELETE")

    def dispatch_api_write(self, method: str) -> None:
        try:
            parsed = urlparse(self.path)
            if not parsed.path.startswith("/api/"):
                self.write_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
                return
            body = self.read_json_body() if method in {"POST", "PUT", "PATCH", "DELETE"} else {}
            self.handle_api_write(method, parsed.path, body)
        except (ValidationError, ContextError) as exc:
            self.write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
        except NotFoundError as exc:
            self.write_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": str(exc)})
        except Exception as exc:  # pragma: no cover
            self.write_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": str(exc)},
            )

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        return

    def read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw_body = self.rfile.read(length)
        if not raw_body:
            return {}
        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValidationError("request body must be valid JSON") from exc

    def handle_api_get(self, parsed) -> None:
        if parsed.path == "/api/context":
            snapshot = read_context_snapshot(self.data_root, self.context_cwd)
            self.write_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "data_root": str(self.data_root),
                    "git": {
                        "available": snapshot.get("available", False),
                        "error": snapshot.get("error"),
                        "context": snapshot.get("context"),
                    },
                    "cwd": snapshot.get("cwd"),
                },
            )
            return

        if parsed.path == "/api/projects":
            self.write_json(
                HTTPStatus.OK,
                {"ok": True, "projects": project_counts(self.data_root)},
            )
            return

        if parsed.path == "/api/branches":
            params = parse_qs(parsed.query)
            query = first_query_value(params, "q")
            project = first_query_value(params, "project")
            status = first_query_value(params, "status")
            branch = first_query_value(params, "branch")
            groups = list_branch_groups(
                self.data_root,
                project=project,
                branch=branch,
                status=None if status == "all" else status,
                query=query,
            )
            self.write_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "branches": groups,
                    "projects": project_counts(self.data_root),
                    "counts": branch_counts(self.data_root),
                },
            )
            return

        if parsed.path == "/api/archived-branches":
            params = parse_qs(parsed.query)
            query = first_query_value(params, "q")
            project = first_query_value(params, "project")
            branch = first_query_value(params, "branch")
            groups = list_branch_groups(
                self.data_root,
                project=project,
                branch=branch,
                query=query,
                archived_only=True,
            )
            self.write_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "branches": groups,
                },
            )
            return

        if parsed.path == "/api/records":
            params = parse_qs(parsed.query)
            query = first_query_value(params, "q")
            project = first_query_value(params, "project")
            status = first_query_value(params, "status")
            branch = first_query_value(params, "branch")
            records, errors = list_records(
                self.data_root,
                project=project,
                branch=branch,
                status=None if status == "all" else status,
                query=query,
            )
            self.write_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "records": [record.to_dict() for record in records],
                    "projects": project_counts(self.data_root),
                    "counts": record_counts(records),
                    "errors": errors,
                },
            )
            return

        if parsed.path.startswith("/api/records/"):
            record_id = parsed.path.removeprefix("/api/records/")
            if "/" in record_id:
                self.write_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
                return
            record = get_record(record_id, self.data_root)
            self.write_json(HTTPStatus.OK, {"ok": True, "record": record.to_dict()})
            return

        self.write_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})

    def handle_api_write(self, method: str, path: str, body: dict) -> None:
        if method == "POST" and path == "/api/records":
            action, record = append_branch_change(
                project=body.get("project", ""),
                branch=body.get("branch", ""),
                local_path=body.get("local_path", ""),
                summary=body.get("summary", ""),
                detail_markdown=body.get("detail_markdown"),
                feature_points=body.get("feature_points"),
                modified_files=body.get("modified_files"),
                api_changes=body.get("api_changes"),
                test_notes=body.get("test_notes"),
                remarks=body.get("remarks"),
                status=body.get("status", STATUS_PENDING),
                data_root=self.data_root,
            )
            status_code = HTTPStatus.CREATED if action == "created" else HTTPStatus.OK
            self.write_json(status_code, {"ok": True, "action": action, "record": record.to_dict()})
            return

        if path.startswith("/api/records/") and method == "PUT":
            record_id = path.removeprefix("/api/records/")
            record = update_record(
                record_id,
                project=body.get("project"),
                branch=body.get("branch"),
                local_path=body.get("local_path"),
                summary=body.get("summary"),
                detail_markdown=body.get("detail_markdown"),
                feature_points=body.get("feature_points"),
                modified_files=body.get("modified_files"),
                api_changes=body.get("api_changes"),
                test_notes=body.get("test_notes"),
                remarks=body.get("remarks"),
                status=body.get("status"),
                data_root=self.data_root,
            )
            self.write_json(HTTPStatus.OK, {"ok": True, "record": record.to_dict()})
            return

        if path.startswith("/api/records/") and path.endswith("/status") and method == "PATCH":
            record_id = path.removeprefix("/api/records/").removesuffix("/status")
            existing = get_record(record_id, self.data_root)
            action, record = append_branch_change(
                project=existing.project,
                branch=existing.branch,
                local_path=existing.local_path,
                summary=existing.summary,
                status=body.get("status"),
                data_root=self.data_root,
            )
            self.write_json(HTTPStatus.OK, {"ok": True, "action": action, "record": record.to_dict()})
            return

        if path.startswith("/api/records/") and method == "DELETE":
            record_id = path.removeprefix("/api/records/")
            record = delete_record(record_id, self.data_root)
            self.write_json(HTTPStatus.OK, {"ok": True, "record": record.to_dict()})
            return

        if path == "/api/branches" and method == "DELETE":
            project = body.get("project", "")
            branch = body.get("branch", "")
            records = delete_branch_records(
                project=project,
                branch=branch,
                data_root=self.data_root,
            )
            self.write_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "deleted_count": len(records),
                    "project": project,
                    "branch": branch,
                },
            )
            return

        if path == "/api/branches/archive" and method == "PATCH":
            project = body.get("project", "")
            branch = body.get("branch", "")
            archived = bool(body.get("archived", True))
            metadata = set_branch_archived(
                project=project,
                branch=branch,
                archived=archived,
                data_root=self.data_root,
            )
            self.write_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "branch": metadata,
                },
            )
            return

        if path == "/api/branches/release-status" and method == "PATCH":
            project = body.get("project", "")
            branch = body.get("branch", "")
            release_status = body.get("release_status", "")
            metadata = set_branch_release_status(
                project=project,
                branch=branch,
                release_status=release_status,
                data_root=self.data_root,
            )
            self.write_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "branch": metadata,
                },
            )
            return

        self.write_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})

    def serve_static(self, request_path: str) -> None:
        target = request_path or "/"
        if target == "/":
            target = "/index.html"
        static_path = (self.static_dir / target.lstrip("/")).resolve()
        if self.static_dir.resolve() not in static_path.parents and static_path != self.static_dir.resolve():
            self.write_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
            return
        if not static_path.exists() or not static_path.is_file():
            self.write_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
            return

        content_type, _ = mimetypes.guess_type(str(static_path))
        payload = static_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def write_json(self, status: HTTPStatus, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def first_query_value(params: dict[str, list[str]], key: str) -> str | None:
    values = params.get(key)
    if not values:
        return None
    value = values[0].strip()
    return value or None


def run_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    data_root: str | Path | None = None,
    static_dir: str | Path | None = None,
    context_cwd: str | Path | None = None,
    open_browser: bool = False,
) -> tuple[ThreadingHTTPServer, str]:
    resolved_data_root = resolve_data_root(data_root)
    resolved_static_dir = Path(static_dir) if static_dir else Path(__file__).resolve().parent.parent / "assets" / "web"
    resolved_context_cwd = str(Path(context_cwd).resolve()) if context_cwd else str(Path.cwd().resolve())
    write_context_snapshot(resolved_context_cwd, resolved_data_root)

    handler = partial(
        BranchWorklogHandler,
        data_root=resolved_data_root,
        static_dir=resolved_static_dir,
        context_cwd=resolved_context_cwd,
    )
    httpd = ThreadingHTTPServer((host, port), handler)
    actual_host, actual_port = httpd.server_address[:2]
    url = f"http://{actual_host}:{actual_port}"
    if open_browser:
        webbrowser.open(url)
    return httpd, url


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the branch worklog local server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--static-dir", default="")
    parser.add_argument("--context-cwd", default=str(Path.cwd()))
    parser.add_argument("--open-browser", action="store_true")
    args = parser.parse_args()

    server, url = run_server(
        host=args.host,
        port=args.port,
        data_root=args.data_root,
        static_dir=args.static_dir or None,
        context_cwd=args.context_cwd,
        open_browser=args.open_browser,
    )
    print(json.dumps({"ok": True, "url": url, "data_root": str(resolve_data_root(args.data_root))}, ensure_ascii=False))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
