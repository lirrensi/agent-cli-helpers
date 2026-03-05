---
name: bg-jobs
description: >
  Run and manage background jobs from the terminal. Use this skill when the user wants
  to execute long-running commands in the background, track job status, read job output,
  or manage multiple concurrent processes. Provides job ID tracking, status monitoring,
  and output capture for background tasks.
---

# Background Jobs Skill

Run and manage background jobs from the terminal.

## Installation Check

```bash
bg --help
```

If not installed:
```bash
uv tool install agentcli-helpers
```

## Usage

### Run a Background Job
```bash
bg run "python long_script.py"
# Returns: abc123 (job ID)
```

### List All Jobs
```bash
bg list
bg list --json
```

### Check Job Status
```bash
bg status abc123
```

### Read Job Output
```bash
bg read abc123   # stdout only
bg logs abc123   # stdout + stderr
```

### Remove Job
```bash
bg rm abc123
```

## Workflow Pattern

```bash
# 1. Start a long-running task
JOB_ID=$(bg run "python train_model.py")

# 2. Do other work...

# 3. Check if done
bg status $JOB_ID

# 4. Get results
bg read $JOB_ID
```

## Job Storage

Jobs are stored in `~/.bgjobs/<id>/`:
- `meta.json` - Job metadata (cmd, pid, status, timestamps)
- `stdout.txt` - Standard output
- `stderr.txt` - Standard error

## Status Values

- `running` - Process is still active
- `completed` - Process finished
- `failed` - Process exited with error

## Examples

```bash
# Download large file
bg run "curl -O https://example.com/large_file.zip"

# Run tests in background
bg run "pytest tests/ -v"

# Start a server
bg run "python -m http.server 8000"

# Check all running jobs
bg list
```
