---
name: bg-jobs
description: >
  Run and manage background jobs from the terminal. Use this skill when the user wants
  to execute long-running commands in the background, track job status, read job output,
  or manage multiple concurrent processes. Provides friendly-name tracking, status monitoring,
  and output capture for background tasks.
---

# Background Jobs Skill

Run and manage background jobs from the terminal, with friendly names, live runtime details, wait support, and persisted exit metadata.

## Installation Check

```bash
bg --help
```

If not installed:
```bash
uv tool install "git+https://github.com/lirrensi/agent-sommelier"
```

## Command name: `bg` vs `bgj`

The CLI installs two entry points for the same command: **`bg`** and **`bgj`**.

- `bg` collides with the **shell builtin** of the same name (POSIX job control — "move jobs to the background"). Builtins always win over PATH lookup, so on **bash/zsh/fish** `bg --help` shows the shell's builtin, not this tool.
- **Use `bgj` on bash/zsh/fish** — it is collision-free. On PowerShell/cmd (no `bg` builtin) plain `bg` works.
- If you prefer `bg` everywhere, alias it in your shell profile: `alias bg='env bg'` (bash/zsh). (`command bg` does NOT work — it resolves to the builtin too.)

All examples below use `bg`; substitute `bgj` on POSIX shells.

## Usage

`bg` runs commands in your platform shell. `bg run` returns immediately after creating the handle; a detached worker finishes the launch in the background and jobs appear running unless failure is proven. A short best-effort PID probe updates the record a few seconds later when it can. On Windows it prefers PowerShell 7, then Windows PowerShell, then `cmd.exe`, launches jobs without a visible console window when PowerShell is available, and expects shell syntax that matches the shell you expect.

### Run a Background Job
```bash
bg run "python long_script.py"
# Returns: sleepy-pytest (friendly name)
```

Run from a specific directory (the process actually runs there, and the directory is recorded):
```bash
bg run --cwd /path/to/repo "pytest tests/ -v"
```

```powershell
bg run "python --version"
```

### List Jobs
```bash
bg list            # running jobs only (running / launching / starting)
bg list --all      # everything: Running section + dim Settled section
bg list --all --page 2   # page through long lists (20 rows per page)
bg list --json     # running jobs as JSON (same default filter)
bg list --all --json     # full JSON dump (never paginated)
```

`bg list` shows live job details including name, UID, record state, process state, status, PID, start time, elapsed runtime, the recorded working directory (Dir column), and command. Tables longer than 20 rows print a `Showing X-Y of Z (page N/N)` footer plus a `use --page N` hint.

### Check Job Status
```bash
bg status sleepy-pytest
```

`bg status <ref>` refreshes the job before printing JSON. Use either the friendly name or UID. Running jobs may include `elapsed_seconds`, `memory_bytes`, and `cpu_percent`. Finished jobs can also include `finished_at` and `exit_code`.

### Wait for Completion
```bash
bg wait sleepy-pytest
```

### Wait for Output
```bash
bg wait sleepy-pytest --match "needle"
```

### Wait for All Jobs
```bash
bg wait-all
```

### Timeouts & Agent Safety

`bg wait` and `bg wait-all` apply an **agent-protection timeout** by default: **120 seconds** in non-TTY (agent/script) mode, infinite in TTY (interactive) mode. Detection: if either stdin or stdout is not a TTY, the cap fires.

Override the cap with `--timeout N` (float seconds, `N >= 0`):
- `--timeout 0` disables the cap and waits until the job ends.
- `--timeout 300` waits up to 5 minutes.

When the cap fires:
- A clear message is written to **stderr** (not stdout) explaining the wait loop — not the job — was terminated, naming the still-running job(s) and elapsed times, and listing the re-poll commands.
- Exit code is `0`. The stderr message is the contract: agents should detect a timed-out wait by reading stderr, not by the exit code.

**Recommended re-poll pattern:**
```bash
# Wait hit the 120s cap. The job is still running. Decide next step:
bg status sleepy-pytest           # check current state
bg wait sleepy-pytest --timeout 300   # wait up to 5 more minutes
bg wait sleepy-pytest --timeout 0     # wait until the job ends (no cap)
bg logs sleepy-pytest             # read partial output
```

In an interactive TTY terminal, the default behavior is unchanged (wait forever; `ctrl+c` to abort). The 120s cap only activates when the CLI is invoked as a subprocess, which is the common case for LLM agents.

### Read Job Output
```bash
bg read sleepy-pytest            # full stdout
bg read sleepy-pytest --tail     # only output since the last tail read
bg logs sleepy-pytest            # stdout + stderr
```

`bg read <ref> --tail` prints only new output and remembers the read position per job, so repeated calls never re-print old content — ideal for watching a running job without re-reading the whole file. `bg read` / `bg logs` print a `cwd: <path>` header when the job records a working directory.

### Remove Job
```bash
bg rm sleepy-pytest
```

### Prune Non-Running Jobs
```bash
bg prune
```

Deletes every job that is not currently running, including stale or broken records.

### Restart Job
```bash
bg restart sleepy-pytest
```

`bg restart <ref>` kills the process if alive and starts a new one with the same command and the same recorded working directory. Output appends to existing stdout/stderr files (like ctrl+c + run again). The job keeps the same UID and name.

## Workflow Pattern

```bash
# Bash / zsh
JOB_NAME=$(bg run "python train_model.py")
bg status $JOB_NAME
bg read $JOB_NAME
```

```powershell
# PowerShell
$jobName = bg run "python train_model.py"
bg status $jobName
bg read $jobName
```

## Job Storage

Jobs keep runtime state in your OS temp directory under `agentcli_bgjobs/`:
- `index.json` - Friendly-name and UID lookup index
- `records/<uid>/meta.json` - Canonical job metadata (`uid`, `name`, `cmd`, `cwd`, `pid`, `status`, `started_at`, optional `finished_at`, optional `exit_code`, optional `record_issue`, `last_read_offset`, and live runtime fields)
- `records/<uid>/meta.json` - Canonical job metadata (`uid`, `name`, `cmd`, `pid`, `status`, `started_at`, optional `finished_at`, optional `exit_code`, optional `record_issue`, and lightweight event fields such as `last_event_type`, `last_event_at`, `matched_pattern`, and `matched_stream`)
- `records/<uid>/stdout.txt` - Standard output
- `records/<uid>/stderr.txt` - Standard error
- `records/<uid>/exit_code.txt` - Persisted exit code

Terminal jobs are automatically pruned: keep them for at least 1 hour, cap history at 32 jobs, and evict the oldest terminal jobs first. Running jobs are never evicted automatically.

Windows note:
- PowerShell syntax works by default when `pwsh` or `powershell` is available
- Windows background jobs are started hidden, so there is no extra console window to close
- Use explicit `cmd.exe /d /c "..."` if you need cmd-specific syntax

## Status Values

- `running` - Process is still active
- `launching` - Internal-only launch state; user-facing status is shown as running until failure is proven
- `completed` - Process finished
- `failed` - Process exited with error
- `stale` - Record is healthy but PID is gone and no exit code was found
- `missing` / `corrupt` / `orphaned` - Record problem surfaced by `bg list` / `bg status`

Launch failures keep the handle and mark the record `failed` instead of deleting it.

`bg list` also shows a short update marker when a job has a notable event such as completion, failure, or matched output.

## Examples

```bash
# Download large file
bg run "curl -O https://example.com/large_file.zip"

# Run tests in background
bg run "pytest tests/ -v"

# Run from a specific repo directory
bg run --cwd /path/to/repo "pytest tests/ -v"

# Start a server
bg run "python -m http.server 8000"

# Check one job as JSON
bg status sleepy-pytest

# Check all running jobs
bg list

# See everything, including finished jobs
bg list --all

# Page through a long history
bg list --all --page 2

# Watch live output without re-printing old lines
bg read sleepy-pytest --tail

# Wait for a job to finish
bg wait sleepy-pytest

# Wait for a log line to appear
bg wait sleepy-pytest --match "ready"

# Wait for all known jobs
bg wait-all

# Read merged logs
bg logs sleepy-pytest

# Restart a job
bg restart sleepy-pytest
```

```powershell
# Native PowerShell command
bg run "Get-Process | Sort-Object CPU -Descending | Select-Object -First 5"

# Force cmd syntax when needed
bg run "cmd.exe /d /c dir"
```
