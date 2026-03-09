# Plan: BG and Crony Richer Output
_Done looks like `bg` showing live process/runtime details and `crony list` showing upcoming execution time, with docs and package metadata aligned._

---

# Checklist
- [x] Step 1: Add runtime inspection dependency metadata
- [x] Step 2: Extend `bg` job metadata helpers
- [x] Step 3: Enrich `bg list` output
- [x] Step 4: Enrich `bg status` output
- [x] Step 5: Add recurring next-run calculation to `crony`
- [x] Step 6: Enrich `crony list` output
- [x] Step 7: Verify `bg` behavior end to end
- [x] Step 8: Verify `crony` behavior end to end

---

## Context
- The implementation files are `src/agentcli_helpers/bg.py` and `src/agentcli_helpers/crony.py`.
- The package metadata file is `pyproject.toml`.
- The product spec is already updated in `docs/product.md`.
- The architecture spec is already updated in `docs/arch.md`.
- The current `bg` implementation stores only `id`, `cmd`, `started_at`, `status`, and `pid` in `meta.json` and does not report runtime resource usage.
- The current `crony` implementation stores schedule definitions but does not calculate the next run for recurring jobs.

## Prerequisites
- Work from repository root: `C:\Users\rx\001_Code\101_DevArea\AgentCLI_Helpers`.
- Use Python 3.10 or newer.
- Install project dependencies before verification with `uv sync` or equivalent local environment setup.
- If `uv sync` fails, stop and report the dependency resolution error. Do not continue to code verification.

## Scope Boundaries
- Do not modify `src/agentcli_helpers/notify.py`.
- Do not modify `src/agentcli_helpers/screenshot.py`.
- Do not add new CLI commands.
- Do not create a new `crony preview` command.
- Do not add the MarkItDown skill in this plan.

---

## Steps

### Step 1: Add runtime inspection dependency metadata
Open `pyproject.toml`.

Add `psutil>=6.0.0` to `[project].dependencies` so `bg` can collect cross-platform process stats.

Add `croniter>=3.0.0` to `[project.optional-dependencies].crony` so `crony` can calculate recurring next-run values.

Save `pyproject.toml`.

✅ Success: `pyproject.toml` contains `psutil>=6.0.0` in the main dependency list and `croniter>=3.0.0` in the `crony` optional dependency list.
❌ If failed: Restore `pyproject.toml` to the last saved state and stop. Report that package metadata could not be edited cleanly.

### Step 2: Extend `bg` job metadata helpers
Open `src/agentcli_helpers/bg.py`.

Add small helper functions that do the following:
- parse ISO timestamps safely
- calculate elapsed seconds from `started_at`
- inspect a live process by PID with `psutil.Process`
- refresh a job record with best-effort fields `elapsed_seconds`, `memory_bytes`, and `cpu_percent`
- mark a finished process with `finished_at` and `exit_code`

Keep the canonical stored fields `id`, `cmd`, `started_at`, `status`, and `pid` intact.

When a process is no longer alive, derive `status` from the exit code: `completed` for zero and `failed` for non-zero.

Persist enriched metadata back into `meta.json` when refreshing a job.

✅ Success: `src/agentcli_helpers/bg.py` contains dedicated helper functions for runtime inspection and terminal-state refresh, and the code path can store `finished_at` plus `exit_code` in job metadata.
❌ If failed: Remove partial helper code from `src/agentcli_helpers/bg.py`, return the file to the pre-step content, and stop. Report that `bg` metadata refresh logic could not be added safely.

### Step 3: Enrich `bg list` output
Open `src/agentcli_helpers/bg.py`.

Change the `list_jobs()` flow so every job is refreshed before sorting and rendering.

Change the human-readable table in `list_cmd()` to include these columns in this order: `ID`, `Status`, `PID`, `Started`, `Elapsed`, `Memory`, `Command`.

Format `Elapsed` into a short human-readable value such as `12s`, `3m 04s`, or `2h 11m`.

Format `Memory` into a short human-readable value such as `42 MB` or `1.2 GB`. If memory is unavailable, print `-`.

Keep `--json` output as a JSON array of enriched job objects.

✅ Success: `bg list` renders the new columns in the specified order and `bg list --json` returns enriched per-job objects with runtime fields when available.
❌ If failed: Revert only the `list_jobs()` and `list_cmd()` edits in `src/agentcli_helpers/bg.py`, keep Step 2 helper functions only if they are still valid, and stop. Report that `bg list` formatting could not be completed.

### Step 4: Enrich `bg status` output
Open `src/agentcli_helpers/bg.py`.

Change `status(job_id)` so the command refreshes the target job before printing JSON.

Make `bg status <job_id>` return the same enriched metadata model used by `bg list --json`, including `elapsed_seconds`, `memory_bytes`, `cpu_percent`, `finished_at`, and `exit_code` when known.

Keep the existing error behavior for missing job IDs.

✅ Success: `bg status <job_id>` prints refreshed JSON that includes terminal fields for finished jobs and runtime fields for running jobs.
❌ If failed: Revert only the `status(job_id)` edits in `src/agentcli_helpers/bg.py` and stop. Report that `bg status` could not be aligned with the richer metadata model.

### Step 5: Add recurring next-run calculation to `crony`
Open `src/agentcli_helpers/crony.py`.

Import `croniter` lazily or in the optional dependency block used by `crony`.

Add small helper functions that do the following:
- parse stored ISO timestamps safely
- calculate a normalized `next_run` value for one-off jobs
- calculate the next upcoming occurrence for recurring jobs from `cron_expr` using `croniter`
- return a copy of each stored job enriched with computed `next_run`

Do not overwrite the canonical schedule definition fields stored in `jobs.json` unless the implementation requires caching `next_run` for output consistency. If caching is added, keep the canonical schedule fields unchanged.

✅ Success: `src/agentcli_helpers/crony.py` contains explicit helper functions that can derive `next_run` for both one-off and recurring jobs.
❌ If failed: Remove partial next-run helper code from `src/agentcli_helpers/crony.py`, return the file to the pre-step content, and stop. Report that recurring next-run calculation could not be added safely.

### Step 6: Enrich `crony list` output
Open `src/agentcli_helpers/crony.py`.

Change `list_cmd()` so both normal list mode and `--sync` mode enrich jobs with computed `next_run` before rendering.

Change the human-readable table to include these columns in this order: `Name`, `Type`, `Schedule`, `Next Run`, `Command`.

Format `Next Run` as a readable timestamp. If `next_run` cannot be derived, print `unknown`.

Keep `--json` output as enriched job objects that include computed `next_run`.

✅ Success: `crony list` shows a `Next Run` column and `crony list --json` includes `next_run` for one-off and recurring jobs when derivable.
❌ If failed: Revert only the `list_cmd()` enrichment and formatting edits in `src/agentcli_helpers/crony.py`, keep Step 5 helper functions only if they are still valid, and stop. Report that `crony list` output could not be enriched.

### Step 7: Verify `bg` behavior end to end
From repository root, install dependencies with `uv sync` if the environment is not already current.

Run a background command that stays alive long enough to inspect, such as:

```bash
uv run bg run "python -c \"import time; time.sleep(20)\""
```

Capture the returned job ID.

Run these commands with the captured job ID:

```bash
uv run bg list
uv run bg list --json
uv run bg status <job_id>
```

After the sleep command exits, run:

```bash
uv run bg status <job_id>
uv run bg rm <job_id>
```

✅ Success: `bg list` shows `PID`, `Elapsed`, and `Memory`; `bg status <job_id>` shows runtime fields while running; the final `bg status <job_id>` shows `finished_at` and `exit_code`; `bg rm <job_id>` removes the record.
❌ If failed: Save the full command output to the execution report, do not modify more files, and stop. Report the exact command that failed and the exact output.

### Step 8: Verify `crony` behavior end to end
From repository root, create one recurring job and one one-off job.

Use commands in this pattern:

```bash
uv run --extra crony crony add test-hourly "every 1h" "python -c \"print('hourly')\""
uv run --extra crony crony add test-once "in 2h" "python -c \"print('once')\""
uv run --extra crony crony list
uv run --extra crony crony list --json
uv run --extra crony crony rm test-hourly
uv run --extra crony crony rm test-once
```

If the local scheduler blocks task creation on the current platform, stop after the first failing `crony add` command and report the scheduler error. Do not fake verification.

✅ Success: `crony list` shows a `Next Run` column with readable upcoming timestamps and `crony list --json` includes `next_run` fields for both test jobs.
❌ If failed: Save the full command output to the execution report, do not modify more files, and stop. Report the exact command that failed and the exact output.

---

## Verification
- `pyproject.toml` contains `psutil>=6.0.0` and `croniter>=3.0.0` in the correct dependency groups.
- `uv run bg list` renders the columns `ID`, `Status`, `PID`, `Started`, `Elapsed`, `Memory`, `Command`.
- `uv run bg status <job_id>` returns JSON with `elapsed_seconds`, `memory_bytes`, and terminal fields `finished_at` plus `exit_code`.
- `uv run --extra crony crony list` renders the columns `Name`, `Type`, `Schedule`, `Next Run`, `Command`.
- `uv run --extra crony crony list --json` returns job objects containing `next_run`.

## Rollback
- Revert code changes in `src/agentcli_helpers/bg.py`, `src/agentcli_helpers/crony.py`, and `pyproject.toml` with:

```bash
git checkout -- pyproject.toml src/agentcli_helpers/bg.py src/agentcli_helpers/crony.py
```

- Leave `docs/product.md` and `docs/arch.md` untouched unless a human explicitly asks to roll back the spec change.
- Remove verification jobs created during Step 8 with `uv run --extra crony crony rm <name>` if scheduler registration succeeded before rollback.

Plan complete. Handing off to Executor.
