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
uv tool install agentcli-helpers
```

## Usage

`bg` runs commands in your platform shell. On Windows it prefers PowerShell 7, then Windows PowerShell, then `cmd.exe`, launches jobs without a visible console window when PowerShell is available, and expects shell syntax that matches the shell you expect.

### Run a Background Job
```bash
bg run "python long_script.py"
# Returns: sleepy-pytest (friendly name)
```

```powershell
bg run "python --version"
```

### List All Jobs
```bash
bg list
bg list --json
```

`bg list` shows live job details including name, UID, record state, process state, status, PID, start time, elapsed runtime, and command.

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

### Read Job Output
```bash
bg read sleepy-pytest   # stdout only
bg logs sleepy-pytest   # stdout + stderr
```

### Remove Job
```bash
bg rm sleepy-pytest
```

### Restart Job
```bash
bg restart sleepy-pytest
```

`bg restart <ref>` kills the process if alive and starts a new one with the same command. Output appends to existing stdout/stderr files (like ctrl+c + run again). The job keeps the same UID and name.

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
- `records/<uid>/meta.json` - Canonical job metadata (`uid`, `name`, `cmd`, `pid`, `status`, `started_at`, optional `finished_at`, optional `exit_code`, and live runtime fields)
- `records/<uid>/meta.json` - Canonical job metadata (`uid`, `name`, `cmd`, `pid`, `status`, `started_at`, optional `finished_at`, optional `exit_code`, and lightweight event fields such as `last_event_type`, `last_event_at`, `matched_pattern`, and `matched_stream`)
- `records/<uid>/stdout.txt` - Standard output
- `records/<uid>/stderr.txt` - Standard error
- `records/<uid>/exit_code.txt` - Persisted exit code

Windows note:
- PowerShell syntax works by default when `pwsh` or `powershell` is available
- Windows background jobs are started hidden, so there is no extra console window to close
- Use explicit `cmd.exe /d /c "..."` if you need cmd-specific syntax

## Status Values

- `running` - Process is still active
- `completed` - Process finished
- `failed` - Process exited with error
- `stale` - Record is healthy but PID is gone and no exit code was found
- `missing` / `corrupt` / `orphaned` - Record problem surfaced by `bg list` / `bg status`

`bg list` also shows a short update marker when a job has a notable event such as completion, failure, or matched output.

## Examples

```bash
# Download large file
bg run "curl -O https://example.com/large_file.zip"

# Run tests in background
bg run "pytest tests/ -v"

# Start a server
bg run "python -m http.server 8000"

# Check one job as JSON
bg status sleepy-pytest

# Check all running jobs
bg list

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
