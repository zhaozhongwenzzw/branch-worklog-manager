# Branch Worklog Data Format

## Storage Root

- Default root: `C:/Users/20613/.agents/data/branch-worklog`
- Records directory: `C:/Users/20613/.agents/data/branch-worklog/records/<project-slug>/`

## Record File Format

Each record is a Markdown file with YAML-like frontmatter and a Markdown detail body. One file represents one timeline node. Branch-level release and archive state are stored separately in branch metadata.

```md
---
id: "20260319-182000-123456-feature-login-a1b2c3"
project: "hello-admin"
branch: "feature/login"
local_path: "D:\\work\\hello-admin"
created_at: "2026-03-19T18:20:00.123456+08:00"
updated_at: "2026-03-19T18:20:00.123456+08:00"
summary: "完成权限模块改造"
feature_points: ["重构权限校验", "补充角色菜单映射"]
modified_files: ["auth/service.py", "auth/routes.py", "ui/menu.ts"]
remarks: ["等待产品确认菜单文案"]
---
功能点:
- 重构权限校验
- 补充角色菜单映射

修改文件:
- auth/service.py
- auth/routes.py
- ui/menu.ts

```

## Field Rules

- `id`: unique identifier used by the CLI and Web UI
- `project`: repository root folder name by default
- `branch`: original Git branch name
- `local_path`: absolute local project path; defaults to the repository root
- `summary`: short branch change summary used in lists and timeline cards
- `feature_points`: extracted or edited function-level change points
- `modified_files`: extracted or edited file paths
- `remarks`: extracted or edited remarks or risks
- `created_at`: initial write time in ISO 8601 with microseconds
- `updated_at`: last mutation time in ISO 8601 with microseconds
- Body: long Markdown detail for the work item

## Branch Metadata

Branch-level metadata is stored separately and includes:

- `release_status`: `未上线` or `已上线`
- `archived`: whether the branch is hidden from the main list
- `archived_at`: archive timestamp

## File Naming

The server writes files as:

`<timestamp>-<branch-slug>.md`

Example:

`20260319-182000-123456-feature-login.md`

## Update Semantics

- Records are append-only timeline nodes.
- CLI `add` and `create` compare against the latest node of the same project + branch.
- If content fields are unchanged, no new node is created and the command returns `unchanged`.
- If the UI is already running, the launcher should reuse it and return the URL without reopening the browser.
- If any of those fields changed, a new node is created.
- Branch release status changes do not create time axis nodes.
- Only branches with `release_status = 已上线` may be archived.
- Deleting a record removes the underlying Markdown file.
