---
name: tmux
description: >
  Control tmux/psmux sessions for interactive CLIs, SSH connections, and parallel agent orchestration.
  Works cross-platform: tmux on Linux/macOS, psmux on Windows. Provides sync commands that send keys
  and automatically capture output. Triggers: "run in tmux", "create tmux session", "tmux", "SSH session",
  "parallel terminals", "run multiple agents".
---

# tmux Skill

Control tmux sessions programmatically. Send keys, capture output, run interactive processes.

**Cross-platform:**
- **Linux/macOS**: Uses native `tmux`
- **Windows**: Uses `psmux` (native Windows tmux, 95%+ syntax compatible)

**Use tmux when:**
- SSH to remote servers (persistent sessions)
- Interactive TTY needed (REPLs, shells, prompts)
- Running multiple processes in parallel
- Orchestrating coding agents

**Don't use tmux for:**
- Simple background tasks → use `bg run` instead
- One-shot commands → run directly

---

## Installation

### Linux/macOS
```bash
# Debian/Ubuntu
sudo apt install tmux

# macOS
brew install tmux
```

### Windows (psmux)

psmux is a native Windows tmux implementation. Same commands, same config.

```powershell
# WinGet (recommended)
winget install psmux

# Scoop
scoop bucket add psmux https://github.com/marlocarlo/scoop-psmux
scoop install psmux

# Chocolatey
choco install psmux

# Cargo
cargo install psmux
```

**If installation fails:**
- Check GitHub releases: https://github.com/marlocarlo/psmux/releases
- Download `.zip`, extract, add to PATH
- Requires PowerShell 7+ (install: `winget install Microsoft.PowerShell`)

**Verify:**
```powershell
psmux -V
# or just: tmux (psmux ships with tmux alias)
```

---

## Quick Start

```bash
# Unix
tmux -V
tmx new mysession
tmx sync mysession "ls -la"
tmx capture mysession
tmx kill mysession
```

```powershell
# Windows
psmux -V
tmx new mysession
tmx sync mysession "Get-ChildItem"
tmx capture mysession
tmx kill mysession
```

---

## Helper: tmx

Scripts at `{baseDir}/scripts/`:
- `tmx.sh` — Bash version (Linux/macOS)
- `tmx.ps1` — PowerShell version (Windows, works everywhere)

### Commands

| Command | Description |
|---------|-------------|
| `tmx new <name> [cmd]` | Create session, optionally run cmd |
| `tmx send <session> "<cmd>"` | Send keys (fire and forget) |
| `tmx capture <session> [lines]` | Capture output (default 500 lines) |
| `tmx sync <session> "<cmd>"` | Send + wait + capture |
| `tmx list` | List all sessions |
| `tmx kill <session>` | Kill session |
| `tmx attach <session>` | Attach interactively |

### Sync Modes

```bash
# Wait for shell prompt (default)
tmx sync server "pip install numpy"

# Fixed timeout mode
tmx sync server "make build" --timeout 30   # Bash
tmx sync server "make build" -Timeout 30    # PowerShell

# Custom prompt pattern
tmx sync server "python script.py" --prompt "DONE>"  # Bash
tmx sync server "python script.py" -Prompt "DONE>"   # PowerShell
```

---

## Pattern 1: SSH Sessions (Most Common)

SSH through tmux gives persistent sessions that survive disconnects.

```bash
# Create SSH session
tmx new server "ssh user@myserver.com"

# Wait for password prompt or SSH ready
tmx capture server 20   # Check where we are

# Send password (if needed)
tmx send server "mypassword"

# Wait for shell prompt on remote
tmx sync server "hostname" --prompt '\$'

# Run remote commands
tmx sync server "cd /var/log && ls -la"
tmx sync server "tail -100 nginx/access.log" --timeout 5

# Long-running remote task
tmx send server "docker logs -f mycontainer"
# Later: capture output
tmx capture server 500

# Detach and return later - SSH persists!
tmx list  # session still there
tmx capture server  # get latest output
```

**SSH with sudo:**
```bash
tmx new prod "ssh admin@prod-server"
tmx sync prod "sudo tail -f /var/log/syslog" --prompt '\[sudo\]'
tmx send prod "sudo_password"
tmx capture prod 200
```

---

## Pattern 2: Background Process Monitoring

Monitor long-running processes in tmux. Useful when already working in tmux context.

```bash
# Start a server
tmx new api "cd /app && python api.py"
tmx sync api "echo 'Server starting...'" --timeout 3

# Check if running
tmx capture api 30 | grep -q "Listening" && echo "API is up"

# Monitor logs
tmx capture api 100

# Tail mode (continuous capture)
for i in {1..10}; do
  tmx capture api 5
  sleep 2
done

# Multiple services
tmx new db "docker run --name postgres -e POSTGRES_PASSWORD=pass postgres"
tmx new redis "redis-server"

# Check all
tmx list
tmx capture db 20
tmx capture redis 20
```

---

## Pattern 3: Interactive REPL

REPLs work but may need prompt tuning. Use `--prompt` for custom prompts.

```bash
# Python (standard REPL)
tmx new python "python3 -q"
tmx sync python "import sys; print(sys.version)"
tmx sync python "2 + 2"

# IPython (custom prompt)
tmx new ipy "ipython"
tmx sync ipy "print('hello')" --prompt "In \[.*\]:"

# Node.js
tmx new node "node -i"
tmx sync node "1+1" --prompt ">"
```

---

## Pattern 4: Parallel Agents

```bash
# Spin up multiple coding agents
for i in 1 2 3; do
  tmx new "agent-$i" "cd /tmp/project$i && codex --yolo 'Fix bugs'"
done

# Poll for completion
for s in agent-1 agent-2 agent-3; do
  if tmx capture "$s" 20 | grep -q "completed"; then
    echo "$s: DONE"
  fi
done

# Get results
tmx capture agent-1 2000
```

---

## Key Bindings (when attached)

| Key | Action |
|-----|--------|
| `Ctrl+b d` | Detach from session |
| `Ctrl+b c` | Create new window |
| `Ctrl+b n/p` | Next/Previous window |
| `Ctrl+b %` | Split vertical |
| `Ctrl+b "` | Split horizontal |
| `Ctrl+b [` | Copy mode (scroll) |

---

## Platform Differences

| Feature | tmux (Unix) | psmux (Windows) |
|---------|-------------|-----------------|
| Sessions | ✅ | ✅ |
| Windows/Panes | ✅ | ✅ |
| Detach/Attach | ✅ | ✅ |
| `capture-pane` | ✅ | ✅ |
| `send-keys` | ✅ | ✅ |
| `.tmux.conf` | ✅ | ✅ (also `.psmux.conf`) |
| Mouse support | ✅ | ✅ |
| SSH mouse | ✅ | Win11 22H2+ |

---

## Gotchas

- **REPL prompts**: IPython, IRB, etc. use different prompts. Use `--prompt` to match.
- **Named sessions only**: No socket complexity
- **Prompt detection**: Default `(\$|❯|#|>|>>>)` covers most shells
- **psmux is fresh**: If issues, check GitHub releases for updates
- **Windows needs PowerShell 7+**: Install with `winget install Microsoft.PowerShell`

---

## Raw Commands

```bash
# Target syntax: session:window.pane
tmux send-keys -t mysession -l -- "echo hello"
tmux send-keys -t mysession Enter
tmux capture-pane -p -J -t mysession -S -500
tmux list-sessions
```
