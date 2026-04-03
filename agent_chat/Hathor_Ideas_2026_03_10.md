---
summary: "Idea scan for AgentCLI Helpers focused on fancy skills, CLI UX gaps, and missing coding-agent capabilities"
created: 2026-03-10
tags: [ideas, skills, cli, ux, coding-agents]
---

# AgentCLI Helpers - Idea Scan

## Vibe Summary

- This codebase feels like a sharp pocketknife that wants to become a field kit.
- The biggest lie it tells is: "simple CLI tools that just work" when the real differentiator is "agent-grade workflows with almost no ceremony."
- If this project was a person, it would wear a black hoodie, carry six perfectly chosen shell aliases, and secretly want a pelican case full of labeled adapters.

## What Exists Now

- Core primitives are strong and intentionally small: `notify`, `bg`, `crony`, `screenshot`, plus skills for `tmux`, `edge-tts`, and `memory-bank` in `docs/product.md` and `docs/arch.md`.
- The current product shape is "desktop superpowers for AI agents" rather than a generic CLI toolbox.
- The repo already leans toward cross-platform wrappers, no-daemon ergonomics, and skill-first distribution via `skills/*/SKILL.md`.
- The next win is not more random tools; it is better agent workflow coverage around handoff, visibility, capture, and recovery.

## Quick Wins

**[DX Lens] - `doctor` Preflight Command**
|- Why: Make installation and platform drift visible before the agent hits a dead end.
|- How: Add `src/agentcli_helpers/doctor.py`, wire a `doctor` script in `pyproject.toml`, and add skill snippets that check for `notify-send`, `schtasks`, `tmux`/`psmux`, `mss`, `edge-tts`, and common PATH issues.
|- Effort: S
|- Breaking: NO
|- Unlocks: Better install UX, support bundles, safer auto-install flows
|- Score: Impact 7 x Compound 1.2 x Confidence 0.9 = 7.56

=> idk, each skill already has install if not instruction!

**[Integration Lens] - Clipboard Skill (`clip get|set|files|image`)**
|- Why: Agents constantly bridge terminal output to humans and browsers, and clipboard is the missing zero-friction handoff layer.
|- How: Add `src/agentcli_helpers/clipboard.py` plus `skills/clipboard/SKILL.md` with cross-platform backends (`pbcopy`, `xclip`/`wl-copy`, PowerShell clipboard APIs) and stdin/stdout-friendly flows.
|- Effort: S
|- Breaking: NO
|- Unlocks: Browser workflows, artifact sharing, quick approvals
|- Score: Impact 8 x Compound 1.2 x Confidence 0.9 = 8.64

=> HELL NO privacy nightamare level maxx

**[User Journey Lens] - `open` / `reveal` Skill**
|- Why: Agents often end with "the file is here" when they could open the file, folder, URL, or screenshot for the user instantly.
|- How: Add `src/agentcli_helpers/openit.py` with `open`, `reveal`, and `browse` commands using `start`, `open`, and `xdg-open`; publish `skills/open/SKILL.md` with agent trigger guidance.
|- Effort: S
|- Breaking: NO
|- Unlocks: Better browser automation handoffs, artifact review, richer report flows
|- Score: Impact 7 x Compound 1.2 x Confidence 0.9 = 7.56

=> good idea! but... cant they do it with native os stuff? open link/ open folder... default os handling

**[Observability Lens] - `bg wait`, `bg tail`, and `bg run --notify`**
|- Why: Background jobs are useful now, but they still make the user poll manually like it is 2009.
|- How: Extend `src/agentcli_helpers/bg.py` with blocking wait, follow-mode logs, exit-code capture, and optional notification hooks via `notify`.
|- Effort: S
|- Breaking: NO
|- Unlocks: Scriptable pipelines, scheduled jobs, incident capture
|- Score: Impact 8 x Compound 1.2 x Confidence 0.9 = 8.64

=> hm! we assume cli tool is blocking and not async. 
we can do `wait` command like that watches for regex, but its still like function, send and wait
! we have some in swarmkeeper!

**[Trust & Assurance Lens] - `crony preview` + "next 5 runs"**
|- Why: Human-readable scheduling only feels safe when users can see exactly what it will do before they trust it.
|- How: Extend `src/agentcli_helpers/crony.py` with a preview subcommand that shows parsed time, cron translation, next runs, and platform registration details before `add`.
|- Effort: S
|- Breaking: NO
|- Unlocks: Safer scheduling, easier docs, future dry-run policies
|- Score: Impact 7 x Compound 1.0 x Confidence 1.0 = 7.00

=> like crony list?

**[Subtraction Lens] - Consistent Output Contract (`--plain`, `--json`, `--quiet`, `--explain`)**
|- Why: Smaller CLI tools get noisy or inconsistent fast; a tiny output contract makes them feel like one product instead of six scripts.
|- How: Standardize flags and exit semantics across `src/agentcli_helpers/*.py`, document the contract in `docs/product.md`, and mirror it in every skill example.
|- Effort: S
|- Breaking: YES
|  |- Breaks: Some human-readable defaults and help text patterns change.
|  |- Migration: Keep old behavior as aliases for one release, document the new contract.
|  `- Worth it?: A predictable interface is compound value for every future command.
|- Unlocks: Better scripting, agent parsing, reduced verbosity complaints
|- Score: Impact 8 x Compound 1.5 x Confidence 0.9 = 10.80

=> json mode maybe nice! but... raw text is their native interface

**[Integration Lens] - Remote Notifications via Apprise Adapters**
|- Why: Desktop notifications are good, but long-running agent work increasingly finishes away from the desk.
|- How: Extend `notify` or add `notify route` with Apprise-style backends for Slack, Discord, email, and Pushbullet; document simple webhook recipes in `skills/desktop-notifications/SKILL.md`.
|- Effort: S
|- Breaking: NO
|- Unlocks: Remote approvals, job alerts, scheduled workflows
|- Source: `https://aider.chat/docs/usage/notifications.html`
|- Score: Impact 6 x Compound 1.2 x Confidence 0.9 = 6.48

=> kinda meh, would require login/auth keys to be stored insie folder, unless u have a cli tool like tg notify

## Medium Bets

**[Architecture Lens] - Searchable Skill Registry + Capability Discovery**
|- Why: Once the skill count grows, README tables stop being a product surface and start becoming a hiding place.
|- How: Add a generated `skills/index.json` plus a small `helpers skills list|search|show` CLI that reads frontmatter from `skills/*/SKILL.md` and exposes triggers, install steps, and examples.
|- Effort: M
|- Breaking: NO
|- Unlocks: Skill marketplace feel, recommendations, auto-trigger ranking
|- Score: Impact 8 x Compound 1.5 x Confidence 0.9 = 10.80

=> u install all what need anyway

**[New Primitive Lens] - Artifact Primitive for All Tools**
|- Why: Logs, screenshots, job output, and future captures should be first-class artifacts instead of random files in temp folders.
|- How: Add `src/agentcli_helpers/artifacts.py` to mint artifact IDs, metadata, previews, and retention info; make `bg`, `screenshot`, and future tools emit artifact metadata.
|- Effort: M
|- Breaking: NO
|- Unlocks: Dashboards, bundles, memory links, share/export flows
|- Score: Impact 8 x Compound 1.5 x Confidence 0.8 = 9.60

=> why tho...

**[DX Lens] - File Watcher Skill (`watch path --run ... --notify`)**
|- Why: Agents and developers repeatedly re-run commands after file changes, and that loop wants to be one declarative command.
|- How: Add `src/agentcli_helpers/watch.py` with filesystem watching, debounce, optional background mode, and notification hooks; publish `skills/watch/SKILL.md` with build/test examples.
|- Effort: M
|- Breaking: NO
|- Unlocks: Local automation, CI-like feedback, live coding loops
|- Score: Impact 7 x Compound 1.2 x Confidence 0.9 = 7.56

=> not sure its often used, usuall u dont do parallel edits anyway... and its blocking!

**[Integration Lens] - Browser Automation Skill in This Repo**
|- Why: For agent users, screenshots without browser control are like giving a mechanic a mirror but no wrench.
|- How: Add a repo-native `skills/browser-automation/SKILL.md` that wraps Playwright or the existing browser skill pattern with install guidance, screenshot capture, form filling, and extraction recipes.
|- Effort: M
|- Breaking: NO
|- Unlocks: UI testing, approval loops, web research, multimodal artifacts
|- Source: `https://docs.anthropic.com/en/docs/claude-code/overview`
|- Score: Impact 8 x Compound 1.2 x Confidence 0.8 = 7.68

=> no, playwright has own skill in own repo 

**[Composability Lens] - `workflow` Recipes That Compose `bg`, `crony`, `notify`, and `tmux`**
|- Why: The repo already has LEGO bricks; users now need a way to snap them together without rewriting glue every time.
|- How: Add `src/agentcli_helpers/workflow.py` with YAML or single-file recipe support for "run this in bg, alert on finish, then schedule a rerun" patterns; provide starter recipes under `examples/workflows/`.
|- Effort: M
|- Breaking: NO
|- Unlocks: Reusable automations, team sharing, semi-agentic operations
|- Score: Impact 8 x Compound 1.5 x Confidence 0.8 = 9.60

=> no, u want a workflow - do a bash script 

**[Artifact Lens] - `session-recap` / `run-report` Generator**
|- Why: Smaller tools usually do the task but do not leave behind a useful narrative artifact.
|- How: Add a report generator that composes job logs, command metadata, screenshots, and timestamps into Markdown under `agent_chat/` or `reports/`, using the artifact primitive.
|- Effort: M
|- Breaking: NO
|- Unlocks: Memory-bank integration, audits, PR summaries, support bundles
|- Score: Impact 7 x Compound 1.5 x Confidence 0.9 = 9.45

**[Trust & Assurance Lens] - `record` / `replay` for Risky Commands**
|- Why: Coding agents feel safer when users can preview, record, and replay actions instead of trusting one-off shell incantations.
|- How: Add a wrapper that stores command, cwd, env subset, outputs, and artifacts, then lets the user replay or dry-run them later; connect it to `bg` and future workflows.
|- Effort: M
|- Breaking: NO
|- Unlocks: Undo stories, audit trails, incident repros
|- Source: `https://docs.anthropic.com/en/docs/claude-code/overview`
|- Score: Impact 8 x Compound 1.5 x Confidence 0.8 = 9.60

=> require too much integration, cant(

## Big Swings

**[New Primitive Lens] - `agentctl` Unified Front Door**
|- Why: Right now the repo ships sharp individual commands; a single front door would make it feel like a coherent agent operations platform.
|- How: Add `src/agentcli_helpers/agentctl.py` with subcommands for jobs, schedule, capture, notify, artifacts, and skills discovery, while keeping `bg`, `crony`, `notify`, and `screenshot` as compatibility shims.
|- Effort: L
|- Breaking: YES
|  |- Breaks: Docs and muscle memory gradually shift from many top-level commands to one umbrella command.
|  |- Migration: Keep existing binaries as wrappers and print migration hints.
|  `- Worth it?: It gives the project a memorable surface area and makes future additions easier to discover.
|- Unlocks: Capability discovery, consistent UX, richer dashboards
|- Score: Impact 9 x Compound 1.5 x Confidence 0.8 = 10.80

=> we cant have it all, each part is modular and u install only what want

**[Inversion Lens] - `workflow record` -> Auto-Generate a New Skill**
|- Why: The most valuable skills are the ones users accidentally invent by repeating themselves.
|- How: Observe repeated command sequences, prompts, and docs snippets, then scaffold `skills/<name>/SKILL.md`, install checks, and example commands automatically.
|- Effort: L
|- Breaking: NO
|- Unlocks: Internal skill marketplace, team knowledge capture, self-evolving toolset
|- Score: Impact 10 x Compound 1.5 x Confidence 0.7 = 10.50

=> skill creator is already default everywhere 

**[Integration Lens] - Remote Control Surface for Long-Running Agent Work**
|- Why: Bigger coding agents increasingly let users kick off work, leave, and come back from another surface; smaller tools usually strand the session in one terminal.
|- How: Build a thin remote layer over `bg`, `workflow`, and artifacts with webhook-triggered status pages, chat notifications, and approval callbacks.
|- Effort: L
|- Breaking: NO
|- Unlocks: Mobile monitoring, async approvals, team operations
|- Source: `https://docs.anthropic.com/en/docs/claude-code/overview`
|- Score: Impact 9 x Compound 1.5 x Confidence 0.7 = 9.45

=> tmux has it but its too complex!

**[Artifact Lens] - `capture` Bundles for Debugging and Handoff**
|- Why: A single command that grabs screenshot, clipboard, git diff, logs, and environment summary would feel like cheating in the best way.
|- How: Add `src/agentcli_helpers/capture.py` on top of artifacts, `screenshot`, clipboard, and `bg`; emit a timestamped Markdown+ZIP bundle with previews and shareable paths.
|- Effort: L
|- Breaking: NO
|- Unlocks: Incident reporting, support tickets, async reviews, memory snapshots
|- Score: Impact 9 x Compound 1.5 x Confidence 0.8 = 10.80

=> nah, too much info! grab only what need 

## Wild Ideas

**[Toy Maker Hat] - ✨ MAGIC: Ambient Agent Cockpit**
|- Why: Turn invisible background activity into a delightful little mission-control view instead of making users stitch status together from scattered commands.
|- How: Use Rich/Textual to build a TUI showing live jobs, scheduled tasks, recent screenshots, alerts, and memory/report artifacts from the new artifact registry.
|- Effort: Unknown
|- Breaking: NO
|- Unlocks: Unified operations UX, demos, team adoption
|- Score: Impact 8 x Compound 1.5 x Confidence 0.6 = 7.20

**[Lazy Genius Hat] - ✨ MAGIC: Failure Auto-Triage Bot**
|- Why: On command failure, the tool could automatically collect logs, take a screenshot, summarize what happened, and notify the user before they even ask.
|- How: Build this on `bg`, `capture`, `notify`, and `session-recap`, with opt-in policies such as "on non-zero exit, create incident bundle and ping Slack".
|- Effort: Unknown
|- Breaking: NO
|- Unlocks: Reliability posture, support automation, delight through saved time
|- Score: Impact 9 x Compound 1.5 x Confidence 0.6 = 8.10

**[Time Traveler Hat] - ✨ MAGIC: Time-Machine Query for Jobs and Sessions**
|- Why: Users should be able to ask "what changed since this morning?" or "show me the last successful run that looked like this" without spelunking temp folders.
|- How: Store normalized event history for jobs, schedules, captures, and reports; expose a query CLI like `agentctl history --since 9am --type failed`.
|- Effort: Unknown
|- Breaking: NO
|- Unlocks: Replay, analytics, trust, richer agent memory
|- Score: Impact 8 x Compound 1.5 x Confidence 0.5 = 6.00

## Pattern From Other Agents

- Claude Code leans hard into shared memories, hooks, remote surfaces, multiple agents, and recurring tasks; this repo can steal the smallest useful versions of those ideas without bloating into a platform immediately.
- Aider already proves that notifications, scripting, repo-aware commands, and clear in-chat affordances matter; the equivalent here is a stricter output contract plus workflow and artifact layers.
- Smaller tools usually fail in three places: no handoff surface, no report artifact, and no confidence story before risky actions.

## If You Only Build 3 Next

1. `Searchable Skill Registry + Capability Discovery`
2. `Artifact Primitive for All Tools`
3. `capture Bundles for Debugging and Handoff`

## Magic In The List

- `Ambient Agent Cockpit` - makes the invisible visible and gives the repo a demo-worthy face.
- `Failure Auto-Triage Bot` - turns "ugh, now I have to investigate" into an automatic support artifact.
- `Time-Machine Query for Jobs and Sessions` - gives tiny CLI tools an unusually premium memory and observability story.
- `workflow record -> Auto-Generate a New Skill` - lets the product learn from repeated use instead of waiting for manual curation.

## Theme Emerging

This repo should not become "more commands." It should become the best low-ceremony agent operations kit: discoverable skills, first-class artifacts, safer async workflows, and a few magical handoff features that make small CLI tools feel much bigger than they are.

---

# Second Run - Net-New Ideas Only

These are intentionally new proposals only. I excluded the first-pass themes (`doctor`, clipboard, open/reveal, output contract, skill registry, artifacts, watch, workflows, reports, record/replay, unified front door, capture bundles, cockpit, auto-triage, time-machine query).

## Vibe Summary

- This codebase still feels like a tight belt of utilities, but the missing jump is from "helpers" to "agent interaction layer."
- The biggest lie now is: "the shell is the interface" when the real missing product is "how the agent and human meet in the middle."
- If this project was a person, it would wear cargo pants with excellent tools, but still no clipboard for decisions, approvals, or stage lighting.

## Quick Wins

**[Subtraction Lens] - `pick` Selector Skill**
|- Why: Replace verbose back-and-forth with a tiny chooser for files, jobs, branches, or options.
|- How: Add `src/agentcli_helpers/pick.py` plus `skills/pick/SKILL.md`; wrap `fzf`, `gum`, or a minimal Rich prompt so stdin lists become single or multi-select output.
|- Effort: S
|- Breaking: NO
|- Unlocks: Approval menus, disambiguation, job picking, quick command palettes
`- Score: Impact 8 x Compound 1.2 x Confidence 0.9 = 8.64

**[Trust & Assurance Lens] - `approve` Gate Skill**
|- Why: Bigger coding agents feel premium because they stop at the edge and ask for one crisp decision before acting.
|- How: Add `src/agentcli_helpers/approve.py` plus `skills/approve/SKILL.md`; support `approve text`, `approve command`, and `approve diff` with approve/reject/edit choices and optional timeout defaults.
|- Effort: S
|- Breaking: NO
|- Unlocks: Safe destructive actions, plan review, scheduled confirmations, human-in-the-loop flows
|- Source: `https://docs.devin.ai/work-with-devin/interactive-planning`
`- Score: Impact 9 x Compound 1.5 x Confidence 0.9 = 12.15

=> cant unless integrated into harness

**[Artifact Lens] - `cast` Terminal Recording Skill**
|- Why: A 20-second replay is often more useful than 500 lines of logs when handing off or showing off.
|- How: Add `skills/cast/SKILL.md` and optional `src/agentcli_helpers/cast.py` wrapping `asciinema` or `vhs`; emit `.cast`, SVG, or GIF from a command or tmux pane.
|- Effort: S
|- Breaking: NO
|- Unlocks: Demos, support repros, docs snippets, social proof
`- Score: Impact 7 x Compound 1.2 x Confidence 0.9 = 7.56

=> usually our terminals not interactive... u can do it in tmux tho

**[Integration Lens] - `serve` Micro Preview Skill**
|- Why: Agents keep generating HTML, markdown reports, and screenshots, but the last mile is still "go open this yourself."
|- How: Add `src/agentcli_helpers/serve.py` plus `skills/serve/SKILL.md`; start a throwaway local server, auto-pick a free port, and optionally open the browser.
|- Effort: S
|- Breaking: NO
|- Unlocks: Local report preview, artifact review, web demo flows
`- Score: Impact 7 x Compound 1.2 x Confidence 0.9 = 7.56

=> YES, exactly like open in skill! but native os methods?

**[Integration Lens] - `extract` Document Skill**
|- Why: Smaller agent tools still get clumsy around PDFs, DOCX files, archives, and "can you just read this thing?" moments.
|- How: Add `src/agentcli_helpers/extract.py` plus `skills/extract/SKILL.md`; normalize PDF, DOCX, ZIP, and HTML into plain text or a folder tree using lightweight optional backends.
|- Effort: S
|- Breaking: NO
|- Unlocks: Better context ingestion, handoffs, OCR pipelines, report generation
`- Score: Impact 8 x Compound 1.2 x Confidence 0.8 = 7.68

=> Oh, fuckiing yes, that's a good one. One to unstructured Python library to read anything binary crap into correct and clean markdown. You can even take it partially, like you want to look at a table, you don't need to drag a big pandas in there. You use this one and get table headers real quick. 

## Medium Bets

**[Integration Lens] - ✨ MAGIC: `screenread` OCR Skill**
|- Why: Turn screenshots and UI captures into searchable text so the agent can act on visible state instead of treating the screen like a black box.
|- How: Add `src/agentcli_helpers/screenread.py` plus `skills/screenread/SKILL.md`; accept image/PDF input or chain from `screenshot`, run OCR, and emit plain text with optional bounding boxes.
|- Effort: M
|- Breaking: NO
|- Unlocks: UI debugging, screenshot triage, accessibility checks, document ingestion
`- Score: Impact 8 x Compound 1.2 x Confidence 0.8 = 7.68

=> I don't know, usually screenshot tool is a bit of a miss here, because we allow screenshot tool but we don't have special computer use right here. It's completely separate thing. So, I don't know. You can get bounded boxes, but how would you use them? 

**[Trust & Assurance Lens] - `checkpoint` Skill**
|- Why: Premium agents have save points; smaller CLIs still rely on vibes and raw git history.
|- How: Add `skills/checkpoint/SKILL.md` and maybe `src/agentcli_helpers/checkpoint.py`; create named snapshots via git worktrees, lightweight patch files, or branch bookmarks with resume notes.
|- Effort: M
|- Breaking: NO
|- Unlocks: Safe experimentation, undo stories, pause/resume, multi-agent branching
|- Source: `https://www.tembo.io/blog/coding-cli-tools-comparison`
`- Score: Impact 9 x Compound 1.5 x Confidence 0.9 = 12.15

=> Usually, checkpoints are either entirely on git or integrated into harness, I don't know. 

**[Composability Lens] - ✨ MAGIC: `handoff` Capsule Skill**
|- Why: The missing feature in small agent tools is not more execution; it is clean transfer of intent, state, and next steps.
|- How: Add `src/agentcli_helpers/handoff.py` plus `skills/handoff/SKILL.md`; capture cwd, branch, touched files, last commands, and open questions into `agent_chat/handoff_*.md` for another agent or future self.
|- Effort: M
|- Breaking: NO
|- Unlocks: Resumable sessions, subagent delegation, async collaboration, better memory
|- Source: `https://cursor.com/`
`- Score: Impact 9 x Compound 1.5 x Confidence 0.9 = 12.15

=> this is unUsually, checkpoints are either entirely on git or integrated into harness, I don't know. usual, because they have compaction in most of a harnesses, but could be useful for, I don't know, when you want to do it anyway. Because current problem, that compact skill, oh sorry, the compact inside the harness just does it in place, it doesn't save into a file. You have to manually tailor it to save into a file first, huh, well, it could be useful, like, just take the compaction prompt from open code and with explicit writing into a file, so you could really. Or, you know, it could be like, like a checkpoint, when you go to sleep. You run, you ask, get the skill and save a checkpoint, and it saves everything worked before, even if session survived many compactions and so on. 

But honestly this is literally just one asking, save our progress into a file. 

**[DX Lens] - ✨ MAGIC: `squawk` Output Compactor**
|- Why: The repo's biggest UX complaint is verbosity, and the clever move is not less information - it is better layering of information.
|- How: Add `src/agentcli_helpers/squawk.py`; run any command, keep the raw log, but print a terse summary, first failure, and "show more" hints with optional folding for long stderr.
|- Effort: M
|- Breaking: NO
|- Unlocks: Quieter agent sessions, cleaner CI use, easier human scanning, future dashboards
|- Source: `https://clig.dev/`
`- Score: Impact 9 x Compound 1.5 x Confidence 0.8 = 10.80

=> Well, currently we already have BASH output truncation. It's just usually they run either in full PTY mode, like Tmux, or running without PTY, so it's not interactive. And the tools itself detect, like, how would you be cleaning up the crap in there? Unless, I don't know, usually they output, no tool outputs your binary stream, they just text stream, which behaves weirdly, I don't know how we would implement it. 

**[Observability Lens] - `jobtop` Monitor Skill**
|- Why: `bg` can tell you a job exists, but not whether it is healthy, wedged, or quietly eating 8 GB of RAM.
|- How: Add `src/agentcli_helpers/jobtop.py` plus `skills/jobtop/SKILL.md`; map `bg` PIDs to live CPU, memory, elapsed time, and optional threshold notifications.
|- Effort: M
|- Breaking: NO
|- Unlocks: Performance triage, stall detection, smarter background automation
`- Score: Impact 7 x Compound 1.2 x Confidence 0.9 = 7.56

=> I think we should, for backgrounds, should just add the status, something like that, so, oh, we have background list, why not also add the actual modification, actual stats, could be cool, can we do it? 

**[Integration Lens] - `portshare` Tunnel Skill**
|- Why: Agents generate local previews and webhook endpoints, but remote review still dies at localhost.
|- How: Add `skills/portshare/SKILL.md` and optional wrapper over `cloudflared` or `ngrok`; return a temporary public URL, lifetime, and shutdown command.
|- Effort: M
|- Breaking: NO
|- Unlocks: Mobile review, webhook demos, async approvals, external testing
`- Score: Impact 8 x Compound 1.2 x Confidence 0.8 = 7.68

=> Wait, I think it's too complicated. It actually should be. It's not our responsibility to manage tunnels. You set up it completely different way. I don't know, for which you have to somehow have an account, how to login, how to set up, it's before, it's not like one of thingy. 

**[New Primitive Lens] - `window` Desktop Targeting Skill**
|- Why: Right now the desktop is only accessible as "whole screen" when many tasks really want "this app" or "that window."
|- How: Add `src/agentcli_helpers/window.py` plus `skills/window/SKILL.md`; list windows, focus one, capture active window, and return coordinates for follow-up tooling.
|- Effort: M
|- Breaking: NO
|- Unlocks: Better screenshots, OCR regions, future UI automation, less noisy capture
`- Score: Impact 8 x Compound 1.5 x Confidence 0.8 = 9.60

=> I wonder if we already could do it in PowerShell, however, I remember where accessibility API is horrible, and which is not our responsibility in the first place, it's computer use skill, which we do not use here. 

## Big Swings

**[Architecture Lens] - `mission` Task Folder Primitive**
|- Why: Top coding agents feel more trustworthy because work has stages; smaller tools dump plan, execution, and review into one stream.
|- How: Add `src/agentcli_helpers/mission.py`; create a task folder with `plan.md`, `notes.md`, `approval.txt`, `checkpoint.diff`, and `result.md`, then expose subcommands to move work through those stages.
|- Effort: L
|- Breaking: NO
|- Unlocks: Handoffs, checkpoints, approvals, reproducible task history
|- Source: `https://docs.devin.ai/work-with-devin/interactive-planning`
`- Score: Impact 9 x Compound 1.5 x Confidence 0.8 = 10.80

=> While good in itself, I think it's meh, because everyone has their own workflow and own files. I don't want to force it on them. 

**[Trust & Assurance Lens] - `policy` Safety Rails for Helpers**
|- Why: Bigger agents win trust because they know what must ask first; small tools usually leave that entirely to prompt wording.
|- How: Add `src/agentcli_helpers/policy.py` plus a tiny `agent_policy.toml`; allow rules like `rm -> ask`, `git push -> ask`, `notify -> allow`, `screenshot -> deny outside repo`.
|- Effort: L
|- Breaking: YES
|  |- Breaks: Some existing "just run it" flows gain prompts or denials under active policy.
|  |- Migration: Ship disabled by default, then offer opt-in presets like `safe`, `balanced`, `autonomous`.
|  `- Worth it?: It gives the repo a real autonomy dial instead of one global trust level.
|- Unlocks: Team policies, safer unattended runs, enterprise adoption, approval UX
|- Source: `https://artificialanalysis.ai/insights/coding-agents-comparison`
`- Score: Impact 9 x Compound 1.5 x Confidence 0.8 = 10.80

=> Also, this is just a suggestion. You should not rely on it, it's awfully bad idea to rely that we would listen to you. It's decided on hardness level, not here. 

**[Brand Voice Lens] - `studio` Command Palette for Installed Skills**
|- Why: Once the helper set grows, memorizing command names becomes the opposite of "desktop superpowers."
|- How: Add `src/agentcli_helpers/studio.py`; present a fast TUI palette of installed tools/skills with search, recent actions, and generated copy-paste command previews.
|- Effort: L
|- Breaking: NO
|- Unlocks: Discoverability, onboarding, demos, lower skill-name tax
`- Score: Impact 8 x Compound 1.5 x Confidence 0.7 = 8.40

+> Well, you learned nothing. Commands exist. You just ask to do something, and it fetches the skill. 

## Wild Ideas

**[Toy Maker Hat] - ✨ MAGIC: Ambient Approval Orb**
|- Why: The weird-good version of approvals is not another prompt - it is a tiny local UI that glows when the agent needs a decision and stays out of the way otherwise.
|- How: Build a tiny tray app or floating TUI fed by `approve` and `mission`; clicking it reveals pending choices, diffs, screenshots, or command previews.
|- Effort: Unknown
|- Breaking: NO
|- Unlocks: Human-in-loop delight, remote-ish local control, memorable brand identity
`- Score: Impact 8 x Compound 1.2 x Confidence 0.6 = 5.76

+> We can't do it without interfacing with hordes 

## Pattern From Other Agents - New Takeaways

- The feature gap is less about raw coding power and more about workflow state: approvals, checkpoints, handoffs, and resumability are where premium agents feel different.
- CLI UX best practices still point the same way: terse success, richer failure, machine-readable edges, and progressive disclosure instead of giant output dumps.
- This repo has a rare opportunity to own the desktop side of that equation: not a full IDE agent, but the best human-agent boundary tools in the terminal.

## If You Could Only Build 3 Next

1. `checkpoint` Skill
2. `handoff` Capsule Skill
3. `approve` Gate Skill

## Magic In The List

- `screenread` OCR Skill - makes the screen queryable instead of merely visible.
- `handoff` Capsule Skill - turns "I lost the thread" into a reusable product feature.
- `squawk` Output Compactor - solves verbosity by design instead of by deleting information.
- `Ambient Approval Orb` - makes approvals feel like product, not plumbing.

## Theme Emerging

The second-pass direction is clear: stop adding more isolated helpers and start adding the missing collaboration layer around them. The strongest additions are the ones that make the agent easier to trust, easier to resume, and less annoying to read.
