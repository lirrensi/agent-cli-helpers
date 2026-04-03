# Plan: BG Naming + State Redesign
_Goal: make `bg` easier to remember and safer to reason about by separating a human-friendly job name from the internal record ID, and by distinguishing record state from live process state._

---

# Checklist
- [x] Step 1: Lock the naming model and collision rules
- [x] Step 2: Introduce internal UID + name index storage
- [x] Step 3: Separate record state from process state
- [x] Step 4: Update `run`, `list`, `status`, `read`, `logs`, and `rm`
- [x] Step 5: Update docs and skill text to match the new model
- [x] Step 6: Verify naming, lookup, collision, and corruption cases

---

## Context
- Current implementation lives in `src/agentcli_helpers/bg.py`.
- Current storage is `tempdir/agentcli_bgjobs/<job_id>/meta.json` plus stdout/stderr files.
- Current public ID is a 6-char random string used as both user-facing identifier and storage key.
- Current status refresh logic mixes stored metadata, process liveness, and terminal exit metadata in one flow.

## Target Behavior
- Public names should be easy to remember and read.
- Name shape should be: `<word>-<commandroot>`.
- `<word>` comes from one mixed pool of adjective/noun words.
- If the friendly name collides, append a short suffix such as `-k7`.
- Internal storage should use a hidden stable UID, separate from the friendly name.
- `bg list` and `bg status` should distinguish:
  - whether the record exists and is readable
  - whether the process is alive
  - whether the metadata is corrupted or incomplete
- Runtime process checks should be performed on `list` and `status`, but the live probe should not silently erase record problems.

## Scope Boundaries
- Do not add a daemon.
- Do not add a database.
- Do not change unrelated tools (`notify`, `crony`, `screenshot`).
- Do not remove the ability to reference a job by an internal UID if it is helpful for backward compatibility.

## Steps

### Step 1: Lock the naming model and collision rules
Define the public name generator as:
- one word from a shared adjective/noun pool
- a command-root slug derived from the submitted command
- a short suffix only when needed for uniqueness

Define the command-root rule so it stays short and useful:
- prefer the first executable or the command’s main noun/token
- normalize to lowercase alphanumerics plus hyphen
- truncate aggressively so names stay compact

Define collision handling:
- if a generated friendly name is already taken, append a short suffix
- if that still collides, retry with a new suffix until unique

✅ Success: the naming rules are explicit, compact, and collision-safe.

### Step 2: Introduce internal UID + name index storage
Refactor `bg` storage to separate:
- `uid` = internal storage key
- `name` = human-friendly display/lookup name

Add an index file or equivalent lookup layer that maps:
- friendly name → uid
- uid → record path

Keep `meta.json` as the canonical job record, but expand the record to carry both identity layers and the derived display name.

Ensure new jobs cannot overwrite older records on a name collision.

✅ Success: one job can be looked up by friendly name without exposing that name as the storage key.

### Step 3: Separate record state from process state
Split job inspection into two independent signals:
- **record state**: record exists, missing, or corrupt
- **process state**: alive, dead, missing PID, zombie, or unknown

Derive the user-facing job status from those signals instead of mixing them together.

Suggested output fields:
- `uid`
- `name`
- `record_state`
- `process_state`
- `pid`
- `status`
- `finished_at`
- `exit_code`

If metadata cannot be parsed, surface that explicitly rather than pretending the job is normal.

✅ Success: a corrupted record is visibly distinct from a dead process.

### Step 4: Update command behavior
Update `bg run` to:
- generate the friendly name
- allocate a unique internal UID
- write the indexed record
- return the friendly name or both identifiers, depending on the final UX decision

Update `bg list` to:
- refresh process state live
- preserve record state separately
- render the more precise state model

Update `bg status` to:
- resolve by friendly name and/or UID
- return the same enriched model as `list`

Update `bg read`, `bg logs`, and `bg rm` to:
- resolve through the new index
- fail clearly when the record is missing or corrupted
- only kill processes when the process state confirms a live PID

✅ Success: all subcommands work through the new naming/index layer.

### Step 5: Update docs and skill text
Align the canonical docs and skill copy with the new model:
- `docs/product.md`
- `docs/arch.md`
- `skills/bg-jobs/SKILL.md`
- `README.md` if user-facing examples change

Document the new naming pattern, collision behavior, and record/process distinction.

✅ Success: docs describe the new user-facing name and the internal UID separation.

### Step 6: Verify naming, lookup, collision, and corruption cases
Test the following cases end to end:
- a normal job run with a generated friendly name
- a collision that forces suffix generation
- `list` and `status` on a live job
- `list` and `status` after process exit
- missing record
- corrupted `meta.json`
- stale PID / orphaned process record

✅ Success: the output clearly distinguishes healthy jobs, dead processes, and broken records.

---

## Verification Criteria
- Friendly names are short and memorable.
- Name collisions never overwrite a prior job.
- Internal UID and public name are separate.
- `list/status` report record state and process state independently.
- Corrupt metadata is explicit, not silently normalized away.

Plan ready. If you want, next I can turn this into the actual implementation work plan and run it.
