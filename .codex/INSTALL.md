# Branch Worklog Manager for Codex

Guide for using Branch Worklog Manager with OpenAI Codex via native skill discovery.

## Quick Install

Tell Codex:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/zhaozhongwenzzw/branch-worklog-manager/refs/heads/main/.codex/INSTALL.md
```

## Manual Installation

### Prerequisites

- OpenAI Codex CLI
- Git

### Steps

1. Clone the repo:

   ```bash
   git clone https://github.com/zhaozhongwenzzw/branch-worklog-manager.git ~/.codex/branch-worklog-manager
   ```

2. Make the skill visible to Codex:

   ```bash
   mkdir -p ~/.agents/skills
   ln -s ~/.codex/branch-worklog-manager ~/.agents/skills/branch-worklog-manager
   ```

3. Restart Codex.

4. The default local data directory is:

   ```text
   ~/.agents/data/branch-worklog
   ```

### Windows

Use a junction instead of a symlink:

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.agents\skills"
cmd /c mklink /J "$env:USERPROFILE\.agents\skills\branch-worklog-manager" "$env:USERPROFILE\.codex\branch-worklog-manager"
```

## How It Works

Codex scans `~/.agents/skills/` at startup and loads skills on demand. This skill becomes available through:

```text
~/.agents/skills/branch-worklog-manager -> ~/.codex/branch-worklog-manager
```

## Updating

```bash
cd ~/.codex/branch-worklog-manager && git pull
```

## Uninstalling

```bash
rm ~/.agents/skills/branch-worklog-manager
rm -rf ~/.codex/branch-worklog-manager
```

**Windows (PowerShell):**

```powershell
Remove-Item "$env:USERPROFILE\.agents\skills\branch-worklog-manager"
Remove-Item -Recurse -Force "$env:USERPROFILE\.codex\branch-worklog-manager"
```

## Troubleshooting

### Skill not showing up

1. Verify the link:

   ```bash
   ls -la ~/.agents/skills/branch-worklog-manager
   ```

2. Check the cloned repo:

   ```bash
   ls ~/.codex/branch-worklog-manager
   ```

3. Restart Codex.
