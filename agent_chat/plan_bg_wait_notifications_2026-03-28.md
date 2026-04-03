# Plan: BG Wait Modes + Update Notifications
_Goal: add a completion wait mode, an output-match wait mode, and a lightweight update notification signal in `bg list` / `bg status` without turning the tool into a daemon._

---

# Checklist
- [x] Step 1: Lock the wait/notify UX
- [x] Step 2: Add state fields for match/completion notifications
- [x] Step 3: Implement `bg wait` and `bg wait-all`
- [x] Step 4: Surface update markers in `bg list` / `bg status`
- [x] Step 5: Update docs/skill text/examples
- [x] Step 6: Verify completion waits, match waits, and notification surfacing

---

## Context
- Current `bg` already refreshes live process state and terminal fields.
- Current storage uses a friendly name plus stable UID split, with file-backed records.
- There is no `wait` command yet.
- The user wants two wait modes:
  - wait until a job completes
  - wait until a string appears in stdout/stderr
- The user also wants `bg list` / `bg status` to surface the new update signal.

## Target Behavior
- `bg wait <job>` blocks until the job reaches a terminal state.
- `bg wait <job> --match PATTERN` blocks until PATTERN appears in stdout/stderr.
- `bg wait-all` waits for all known jobs to finish.
- `bg list` / `bg status` keep their current snapshot behavior, but also show a compact update marker when a job has a noteworthy event such as:
  - completed
  - failed
  - matched output
- Update markers should be lightweight and file-backed; no daemon, no DB.

## Scope Boundaries
- Do not add a daemon or long-running background service.
- Do not remove the current live-refresh behavior of `list/status`.
- Do not change unrelated tools.
- Keep the public UX compact; avoid introducing a large event system.

## Steps

### Step 1: Lock the wait/notify UX
Define the minimum CLI surface as:
- `bg wait JOB_REF`
- `bg wait JOB_REF --match PATTERN`
- `bg wait-all`

Optional flags if they fit cleanly:
- `--stdout`, `--stderr`, `--both`
- `--timeout SECONDS`
- `--notify`

Define the output-match rule:
- check the chosen output stream(s) incrementally while the job runs
- stop immediately when the pattern appears
- stop if the job exits first

Define the update marker rule:
- show a short notice in `list/status` when a job has a terminal or matched event worth surfacing
- keep the marker informational, not a new core status value unless needed

✅ Success: the command and marker behavior are explicit and compact.

### Step 2: Add state fields for match/completion notifications
Extend job metadata only as needed to record the last notable event, such as:
- `last_event_type`
- `last_event_at`
- `matched_pattern` (for match waits)
- `matched_stream` (stdout/stderr/both)

Keep the existing `status`, `record_state`, and `process_state` model intact.

If the implementation needs a read cursor or previous output offset, store it in a small, file-backed way that does not break existing records.

✅ Success: `bg` can remember and surface a completion/match event without a daemon.

### Step 3: Implement `bg wait` and `bg wait-all`
Add wait logic that polls the existing record and output files:
- resolve by friendly name or UID
- refresh process state while waiting
- for completion waits, return when terminal state is reached
- for match waits, return when the pattern is found in the chosen stream(s)
- for `wait-all`, iterate over all known jobs and block until all are terminal

If `--notify` is enabled and a desktop notification path is available, emit one when the wait condition is satisfied.

✅ Success: waiting works for both completion and output match.

### Step 4: Surface update markers in `bg list` / `bg status`
Update the rendered and JSON output so it can expose the new event signal, for example via:
- `last_event_type`
- `last_event_at`
- a short human-readable marker column in `list`

Preserve the existing live status refresh behavior.
Make sure `list/status` still clearly separate record problems from process state.

✅ Success: the new notification signal is visible in list/status without hiding current truth.

### Step 5: Update docs/skill text/examples
Align the canonical docs and user-facing copy:
- `docs/product.md`
- `docs/arch.md`
- `skills/bg-jobs/SKILL.md`
- `README.md` if examples change

Document both wait modes and the notification/update marker behavior.

✅ Success: docs explain the new waits and the new update marker clearly.

### Step 6: Verify completion waits, match waits, and notification surfacing
Test the following end to end:
- `bg wait <job>` on a short-lived job
- `bg wait <job> --match PATTERN` on a job that prints the pattern
- `bg wait-all` with multiple jobs
- `bg list` / `bg status` showing the new event marker
- timeout / no-match behavior if implemented

✅ Success: tests prove the new wait paths and the surfaced update marker.

---

## Verification Criteria
- Completion waits block until the job ends.
- Match waits unblock when the requested output appears.
- `wait-all` waits for all known jobs.
- `list/status` keep the live snapshot behavior and surface a compact update marker.
- No daemon or database is introduced.

Plan ready. Next: implement, then verify.
