# Branch Worklog Manager

Branch Worklog Manager is a local-first skill for tracking branch work, detailed change history, release status, archiving, and a local Web UI.

`branch-worklog-manager` 是一个本地优先的技能，用来记录分支开发内容、详细变更历史、分支上线状态、归档与本地 Web UI 管理。

## Features

### English

- Record branch changes as timeline nodes stored in local Markdown files
- Keep both a short summary and detailed Markdown notes
- Auto-extract structured fields such as feature points, modified files, and remarks
- Manage branch-level release status
- Archive released branches and restore them later
- Permanently delete a full branch history when needed
- Open and manage everything through a local Web UI

### 中文

- 以本地 Markdown 时间轴节点记录分支变更
- 同时保存简短总结和详细 Markdown 正文
- 自动提取功能点、修改文件、备注等结构化字段
- 管理分支级上线状态
- 支持分支归档与恢复
- 需要时可永久删除整个分支历史
- 通过本地 Web UI 统一管理

## Repository Layout

### English

- `SKILL.md`: core skill instructions
- `agents/openai.yaml`: UI metadata
- `scripts/`: CLI, storage, launcher, and server
- `assets/web/`: local Web UI
- `references/data-format.md`: storage format reference

### 中文

- `SKILL.md`：技能主说明
- `agents/openai.yaml`：界面元数据
- `scripts/`：CLI、存储、启动器、服务端
- `assets/web/`：本地 Web UI
- `references/data-format.md`：数据格式说明

## Installation

### Claude Code

Official Claude Code installation:

- Anthropic Quickstart: [Quickstart](https://docs.anthropic.com/en/docs/claude-code/quickstart)
- Anthropic Skills documentation: [Extend Claude with skills](https://docs.anthropic.com/en/docs/claude-code/slash-commands)

Install Claude Code first:

```bash
npm install -g @anthropic-ai/claude-code
```

Or use the native installer shown in Anthropic's quickstart.

Install this skill for Claude Code:

- Personal scope:
  - Copy or clone this repository to `~/.claude/skills/branch-worklog-manager`
- Project scope:
  - Copy or clone this repository to `<your-project>/.claude/skills/branch-worklog-manager`

After that, open Claude Code and invoke `/branch-worklog-manager` if your setup exposes the skill as a slash command.

### Codex

Official Codex CLI installation:

- OpenAI Codex CLI docs: [Codex CLI](https://developers.openai.com/codex/cli)

Install Codex CLI:

```bash
npm i -g @openai/codex
```

Then run:

```bash
codex
```

The first run will ask you to sign in.

Install this skill for the current Codex-style local environment used in this workspace:

- Copy or clone this repository to `~/.agents/skills/branch-worklog-manager`
- The local data directory defaults to `~/.agents/data/branch-worklog`

Important:

- The `~/.agents/skills/...` path is based on the current local environment convention in this workspace.
- Different Codex environments may use different local skill directories.

## Usage

### Natural language examples

#### English

- `Record current branch changes: implement inventory assignment page`
- `Mark the current branch as released`
- `Open the branch worklog manager page`
- `Archive the current branch`

#### 中文

- `记录当前分支修改内容：实现库存分配页面`
- `把当前分支状态改为已上线`
- `打开分支记录管理页面`
- `归档当前分支`

### CLI examples

Record current branch work:

```powershell
python "scripts/branch_worklog_cli.py" add --summary "实现库存分配页面"
```

Create a detailed record:

```powershell
python "scripts/branch_worklog_cli.py" create ^
  --summary "完成权限模块改造" ^
  --detail-markdown "功能点:
- 重构权限校验
- 增加菜单权限映射

修改文件:
- auth/service.py
- auth/routes.py
- ui/menu.ts

备注:
- 等待产品确认菜单文案"
```

Update a timeline node:

```powershell
python "scripts/branch_worklog_cli.py" update <record-id> --summary "更新后的总结"
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

Each timeline node is stored as one Markdown file and keeps:

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

Branch-level metadata is stored separately and keeps:

- `release_status`
- `archived`
- `archived_at`

### Rules

#### English

- Active branch lists hide archived branches
- Only released branches can be archived
- Editing a node updates that node directly
- Appending a change creates a new timeline node

#### 中文

- 首页分支列表默认不显示已归档分支
- 只有已上线分支可以归档
- 编辑节点时直接修改该节点
- 追加变更时才新增时间轴节点

## Web UI

### English

- Left panel: current workspace
- Main panel: active branch list
- Right drawer: branch timeline and node editing
- Project overview panel
- Archived branches panel

### 中文

- 左侧：当前工作区
- 中间：活跃分支列表
- 右侧抽屉：分支时间轴与节点编辑
- 项目概览弹窗
- 已归档分支弹窗

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

### English

- This repository is local-first and does not require a database
- Archived branches are hidden from the main list but can be restored
- Existing old records remain readable for compatibility

### 中文

- 这个技能完全本地运行，不依赖数据库
- 归档分支不会出现在首页，但可以恢复
- 历史旧数据仍保持兼容可读
