# Branch Worklog Manager

`branch-worklog-manager` is a local-first skill for recording branch work, detailed change history, branch-level release status, branch archiving, branch deletion, and managing everything through a local Web UI.

## Features

- Record branch changes as local Markdown timeline nodes
- Keep both a short summary and detailed Markdown notes
- Auto-extract structured fields such as feature points, modified files, and remarks
- Manage branch-level release status
- Allow archiving only for released branches
- Restore archived branches later
- Permanently delete a full branch history when needed
- Open and manage everything through a local Web UI

## Repository Layout

- `SKILL.md`: core skill instructions
- `agents/openai.yaml`: UI metadata
- `scripts/`: CLI, storage, launcher, and server
- `assets/web/`: local Web UI
- `references/data-format.md`: storage format reference

## Installation

### Codex Quick Install

Once this repository is published to GitHub, you can tell Codex:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/zhaozhongwenzzw/branch-worklog-manager/refs/heads/main/.codex/INSTALL.md
```

### Claude Code

Official documentation:

- Anthropic Quickstart: [Quickstart](https://docs.anthropic.com/en/docs/claude-code/quickstart)
- Claude Code slash commands / skills: [Extend Claude with skills](https://docs.anthropic.com/en/docs/claude-code/slash-commands)

Install Claude Code first:

```bash
npm install -g @anthropic-ai/claude-code
```

Then place this repository in the Claude Code skills directory:

- Personal scope:
  - `~/.claude/skills/branch-worklog-manager`
- Project scope:
  - `<your-project>/.claude/skills/branch-worklog-manager`

After installation, invoke the skill using the command style supported by your Claude Code environment.

### Codex

Official documentation:

- OpenAI Codex CLI: [Codex CLI](https://developers.openai.com/codex/cli)

Install Codex CLI:

```bash
npm i -g @openai/codex
```

Then run:

```bash
codex
```

The first run will ask you to sign in.

In the local environment used here, place this repository in:

- `~/.agents/skills/branch-worklog-manager`

The local data directory defaults to:

- `~/.agents/data/branch-worklog`

Important:

- `~/.agents/skills/...` is the local convention used in this environment.
- Different Codex environments may use different local skill directories.
- A Codex AI-install entrypoint is provided in [`.codex/INSTALL.md`](./.codex/INSTALL.md).

## Usage

### Natural language examples

- `Record current branch changes: implement inventory assignment page`
- `Mark the current branch as released`
- `Open the branch worklog manager page`
- `Archive the current branch`

### Common CLI commands

Record current branch work:

```powershell
python "scripts/branch_worklog_cli.py" add --summary "Implement inventory assignment page"
```

Create a detailed record:

```powershell
python "scripts/branch_worklog_cli.py" create ^
  --summary "Complete permission module refactor" ^
  --detail-markdown "Feature points:
- Refactor permission checks
- Add menu permission mapping

Modified files:
- auth/service.py
- auth/routes.py
- ui/menu.ts

Remarks:
- Waiting for product to confirm menu wording"
```

Update a timeline node:

```powershell
python "scripts/branch_worklog_cli.py" update <record-id> --summary "Updated summary"
```

Change branch release status:

```powershell
python "scripts/branch_worklog_cli.py" update-status --status "已上线"
```

Archive a released branch:

```powershell
python "scripts/branch_worklog_cli.py" archive-branch
```

Restore an archived branch:

```powershell
python "scripts/branch_worklog_cli.py" unarchive-branch --branch "feature/login"
```

Delete a branch completely:

```powershell
python "scripts/branch_worklog_cli.py" delete-branch --branch "feature/login"
```

Open the local Web UI:

```powershell
python "scripts/branch_worklog_cli.py" open-ui
```

## Data Model

### Timeline nodes

Each timeline node is stored as one Markdown file and includes:

- `project`
- `branch`
- `local_path`
- `summary`
- `detail_markdown`
- `feature_points`
- `modified_files`
- `remarks`
- timestamps

### Branch metadata

Branch-level metadata is stored separately and includes:

- `release_status`
- `archived`
- `archived_at`

### Rules

- Active branch lists hide archived branches
- Only released branches can be archived
- Editing a node updates that node directly
- Appending a change creates a new timeline node
- Deleting a branch permanently removes all timeline nodes for that branch

## Web UI

- Left panel: current workspace
- Main panel: active branch list
- Right drawer: branch timeline and node editing
- Project overview panel
- Archived branches panel

## Development

Validate the skill:

```powershell
python "C:/Users/20613/.agents/skills/skill-creator/scripts/quick_validate.py" .
```

Run the local UI server:

```powershell
python "scripts/branch_worklog_cli.py" serve --open-browser
```

Open the UI only if needed:

```powershell
python "scripts/branch_worklog_cli.py" open-ui
```

## Notes

- This repository is local-first and does not require a database
- Archived branches are hidden from the main list but can be restored
- Existing old records remain readable for compatibility
