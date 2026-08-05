# FILE: src/agent_sommelier/ttt.py
# PURPOSE: Personal tmux aliases — instant manager, new-session-from-cwd, and start-order index attach.
# OWNS: The `ttt` / `tttn` entry points and their dispatch logic on top of the tmx manager.
# EXPORTS: main (ttt), main_n (tttn), new_and_attach, _resolve_index, _auto_name
# DOCS: .agents/reports/plan_ttt_2026-08-06.md

"""ttt — personal tmux aliases: instant manager, new-session, index attach.

ttt        → interactive manager picker (same as ``tmx manager``)
ttt n      → create a new session from cwd and attach (same as ``tttn``)
ttt INDEX  → attach to a session by 0-based start-order index (oldest = 0)
ttt NAME   → attach to a session by name
"""

from __future__ import annotations

import os
import subprocess

import click

from agent_sommelier.tmx import (
    _find_tmux,
    _get_session_list,
    _session_exists,
    _set_scrollback,
    _tmux,
    run_manager,
)


def _auto_name() -> str:
    """Deterministic session name from cwd basename, deduped with -2, -3, ..."""
    base = os.path.basename(os.getcwd())
    name = base.lower().replace(" ", "-") if base else "session"
    if not _session_exists(name):
        return name
    i = 2
    while _session_exists(f"{name}-{i}"):
        i += 1
    return f"{name}-{i}"


def _attach(name: str) -> None:
    """Echo the attach banner, then block in ``tmux attach -t NAME``."""
    click.echo(f"Attaching to {name} (detach: Ctrl+B d)")
    subprocess.run([_find_tmux(), "attach", "-t", name], check=False)


def new_and_attach() -> None:
    """Create a new detached session from cwd (auto-named, deduped) and attach."""
    name = _auto_name()
    _tmux(
        "new-session",
        "-d",
        "-s",
        name,
        "-x",
        "120",
        "-y",
        "40",
        "-c",
        os.getcwd(),
    )
    _set_scrollback(name)
    _attach(name)


def _resolve_index(target: str) -> str:
    """Map a 0-based start-order index (oldest = 0) to a live session name."""
    sessions = _get_session_list()  # already in start order (tmux session id)
    try:
        idx = int(target)
    except ValueError:
        raise click.ClickException(f"invalid index: {target!r}") from None
    if idx < 0 or idx >= len(sessions):
        if not sessions:
            raise click.ClickException("no sessions — run tttn")
        listing = ", ".join(f"{i}: {s['name']}" for i, s in enumerate(sessions))
        raise click.ClickException(f"no such index {idx} — current sessions: {listing}")
    return sessions[idx]["name"]


@click.command()
@click.argument("target", required=False)
def main(target: str | None) -> None:
    """ttt — attach or manage tmux sessions.

    No args: interactive session picker (same as tmx manager).

    n or new: create a new session from cwd and attach immediately.

    INDEX: attach to the session at that 0-based start-order index
    (oldest live session is 0; indices shift as sessions are killed).

    NAME: attach to a session by name.
    """
    if target is None:
        run_manager()
    elif target in ("n", "new"):
        new_and_attach()
    elif target.isdigit():
        _attach(_resolve_index(target))
    else:
        if not _session_exists(target):
            raise click.ClickException(f"no session named '{target}'")
        _attach(target)


@click.command()
def main_l() -> None:
    """tttl — dumb plain list: index | name | path (no TUI).

    Glance at the list, then `ttt INDEX` to jump in. Oldest session is 0.
    """
    sessions = _get_session_list()
    if not sessions:
        click.echo("no sessions — run tttn")
        return
    for i, s in enumerate(sessions):
        click.echo(f"{i} | {s['name']} | {s.get('path') or '-'}")


@click.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
def main_n() -> None:
    """tttn — create a new session from cwd and attach immediately.

    Extra arguments are ignored on purpose (typing habits).
    """
    new_and_attach()


if __name__ == "__main__":
    main()
