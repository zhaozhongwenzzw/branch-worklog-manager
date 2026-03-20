# Branch Worklog Manager

`branch-worklog-manager` 是一个本地优先的技能，用来记录分支开发内容、详细变更历史、分支级上线状态、分支归档与删除，并通过本地 Web UI 管理全部内容。

## 功能

- 以本地 Markdown 时间轴节点记录分支变更
- 同时保存简短总结和详细 Markdown 正文
- 自动提取功能点、修改文件、备注等结构化字段
- 管理分支级上线状态
- 仅允许已上线分支归档
- 支持归档分支恢复
- 支持永久删除整个分支历史
- 通过本地 Web UI 统一管理

## 仓库结构

- `SKILL.md`：技能主说明
- `agents/openai.yaml`：界面元数据
- `scripts/`：CLI、存储、启动器、服务端
- `assets/web/`：本地 Web UI
- `references/data-format.md`：数据格式说明

## 安装

### Claude Code

官方文档：

- Anthropic Quickstart: [Quickstart](https://docs.anthropic.com/en/docs/claude-code/quickstart)
- Claude Code slash commands / skills: [Extend Claude with skills](https://docs.anthropic.com/en/docs/claude-code/slash-commands)

先安装 Claude Code：

```bash
npm install -g @anthropic-ai/claude-code
```

然后把本仓库放到 Claude Code 的技能目录中：

- 个人级：
  - `~/.claude/skills/branch-worklog-manager`
- 项目级：
  - `<your-project>/.claude/skills/branch-worklog-manager`

安装完成后，按你的环境方式调用该 skill。

### Codex

官方文档：

- OpenAI Codex CLI: [Codex CLI](https://developers.openai.com/codex/cli)

先安装 Codex CLI：

```bash
npm i -g @openai/codex
```

然后运行：

```bash
codex
```

首次运行会要求登录。

在当前这套本地环境里，把本仓库放到：

- `~/.agents/skills/branch-worklog-manager`

本地数据目录默认是：

- `~/.agents/data/branch-worklog`

注意：

- `~/.agents/skills/...` 是当前本地环境的约定目录。
- 不同 Codex 环境可能使用不同的本地 skill 路径。

## 使用

### 自然语言示例

- `记录当前分支修改内容：实现库存分配页面`
- `把当前分支状态改为已上线`
- `打开分支记录管理页面`
- `归档当前分支`

### 常用 CLI 命令

记录当前分支变更：

```powershell
python "scripts/branch_worklog_cli.py" add --summary "实现库存分配页面"
```

创建详细记录：

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

更新单个时间轴节点：

```powershell
python "scripts/branch_worklog_cli.py" update <record-id> --summary "更新后的总结"
```

切换分支上线状态：

```powershell
python "scripts/branch_worklog_cli.py" update-status --status "已上线"
```

归档已上线分支：

```powershell
python "scripts/branch_worklog_cli.py" archive-branch
```

恢复归档分支：

```powershell
python "scripts/branch_worklog_cli.py" unarchive-branch --branch "feature/login"
```

永久删除整个分支：

```powershell
python "scripts/branch_worklog_cli.py" delete-branch --branch "feature/login"
```

打开本地 Web UI：

```powershell
python "scripts/branch_worklog_cli.py" open-ui
```

## 数据模型

### 时间轴节点

每个时间轴节点对应一个 Markdown 文件，主要字段包括：

- `project`
- `branch`
- `local_path`
- `summary`
- `detail_markdown`
- `feature_points`
- `modified_files`
- `remarks`
- 时间戳

### 分支元数据

分支级元数据单独存储，主要包括：

- `release_status`
- `archived`
- `archived_at`

### 规则

- 首页活跃分支列表默认不显示已归档分支
- 只有已上线分支可以归档
- 编辑节点时直接修改该节点
- 追加变更时才新增时间轴节点
- 删除分支会永久删除该分支下全部时间轴节点

## Web UI

- 左侧：当前工作区
- 中间：活跃分支列表
- 右侧抽屉：分支时间轴与节点编辑
- 项目概览弹窗
- 已归档分支弹窗

## 开发

校验 skill：

```powershell
python "C:/Users/20613/.agents/skills/skill-creator/scripts/quick_validate.py" .
```

启动本地 UI 服务：

```powershell
python "scripts/branch_worklog_cli.py" serve --open-browser
```

按需打开 UI：

```powershell
python "scripts/branch_worklog_cli.py" open-ui
```

## 说明

- 这个技能完全本地运行，不依赖数据库
- 归档分支不会出现在首页，但可以恢复
- 历史旧数据仍保持兼容可读
