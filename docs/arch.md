# AgentCLI Helpers — Architecture

This document describes the internal implementation of each tool. For product behavior and CLI interface, see `product.md`.

---

## Project Structure

```
AgentCLI_Helpers/
├── src/agentcli_helpers/
│   ├── __init__.py          # Package init, version
│   ├── notify.py            # Desktop notifications
│   ├── bg.py                # Background job manager
│   ├── crony.py             # Cron job scheduler
│   └── screenshot.py        # Screen capture
├── skills/                  # Agent skills for self-install
│   ├── bg-jobs/SKILL.md
│   ├── crony/SKILL.md
│   ├── desktop-notifications/SKILL.md
│   ├── screenshot/SKILL.md
│   └── edge-tts/SKILL.md
├── pyproject.toml           # Package metadata
└── README.md                # User-facing docs
```

---

## Common Infrastructure

### CLI Framework
All tools use **Click** (`click >= 8.1.0`) for CLI argument parsing and command routing.

### Output Formatting
**Rich** (`rich >= 13.0.0`) provides table output for list commands.

### Storage Pattern
- **JSON files** for structured data (jobs, metadata)
- **Temp directories** for transient data (screenshots, bg job output)
- **Home directory** (`~`) for persistent config (`.crony/`)

---

## Component: notify

### File
`src/agentcli_helpers/notify.py`

### Entry Point
```python
notify = "agentcli_helpers.notify:main"
```

### Implementation

```
send_notification(title, body) -> bool
    |
    +-- platform.system()
    |       |
    |       +-- "Linux"  --> subprocess.run(["notify-send", title, body])
    |       |
    |       +-- "Darwin" --> subprocess.run(["osascript", "-e", script])
    |       |
    |       +-- "Windows" --> subprocess.run(["powershell", "-Command", ps_script])
    |
    +-- error handling: CalledProcessError, FileNotFoundError
```

### Platform Details

**Windows (PowerShell):**
- Uses `Windows.UI.Notifications.ToastNotificationManager`
- Creates XML toast template with title and body
- Shows toast via `CreateToastNotifier("AgentCLI").Show()`

**macOS (AppleScript):**
- Uses `display notification "{body}" with title "{title}"`
- Requires no additional dependencies

**Linux (notify-send):**
- Requires `libnotify` (usually pre-installed)
- Falls back to nothing if unavailable

### Input Handling
- Arguments: `notify "Title" "Body"`
- Pipe: `echo "text" | notify "Title"` — reads from `sys.stdin`
- Explicit pipe: `cat file | notify "Title" -` — body = "-"

---

## Component: bg

### File
`src/agentcli_helpers/bg.py`

### Entry Point
```python
bg = "agentcli_helpers.bg:main"
```

### Commands
- `bg run "CMD"` — Create background job
- `bg list` — List all jobs
- `bg status JOB_ID` — Get job metadata
- `bg read JOB_ID` — Read stdout
- `bg logs JOB_ID` — Read stdout + stderr
- `bg rm JOB_ID` — Remove job

### Storage

```
{tempdir}/agentcli_bgjobs/
└── {job_id}/
    ├── meta.json    # {"id", "cmd", "started_at", "status", "pid"}
    ├── stdout.txt   # Captured stdout
    └── stderr.txt   # Captured stderr
```

### Job Lifecycle

```
create_job(cmd) -> job_id
    |
    +-- generate_id() --> 6-char alphanumeric
    |
    +-- mkdir(job_dir)
    |
    +-- write(meta.json, status="running")
    |
    +-- subprocess.Popen(cmd, shell=True, ...)
    |       |
    |       +-- Windows: CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS
    |       |
    |       +-- Unix: start_new_session
    |
    +-- update(meta.json, pid=proc.pid)
    |
    +-- return job_id
```

### Status Checking

```
check_job_alive(job_id) -> bool
    |
    +-- get job metadata (pid)
    |
    +-- Windows: subprocess.run(["tasklist", "/FI", f"PID eq {pid}"])
    |       --> True if pid in output
    |
    +-- Unix: os.kill(pid, 0)
            --> True if no OSError
```

### List Behavior

```
list_jobs() -> list[dict]
    |
    +-- iterate JOBS_DIR/
    |
    +-- for each job:
    |       |
    |       +-- if status == "running" and not check_job_alive():
    |               |
    |               +-- update_job_status("completed")
    |
    +-- sort by started_at descending
    |
    +-- return jobs
```

---

## Component: crony

### File
`src/agentcli_helpers/crony.py`

### Entry Point
```python
crony = "agentcli_helpers.crony:main"
```

### Commands
- `crony add NAME SCHEDULE "CMD"` — Add job
- `crony list` — List jobs
- `crony rm NAME` — Remove job
- `crony run NAME` — Run immediately
- `crony logs NAME` — View logs

### Storage

```
~/.crony/
├── jobs.json    # {"job_name": {...}}
└── logs/
    └── {name}.log
```

### Schedule Parsing

```
parse_schedule(schedule_str) -> dict
    |
    +-- check for "every " or "each " prefix
    |
    +-- if recurring:
    |       |
    |       +-- interval_to_cron(interval) --> cron expression
    |       |
    |       +-- return {"type": "recurring", "interval", "cron_expr"}
    |
    +-- else (one-off):
            |
            +-- dateparser.parse(schedule, settings)
            |
            +-- return {"type": "once", "schedule", "next_run"}
```

### Interval to Cron Mapping

| Input | Cron Output |
|-------|-------------|
| `1m`, `5m`, `15m`, `30m` | `*/{n} * * * *` |
| `1h`, `2h`, `6h`, `12h` | `0 */{n} * * *` |
| `1d`, `24h` | `0 0 * * *` |
| `1w` | `0 0 * * 0` |
| `monday` - `sunday` | `0 0 * * {0-6}` |
| `weekday` | `0 0 * * 1-5` |
| `weekend` | `0 0 * * 0,6` |

### OS Integration

**Linux/macOS (crontab):**
```
register_job_crontab(job)
    |
    +-- subprocess.run(["crontab", "-l"]) --> current crontab
    |
    +-- remove lines containing "CRONY:{name}"
    |
    +-- append "{cron_expr} {cmd}  # CRONY:{name}"
    |
    +-- subprocess.run(["crontab", "-"], input=new_cron)
```

**Windows (Task Scheduler):**
```
register_job_task_scheduler(job)
    |
    +-- schtasks /Delete /TN CRONY_{name} /F  # Remove existing
    |
    +-- if recurring:
    |       |
    |       +-- schtasks /Create /TN CRONY_{name} /TR {cmd} /SC DAILY ...
    |
    +-- else (one-off):
            |
            +-- schtasks /Create /TN CRONY_{name} /TR {cmd} /SC ONCE /ST {time} /SD {date}
```

### Sync Mechanism

```
sync_jobs() -> dict
    |
    +-- load_jobs() --> stored jobs
    |
    +-- scan_os_scheduler() --> OS jobs with CRONY markers
    |
    +-- for each OS job not in stored:
    |       |
    |       +-- add to stored (recovery)
    |
    +-- for each stored job not in OS:
    |       |
    |       +-- re-register with OS
    |
    +-- save_jobs(stored)
    |
    +-- return stored
```

---

## Component: screenshot

### File
`src/agentcli_helpers/screenshot.py`

### Entry Point
```python
screenshot = "agentcli_helpers.screenshot:main"
```

### Commands
- `screenshot [OUTPUT]` — Capture screen

### Auto-Naming

```
auto_name_screenshot() -> Path
    |
    +-- timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    |
    +-- return {tempdir}/agentcli_screenshots/screenshot_{timestamp}.png
```

### Capture Strategy

```
main(output)
    |
    +-- if output provided:
    |       |
    |       +-- resolve to absolute path
    |       |
    |       +-- mkdir parent
    |
    +-- else:
            |
            +-- output_path = auto_name_screenshot()
    |
    +-- if HAS_MSS:
    |       |
    |       +-- screenshot_mss(output_path)
    |
    +-- else:
            |
            +-- screenshot_native(output_path)
```

### mss Capture

```
screenshot_mss(output_path) -> bool
    |
    +-- with mss.mss() as sct:
    |       |
    |       +-- monitors = sct.monitors
    |       |
    |       +-- if len(monitors) > 1:
    |       |       |
    |       |       +-- monitor = monitors[0]  # All monitors combined
    |       |
    |       +-- else:
    |               |
    |               +-- monitor = monitors[1]  # Primary
    |       |
    |       +-- sct_img = sct.grab(monitor)
    |       |
    |       +-- mss.tools.to_png(sct_img.rgb, sct_img.size, output=output_path)
    |
    +-- return True
```

### Native Fallbacks

| Platform | Tool | Command |
|----------|------|---------|
| Linux | gnome-screenshot | `gnome-screenshot -f {path}` |
| Linux | scrot | `scrot {path}` |
| Linux | ImageMagick | `import -window root {path}` |
| Linux | flameshot | `flameshot full -p {path}` |
| macOS | screencapture | `screencapture -x {path}` |
| Windows | PowerShell | `System.Drawing.Bitmap` + `Graphics.CopyFromScreen` |

---

## Dependencies Graph

```
click >= 8.1.0          <-- All tools (CLI framework)
    |
rich >= 13.0.0          <-- bg, crony (table output)
    |
dateparser >= 1.2.0    <-- crony (optional, natural language)
    |
schedule >= 1.2.0      <-- crony (optional, not currently used)
    |
mss >= 9.0.0           <-- screenshot (optional, primary capture)
    |
pillow >= 10.0.0       <-- screenshot (optional, mss dependency)
```

---

## Error Handling Patterns

1. **Tool not found** — `FileNotFoundError` → user-friendly message → exit 1
2. **Subprocess failure** — `CalledProcessError` → capture stderr → exit 1
3. **Invalid input** — ValueError/ClickUsageError → message → exit 1
4. **Missing optional dep** — ImportError at runtime → install hint → exit 1

---

## Platform Detection

All tools use `platform.system()` to detect OS:
- `"Windows"` — Windows
- `"Darwin"` — macOS
- `"Linux"` — Linux

For process detection:
- Windows: `sys.platform == "win32"`
- Unix: `sys.platform != "win32"`