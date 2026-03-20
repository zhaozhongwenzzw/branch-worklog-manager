---
name: branch-worklog-manager
description: Track local Git branch work as Markdown timeline events and manage it through a local Web UI that auto-opens whenever the skill runs. Use when the user asks to record current branch modifications, mark a branch as 已上线, review branch history, or open a local branch management page.
---

# Branch Worklog Manager

## Overview

This skill keeps a local branch worklog outside the active project. It records timeline events as local Markdown files with `project`, `branch`, `local_path`, a short `summary`, structured detail fields, and a long Markdown body. Branch-level metadata separately tracks release status and archive state, and the local Web UI manages both active and archived branch views.

## When To Use

Use this skill when the user asks to:

- Record current branch changes such as `记录当前分支修改内容：xxx`
- Mark a branch as released such as `把当前分支状态改为已上线`
- Review or list historical branch records
- Open a local management page for branch worklogs

## Default Rules

- Data stays local at `C:/Users/20613/.agents/data/branch-worklog`
- Every skill run should ensure the Web UI is running
- If the Web UI is not running yet, start it and open the browser
- If the Web UI is already running, do not re-open the browser; return the URL instead
- Branches have a branch-level release status: `未上线` or `已上线`
- Git context comes from the user's current working directory
- Project name is the current repository root folder name
- Local path defaults to the current repository root
- Status updates apply to the whole branch within the current project
- Data is stored as append-only timeline nodes
- A new node is created only when content fields differ from the latest node on the same branch
- Only released branches can be archived

## Workflow

### 1. Always ensure the Web UI is open

The CLI now auto-opens the Web UI for normal commands. You can also open it explicitly:

```powershell
python "C:/Users/20613/.agents/skills/branch-worklog-manager/scripts/branch_worklog_cli.py" open-ui
```

### 2. Record current branch work

Run the CLI from the user's current repository so Git context can be detected:

```powershell
python "C:/Users/20613/.agents/skills/branch-worklog-manager/scripts/branch_worklog_cli.py" add --summary "实现登录接口和页面联调"
```

This command will:

- Detect the repository root and current branch
- Ensure the local Web UI is running and open it
- Create a new timeline node only if content fields changed
- Prefer richer records: generate `summary`, `feature_points`, `modified_files`, `remarks`, and long Markdown detail from the user's request
- Print JSON describing the result

### 3. Update branch release status

For the current branch:

```powershell
python "C:/Users/20613/.agents/skills/branch-worklog-manager/scripts/branch_worklog_cli.py" update-status --status "已上线"
```

For a specific branch in the current project:

```powershell
python "C:/Users/20613/.agents/skills/branch-worklog-manager/scripts/branch_worklog_cli.py" update-status --branch "feature/login" --status "已上线"
```

### 4. Browse and manage the timeline UI

The page supports:

- Branch-first timeline browsing
- Search by project, branch, local path, and historical content
- Append-only change recording through a right-side drawer
- Edit detailed structured fields and long Markdown notes on existing timeline nodes
- Delete specific timeline nodes
- Archive released branches from the branch list and restore them from the archive panel
- Open project overview in a detached floating panel

## Error Handling

- If the current working directory is not a Git repository, fail clearly and ask for a repository directory or explicit project/branch override.
- If no matching branch exists during status updates, return a not-found error instead of creating a new record.
- If no field changed relative to the latest branch node, return `unchanged` and do not create a duplicate node.
- If a branch is not `已上线`, archiving it must fail.
- If record files are malformed, skip them in listings and surface the parsing error in CLI or server logs.

## Resources

- `scripts/branch_worklog_lib.py`: Markdown storage, Git context detection, timeline grouping, and CRUD helpers
- `scripts/branch_worklog_cli.py`: command-line entrypoint for add, update, list, delete, `open-ui`, and serve
- `scripts/branch_worklog_server.py`: local HTTP server and JSON API for the Web UI
- `scripts/branch_worklog_ui_launcher.py`: detached launcher that ensures the Web UI is running and opens it
- `references/data-format.md`: record structure and conventions
- `assets/web/`: local HTML, CSS, and JavaScript for the management page
