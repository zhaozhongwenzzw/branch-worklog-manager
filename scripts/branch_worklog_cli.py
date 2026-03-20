#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from branch_worklog_lib import (
    DEFAULT_DATA_ROOT,
    STATUS_PENDING,
    VALID_STATUSES,
    append_branch_change,
    ContextError,
    delete_branch_records,
    set_branch_archived,
    set_branch_release_status,
    NotFoundError,
    ValidationError,
    create_record,
    delete_record,
    get_record,
    list_records,
    resolve_project_and_branch,
    safe_context,
    update_record,
    update_status_by_branch,
    upsert_branch_record,
)
from branch_worklog_server import run_server
from branch_worklog_ui_launcher import DEFAULT_PORT, ensure_ui


def emit(payload: dict, exit_code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


def collect_detail_args(args: argparse.Namespace) -> dict:
    return {
        "detail_markdown": getattr(args, "detail_markdown", None),
        "feature_points": getattr(args, "feature_points", None),
        "modified_files": getattr(args, "modified_files", None),
        "api_changes": getattr(args, "api_changes", None),
        "test_notes": getattr(args, "test_notes", None),
        "remarks": getattr(args, "remarks", None),
    }


def handle_add(args: argparse.Namespace) -> None:
    project, branch, context = resolve_project_and_branch(args.project, args.branch, args.cwd)
    action, record = upsert_branch_record(
        project=project,
        branch=branch,
        local_path=args.local_path or (context.repo_root if context else ""),
        summary=args.summary,
        **collect_detail_args(args),
        status=STATUS_PENDING,
        data_root=args.data_root,
    )
    emit(
        {
            "ok": True,
            "action": action,
            "record": record.to_dict(),
            "git_context": context.to_dict() if context else None,
        }
    )


def handle_create(args: argparse.Namespace) -> None:
    project, branch, context = resolve_project_and_branch(args.project, args.branch, args.cwd)
    action, record = append_branch_change(
        project=project,
        branch=branch,
        local_path=args.local_path or (context.repo_root if context else ""),
        summary=args.summary,
        **collect_detail_args(args),
        status=args.status,
        data_root=args.data_root,
    )
    emit(
        {
            "ok": True,
            "action": action,
            "record": record.to_dict(),
            "git_context": context.to_dict() if context else None,
        }
    )


def handle_update_status(args: argparse.Namespace) -> None:
    project, branch, context = resolve_project_and_branch(args.project, args.branch, args.cwd)
    action, branch_meta = update_status_by_branch(
        project=project,
        branch=branch,
        status=args.status,
        data_root=args.data_root,
    )
    emit(
        {
            "ok": True,
            "action": action,
            "branch": branch_meta,
            "git_context": context.to_dict() if context else None,
        }
    )


def handle_list(args: argparse.Namespace) -> None:
    records, errors = list_records(
        args.data_root,
        project=args.project,
        branch=args.branch,
        status=None if args.status == "all" else args.status,
        query=args.query,
    )
    emit(
        {
            "ok": True,
            "records": [record.to_dict() for record in records],
            "errors": errors,
            "count": len(records),
        }
    )


def handle_get(args: argparse.Namespace) -> None:
    record = get_record(args.record_id, args.data_root)
    emit({"ok": True, "record": record.to_dict()})


def handle_update(args: argparse.Namespace) -> None:
    record = update_record(
        args.record_id,
        project=args.project,
        branch=args.branch,
        local_path=args.local_path,
        summary=args.summary,
        **collect_detail_args(args),
        status=args.status,
        data_root=args.data_root,
    )
    emit({"ok": True, "action": "updated", "record": record.to_dict()})


def handle_delete(args: argparse.Namespace) -> None:
    record = delete_record(args.record_id, args.data_root)
    emit({"ok": True, "action": "deleted", "record": record.to_dict()})


def handle_delete_branch(args: argparse.Namespace) -> None:
    project, branch, context = resolve_project_and_branch(args.project, args.branch, args.cwd)
    records = delete_branch_records(
        project=project,
        branch=branch,
        data_root=args.data_root,
    )
    emit(
        {
            "ok": True,
            "action": "deleted_branch",
            "deleted_count": len(records),
            "project": project,
            "branch": branch,
            "git_context": context.to_dict() if context else None,
        }
    )


def handle_archive_branch(args: argparse.Namespace) -> None:
    project, branch, context = resolve_project_and_branch(args.project, args.branch, args.cwd)
    metadata = set_branch_archived(
        project=project,
        branch=branch,
        archived=True,
        data_root=args.data_root,
    )
    emit(
        {
            "ok": True,
            "action": "archived_branch",
            "branch": metadata,
            "git_context": context.to_dict() if context else None,
        }
    )


def handle_unarchive_branch(args: argparse.Namespace) -> None:
    project, branch, context = resolve_project_and_branch(args.project, args.branch, args.cwd)
    metadata = set_branch_archived(
        project=project,
        branch=branch,
        archived=False,
        data_root=args.data_root,
    )
    emit(
        {
            "ok": True,
            "action": "unarchived_branch",
            "branch": metadata,
            "git_context": context.to_dict() if context else None,
        }
    )


def handle_context(args: argparse.Namespace) -> None:
    emit({"ok": True, **safe_context(args.cwd)})


def handle_open_ui(args: argparse.Namespace) -> None:
    payload = ensure_ui(
        host=args.host,
        port=args.port,
        data_root=args.data_root,
        cwd=args.cwd,
        open_browser=not args.no_browser,
    )
    emit(payload)


def handle_serve(args: argparse.Namespace) -> None:
    server, url = run_server(
        host=args.host,
        port=args.port,
        data_root=args.data_root,
        context_cwd=args.cwd,
        open_browser=args.open_browser,
    )
    print(json.dumps({"ok": True, "url": url, "data_root": args.data_root}, ensure_ascii=False))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def add_detail_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--detail-markdown")
    parser.add_argument("--feature-point", dest="feature_points", action="append")
    parser.add_argument("--modified-file", dest="modified_files", action="append")
    parser.add_argument("--api-change", dest="api_changes", action="append")
    parser.add_argument("--test-note", dest="test_notes", action="append")
    parser.add_argument("--remark", dest="remarks", action="append")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage local branch worklogs.")
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--cwd", default=str(Path.cwd()))
    parser.add_argument("--ui-mode", choices=["auto", "off"], default="auto")
    parser.add_argument("--ui-port", type=int, default=DEFAULT_PORT)
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Upsert the latest unreleased record for the current branch.")
    add_parser.add_argument("--summary", required=True)
    add_parser.add_argument("--project")
    add_parser.add_argument("--branch")
    add_parser.add_argument("--local-path")
    add_detail_arguments(add_parser)
    add_parser.set_defaults(func=handle_add)

    create_parser = subparsers.add_parser("create", help="Create a new record explicitly.")
    create_parser.add_argument("--summary", required=True)
    create_parser.add_argument("--project")
    create_parser.add_argument("--branch")
    create_parser.add_argument("--local-path")
    create_parser.add_argument("--status", default=STATUS_PENDING, choices=sorted(VALID_STATUSES))
    add_detail_arguments(create_parser)
    create_parser.set_defaults(func=handle_create)

    update_status_parser = subparsers.add_parser("update-status", help="Update the latest record status by branch.")
    update_status_parser.add_argument("--status", required=True, choices=sorted(VALID_STATUSES))
    update_status_parser.add_argument("--project")
    update_status_parser.add_argument("--branch")
    update_status_parser.set_defaults(func=handle_update_status)

    list_parser = subparsers.add_parser("list", help="List records.")
    list_parser.add_argument("--project")
    list_parser.add_argument("--branch")
    list_parser.add_argument("--status", default="all")
    list_parser.add_argument("--query")
    list_parser.set_defaults(func=handle_list)

    get_parser = subparsers.add_parser("get", help="Get a single record by id.")
    get_parser.add_argument("record_id")
    get_parser.set_defaults(func=handle_get)

    update_parser = subparsers.add_parser("update", help="Update a record by id.")
    update_parser.add_argument("record_id")
    update_parser.add_argument("--project")
    update_parser.add_argument("--branch")
    update_parser.add_argument("--local-path")
    update_parser.add_argument("--summary")
    update_parser.add_argument("--status", choices=sorted(VALID_STATUSES))
    add_detail_arguments(update_parser)
    update_parser.set_defaults(func=handle_update)

    delete_parser = subparsers.add_parser("delete", help="Delete a record by id.")
    delete_parser.add_argument("record_id")
    delete_parser.set_defaults(func=handle_delete)

    delete_branch_parser = subparsers.add_parser("delete-branch", help="Delete all records for a branch.")
    delete_branch_parser.add_argument("--project")
    delete_branch_parser.add_argument("--branch")
    delete_branch_parser.set_defaults(func=handle_delete_branch)

    archive_branch_parser = subparsers.add_parser("archive-branch", help="Archive a branch and hide it from the main list.")
    archive_branch_parser.add_argument("--project")
    archive_branch_parser.add_argument("--branch")
    archive_branch_parser.set_defaults(func=handle_archive_branch)

    unarchive_branch_parser = subparsers.add_parser("unarchive-branch", help="Restore an archived branch.")
    unarchive_branch_parser.add_argument("--project")
    unarchive_branch_parser.add_argument("--branch")
    unarchive_branch_parser.set_defaults(func=handle_unarchive_branch)

    context_parser = subparsers.add_parser("context", help="Show Git context for the current cwd.")
    context_parser.set_defaults(func=handle_context)

    open_ui_parser = subparsers.add_parser("open-ui", help="Ensure the local Web UI is running and open it.")
    open_ui_parser.add_argument("--host", default="127.0.0.1")
    open_ui_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    open_ui_parser.add_argument("--no-browser", action="store_true")
    open_ui_parser.set_defaults(func=handle_open_ui)

    serve_parser = subparsers.add_parser("serve", help="Run the local Web UI server.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.add_argument("--open-browser", action="store_true")
    serve_parser.set_defaults(func=handle_serve)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.ui_mode == "auto" and args.command not in {"serve", "open-ui"}:
            ensure_ui(
                host="127.0.0.1",
                port=args.ui_port,
                data_root=args.data_root,
                cwd=args.cwd,
                open_browser=True,
            )
        args.func(args)
    except (ValidationError, ContextError, NotFoundError) as exc:
        emit({"ok": False, "error": str(exc)}, exit_code=1)
    except BrokenPipeError:
        sys.exit(1)


if __name__ == "__main__":
    main()
