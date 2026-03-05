# AgentCLI Helpers — Product Specification

> Desktop superpowers for your AI agent. Simple CLI tools that just work.

## Overview

AgentCLI Helpers is a collection of 4 independent CLI tools that extend AI agent capabilities with desktop integration. Each tool is a standalone command with no daemon, no database, and no configuration required.

**Installation:**
```bash
uv tool install agentcli-helpers
```

**Optional extras:**
```bash
uv tool install agentcli-helpers[crony]    # Cron job support
uv tool install agentcli-helpers[screenshot]  # Screenshot support
uv tool install agentcli-helpers[all]      # Everything
```

---

## Tool: notify — Desktop Notifications

Cross-platform desktop notifications using native OS tools.

### Commands

#### `notify TITLE [BODY]`

Send a desktop notification.

**Arguments:**
- `TITLE` — Notification title (required)
- `BODY` — Notification body (optional). If omitted, TITLE becomes the body and title defaults to "Notification".

**Options:**
- `--sound` — Play notification sound (platform dependent)

**Input modes:**
1. Arguments: `notify "Build Done" "All tests passed!"`
2. Piped stdin: `echo "Status update" | notify "Progress"`
3. Explicit stdin: `cat log.txt | notify "Logs" -`

**Exit codes:**
- `0` — Notification sent successfully
- `1` — Failed to send notification

### Platform Behavior

| Platform | Tool Used | Notes |
|----------|-----------|-------|
| Windows | PowerShell Toast API | Uses `Windows.UI.Notifications` |
| macOS | `osascript` | Uses AppleScript notification |
| Linux | `notify-send` | Requires `libnotify` package |

### Edge Cases

- If BODY is `-`, reads from stdin (explicit pipe mode)
- If no body provided, TITLE is used as body with title "Notification"
- If stdin is empty and no body provided, sends empty notification
- If notification tool not found, exits with code 1 and error message

---

## Tool: bg — Background Jobs

Run and track background jobs with persistent storage and status monitoring.

### Commands

#### `bg run "CMD"`

Start a command in the background.

**Arguments:**
- `CMD` — Command to execute (string)

**Output:**
- Returns 6-character alphanumeric job ID (e.g., `abc123`)

**Behavior:**
- Job runs detached from terminal
- Process continues even if parent shell exits
- stdout and stderr are captured to files

#### `bg list [--json]`

List all background jobs.

**Options:**
- `--json` — Output as JSON array

**Output (human-readable):**
- Table with columns: ID, Status, Started, Command
- Status colors: yellow=running, green=completed, red=failed

**Output (JSON):**
```json
[
  {
    "id": "abc123",
    "cmd": "python script.py",
    "started_at": "2026-03-05T10:00:00",
    "status": "running",
    "pid": 12345
  }
]
```

**Behavior:**
- Automatically checks if running processes are still alive
- Updates status to "completed" if process has exited

#### `bg status JOB_ID`

Check job status.

**Arguments:**
- `JOB_ID` — Job identifier (6 chars)

**Output:**
- Full job metadata as JSON

**Behavior:**
- If job was "running" but process is dead, updates status to "completed"

#### `bg read JOB_ID`

Read job stdout.

**Arguments:**
- `JOB_ID` — Job identifier

**Output:**
- Complete stdout contents

#### `bg logs JOB_ID`

Read job stdout and stderr.

**Arguments:**
- `JOB_ID` — Job identifier

**Output:**
```
=== STDOUT ===
<stdout content>

=== STDERR ===
<stderr content>
```

#### `bg rm JOB_ID`

Remove a job record.

**Arguments:**
- `JOB_ID` — Job identifier

**Behavior:**
- If job is still running, kills the process first
- Removes all job files from storage

### Storage

Jobs stored in: `{tempdir}/agentcli_bgjobs/{job_id}/`

| File | Contents |
|------|----------|
| `meta.json` | Job metadata (id, cmd, pid, status, timestamps) |
| `stdout.txt` | Captured stdout |
| `stderr.txt` | Captured stderr |

### Status Values

- `running` — Process is active
- `completed` — Process finished successfully
- `failed` — Process exited with non-zero code

### Edge Cases

- Job ID not found: exits with code 1, error message to stderr
- Process already dead when checking status: auto-updates to "completed"
- Windows: uses `CREATE_NEW_PROCESS_GROUP` + `DETACHED_PROCESS`
- Unix: uses `start_new_session` for full detachment

---

## Tool: crony — Cron Jobs, Human-Readable

Natural language cron job scheduler with OS-level integration.

### Commands

#### `crony add NAME SCHEDULE "CMD"`

Add a new cron job.

**Arguments:**
- `NAME` — Unique job name (identifier)
- `SCHEDULE` — Natural language schedule (see below)
- `CMD` — Command to execute

**Schedule formats:**

| Format | Example | Description |
|--------|---------|-------------|
| Relative | `in 5m`, `in 1h`, `in 2d` | One-off, runs once |
| Time | `at 15:30`, `at "2026-03-10 10:00"` | One-off at specific time |
| Interval | `every 1h`, `every 30m`, `every 24h` | Recurring |
| Day | `every monday`, `every weekday`, `every weekend` | Weekly or daily |

**Output:**
```
Added job: health-check
  Schedule: every 1h (recurring)
  Cron: 0 * * * *
```

#### `crony list [--json] [--sync]`

List all cron jobs.

**Options:**
- `--json` — Output as JSON
- `--sync` — Force sync with OS scheduler

**Behavior:**
- Auto-syncs with OS scheduler on every call (reconciles jobs.json with crontab/Task Scheduler)
- Finds orphaned tasks in OS and adds to index
- Re-registers jobs missing from OS

#### `crony rm NAME`

Remove a cron job.

**Arguments:**
- `NAME` — Job name

**Behavior:**
- Removes from jobs.json
- Removes from OS scheduler (crontab or Task Scheduler)

#### `crony run NAME`

Run a job immediately.

**Arguments:**
- `NAME` — Job name

**Behavior:**
- Executes the command immediately (does not modify schedule)

#### `crony logs NAME`

View job logs.

**Arguments:**
- `NAME` — Job name

**Output:**
- Log file contents if exists

### Storage

| Location | Contents |
|----------|----------|
| `~/.crony/jobs.json` | Job definitions and metadata |
| `~/.crony/logs/{name}.log` | Job execution logs |

### OS Integration

| Platform | Scheduler | Marker |
|----------|-----------|--------|
| Linux | crontab | `# CRONY:{name}` |
| macOS | crontab | `# CRONY:{name}` |
| Windows | Task Scheduler | `CRONY_{name}` |

### Edge Cases

- Job name already exists: error, must remove first
- Invalid schedule: error with message
- Missing optional dependencies: error with install hint
- OS scheduler unavailable: error, but job saved to index
- One-off jobs: stored in index but not added to recurring scheduler

---

## Tool: screenshot — Screen Capture

Cross-platform screenshot capture with auto-naming.

### Commands

#### `screenshot [OUTPUT]`

Take a screenshot.

**Arguments:**
- `OUTPUT` — Optional output file path. If omitted, auto-generates.

**Options:**
- `--all-monitors` — Capture all monitors (default behavior)

**Output:**
- Prints the saved file path to stdout

**Auto-naming:**
- Format: `screenshot_{YYYYMMDD}_{HHMMSS}.png`
- Location: `{tempdir}/agentcli_screenshots/`

### Platform Behavior

| Platform | Primary | Fallback |
|----------|---------|----------|
| Windows | mss library | PowerShell + System.Drawing |
| macOS | mss library | `screencapture` |
| Linux | mss library | `gnome-screenshot`, `scrot`, `import`, `flameshot` |

### Edge Cases

- mss not installed: falls back to native tools
- No native tool available: exits with code 1, suggests install
- Output path has parent directories: creates them automatically
- Multiple monitors: captures combined virtual screen (monitor 0)

---

## Dependencies

### Core (always installed)
- `click >= 8.1.0` — CLI framework
- `rich >= 13.0.0` — Terminal formatting

### Optional
- `dateparser >= 1.2.0` — Natural language date parsing (crony)
- `schedule >= 1.2.0` — Schedule library (crony)
- `mss >= 9.0.0` — Cross-platform screenshot (screenshot)
- `pillow >= 10.0.0` — Image processing (screenshot)

---

## Exit Codes

All tools follow this convention:
- `0` — Success
- `1` — Error (invalid input, tool not found, operation failed)

---

## Design Principles

1. **No daemon** — All tools are stateless CLI invocations
2. **No database** — JSON files for persistence
3. **No configuration** — Sensible defaults, auto-detection
4. **Pipe-friendly** — All tools accept stdin where appropriate
5. **Cross-platform** — Same interface on Windows, macOS, Linux