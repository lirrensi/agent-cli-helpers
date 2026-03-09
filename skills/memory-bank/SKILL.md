---
name: memory-bank
description: "Use this skill to save, recall, or organize memories across conversations. Trigger on: 'remember this', 'save this', 'note this', 'what did we discuss about...', 'check your notes', 'do you remember', 'recall'. Also use proactively when the user seems to be resuming previous work, referencing past decisions, or when you discover something genuinely worth preserving for future sessions. This skill is NOT limited to code — use it for business decisions, personal notes, meeting recaps, research, project management, creative work, client history, anything."
---

# Agent Memory Bank

A persistent memory system for storing knowledge that survives across conversations — for any domain: code, business, personal, research, creative work, client management, and more.

**Default location:** `./memory/` (create if it doesn't exist)

---

## Core Philosophy

- **Prefer history over rewrites**: When a task meaningfully changes, create a new file rather than erasing what came before.
- **But don't spam**: If you're actively working on something and a file already exists for it, update it.
- **Never delete memory files** — mark outdated ones with `status: superseded` instead.
- **Write for resumption**: Notes should be self-contained — a future session with zero context should still understand them.
- **Light touch**: Don't save everything. Save things that were hard to figure out, or that would be annoying to reconstruct.

---

## Proactive Saving

Since this skill is loaded, memory is clearly valued here — lean into it. Save without being asked when you encounter:

- Something that took real effort to figure out (research, debugging, negotiation, comparison)
- A decision with non-obvious reasoning — why X over Y
- Information that would be painful to reconstruct if this conversation ended
- Dead ends and failed approaches — saves future sessions from repeating them
- In-progress work with clear next steps
- Anything the user seems to care about that isn't obvious from context alone

Applies to any domain — code, business, personal, creative, research, client work, anything.

---

## File Naming

```
YYYY_MM_DD_meaningful_name.md
```

Examples — notice these span many domains:
- `2025_03_09_client_acme_preferences.md`
- `2025_03_09_auth_bug_root_cause.md`
- `2025_03_10_recipe_modifications_sourdough.md`
- `2025_03_10_q1_marketing_decisions.md`
- `2025_03_11_travel_visa_requirements.md`
- `2025_03_11_novel_chapter3_outline.md`

Multiple files per day are normal and encouraged.

---

## Creating a Memory File

Use your native file tools to create and edit memory files.

**Template:**
```
---
summary: "One line — specific enough to know if you need to read this"
created: YYYY-MM-DD
tags: [optional, tags]
---

# Title

[Write freely — use whatever sections make sense for the domain]
```

**Some section ideas** (use only what fits):
- **Context** — why this matters, background
- **Key Decisions** — what was decided and why
- **Details / Findings** — the actual content worth saving
- **People / Contacts** — who's involved
- **Next Steps** — what to do next
- **Didn't Work** — dead ends to avoid

There's no required structure. A memory for a client call looks different from a debugging session — that's fine.

---

## Editing an Existing Memory

Use your native file editing tools to update memory files.

---

## Searching Memories

### Quick orientation (run this first when memories feel relevant)
```bash
ls -1t ./memory/*.md | head -20
```
This shows the 20 most recently modified files — a fast orientation to what's here.

### Read summaries across all files
```bash
rg "^summary:" ./memory/ -l --no-ignore
```

### Search by keyword (full text)
```bash
rg "keyword" ./memory/ --no-ignore -i
```

### Search summaries only
```bash
rg "^summary:.*keyword" ./memory/ --no-ignore -i
```

### Search by tag
```bash
rg "^tags:.*keyword" ./memory/ --no-ignore -i
```

After finding relevant files, **read them** using your native file tools. The summary tells you if it's worth reading; reading gives you the actual context.

---

## When to Check Memories

Default behavior: check memories when the task feels like it might connect to prior work — e.g. the user references a past decision, says "like we discussed", or you're about to re-research something familiar.

This default can be overridden by the environment. A system prompt may instruct you to always check memories, or only check when explicitly asked — follow those instructions. This skill describes the fallback when no such instruction exists.

When checking: run the quick orientation command, glance at recent file names, and read the ones that seem relevant.

---

## When to Save

No strict rules — use judgment. Good candidates:
- Something that took real effort to figure out
- A decision with non-obvious reasoning behind it
- Information you'd lose if this conversation ended now
- Anything the user explicitly wants remembered

Not worth saving:
- Easily googleable facts
- Transient scratchpad work
- Anything the user will obviously remember themselves

---

## When to Create vs Update a File

**Create a new file** when:
- Starting a meaningfully different task or topic
- Picking up work on a new day or new session with no existing file for this topic
- You want to preserve a snapshot of a prior state

**Update an existing file** when:
- You're continuing the same task within the same workflow
- A file for this topic already exists and is still active
- Adding new findings, progress, or corrections to ongoing work

The goal is to avoid both extremes: don't spam new files for every small update, but don't silently overwrite history either. When in doubt, update if a file exists and create if it doesn't.

When something evolves across clearly distinct phases, new files tell a useful story:

```
2025_03_09_supplier_negotiation_initial.md
2025_03_10_supplier_negotiation_counteroffer.md
2025_03_11_supplier_negotiation_final_terms.md
```

To mark a file as outdated, add `status: superseded` to its frontmatter — don't delete it.

---

## File Organization

By default, memory files live flat in `./memory/` with no subfolders. However, you may encounter or be instructed to use a structured layout (e.g. `./memory/clients/`, `./memory/projects/`). Follow whatever structure exists; if none exists, stay flat.