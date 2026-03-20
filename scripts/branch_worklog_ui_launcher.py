#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from branch_worklog_lib import DEFAULT_DATA_ROOT, resolve_data_root, write_context_snapshot

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
PID_FILENAME = "branch-worklog-server.pid"


def server_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def is_server_alive(url: str, timeout: float = 0.8) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/api/context", timeout=timeout) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def start_detached_server(
    *,
    host: str,
    port: int,
    data_root: Path,
    cwd: Path,
) -> int:
    server_script = Path(__file__).resolve().parent / "branch_worklog_server.py"
    log_path = data_root / "branch-worklog-server.log"
    pid_path = data_root / PID_FILENAME
    log_handle = log_path.open("a", encoding="utf-8")

    command = [
        sys.executable,
        str(server_script),
        "--host",
        host,
        "--port",
        str(port),
        "--data-root",
        str(data_root),
        "--context-cwd",
        str(cwd),
    ]

    popen_kwargs = {
        "stdout": log_handle,
        "stderr": log_handle,
        "cwd": str(cwd),
        "close_fds": True,
    }

    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        popen_kwargs["start_new_session"] = True

    process = subprocess.Popen(command, **popen_kwargs)
    log_handle.close()
    pid_path.write_text(str(process.pid), encoding="utf-8")
    return process.pid


def ensure_ui(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    data_root: str | Path | None = None,
    cwd: str | Path | None = None,
    open_browser: bool = True,
) -> dict[str, object]:
    resolved_data_root = resolve_data_root(data_root)
    resolved_cwd = Path(cwd).resolve() if cwd else Path.cwd().resolve()
    write_context_snapshot(resolved_cwd, resolved_data_root)

    url = server_url(host, port)
    started = False
    pid: int | None = None
    opened_browser = False

    if not is_server_alive(url):
        pid = start_detached_server(
            host=host,
            port=port,
            data_root=resolved_data_root,
            cwd=resolved_cwd,
        )
        started = True

        for _ in range(30):
            if is_server_alive(url):
                break
            time.sleep(0.2)
        else:
            raise RuntimeError(f"failed to start branch worklog UI at {url}")

    if open_browser and started:
        webbrowser.open(url)
        opened_browser = True

    return {
        "ok": True,
        "started": started,
        "opened_browser": opened_browser,
        "pid": pid,
        "url": url,
        "data_root": str(resolved_data_root),
        "cwd": str(resolved_cwd),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ensure the branch worklog Web UI is running and open it.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--cwd", default=str(Path.cwd()))
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    payload = ensure_ui(
        host=args.host,
        port=args.port,
        data_root=args.data_root,
        cwd=args.cwd,
        open_browser=not args.no_browser,
    )
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
