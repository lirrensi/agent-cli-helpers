# Implementation Plan: bg restart command

## Overview
Add `bg restart <job_ref>` command that:
- Keeps the same job record (same UID, name, directory)
- Kills the process if alive
- Starts a new process with the same command
- Appends to existing stdout/stderr files (like ctrl+c + run again)
- No restart counters or extra metadata

## Changes

### 1. Extract process launching logic from `create_job`
Create a new helper function `launch_process_for_job(uid, cmd, stdout_path, stderr_path)` that handles:
- Cross-platform subprocess launching (Windows PowerShell/cmd vs Unix shell)
- Output file redirection
- PID capture
- Returns the new PID

This will be called from both `create_job` and the new `restart`.

### 2. Refactor `create_job` to use the new helper
Split `create_job` into:
- Record creation logic (UID, name, directory setup, index, metadata)
- Process launching via `launch_process_for_job`

### 3. Add `restart` command
Add a new CLI command `bg restart <job_ref>` that:
- Validates job exists and has a valid command
- Kills process if alive using existing `kill_process(pid)`
- Calls `launch_process_for_job` with existing UID, cmd, and file paths
- Updates metadata with new pid and started_at
- Prints the job name on success

### 4. Update skill documentation
Add restart usage to `skills/bg-jobs/SKILL.md`:
```bash
bg restart sleepy-pytest
```

## Files to modify
- `src/agentcli_helpers/bg.py` - Main implementation
- `skills/bg-jobs/SKILL.md` - Documentation

## Edge cases handled
- Job doesn't exist
- Job record corrupted or missing command
- Process already dead (just start new one)
