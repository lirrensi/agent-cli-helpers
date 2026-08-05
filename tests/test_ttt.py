# FILE: tests/test_ttt.py
# PURPOSE: Hermetic integration tests for ttt/tttn aliases and the tmx manager index/path data.
# COVERS: session list fields (created/path), start-order sorting, index resolution,
#         new-session-from-cwd + attach, name dedupe, CLI dispatch, error paths.

from __future__ import annotations

import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import click.testing
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from agent_sommelier import tmx, ttt

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner() -> click.testing.CliRunner:
    return click.testing.CliRunner()


@pytest.fixture
def make_session():
    """Create a detached session with a start dir; kill all created at teardown."""
    created: list[str] = []

    def _make(name: str, cwd: str | None = None) -> str:
        tmx._tmux(
            "new-session", "-d", "-s", name, "-x", "120", "-y", "40",
            "-c", cwd or os.getcwd(),
        )
        created.append(name)
        return name

    yield _make
    for name in created:
        tmx._tmux("kill-session", "-t", name)


@pytest.fixture
def fake_attach(monkeypatch):
    """Replace ttt._attach with a recorder; returns the list of attached names."""
    attached: list[str] = []
    monkeypatch.setattr(ttt, "_attach", lambda name: attached.append(name))
    return attached


def _unique_dir(tmp_path: Path, label: str) -> Path:
    """A fresh subdirectory whose basename is a valid, unique session name."""
    d = tmp_path / f"{label}-{uuid.uuid4().hex[:8]}"
    d.mkdir()
    return d


def _unique_session(prefix: str = "ttt") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# _get_session_list: created/path fields + start-order sort
# ---------------------------------------------------------------------------


def test_get_session_list_reports_created_and_path(tmp_path, make_session):
    d1 = _unique_dir(tmp_path, "ttt-oldest")
    d2 = _unique_dir(tmp_path, "ttt-newest")
    name1 = _unique_session()
    name2 = _unique_session()
    make_session(name1, str(d1))
    time.sleep(1.1)  # distinct session_created seconds so order is unambiguous
    make_session(name2, str(d2))

    sessions = tmx._get_session_list()
    ours = [s for s in sessions if s["name"] in (name1, name2)]
    assert len(ours) == 2

    by_name = {s["name"]: s for s in ours}
    s1, s2 = by_name[name1], by_name[name2]

    # created is a real epoch, path is the start dir we passed
    assert (s1.get("created") or 0) > 0
    assert os.path.normcase(s1.get("path") or "") == os.path.normcase(str(d1))
    assert os.path.normcase(s2.get("path") or "") == os.path.normcase(str(d2))

    # oldest first (start order), and sorted by created
    assert ours[0]["name"] == name1
    assert ours == sorted(ours, key=lambda s: s.get("created", 0))


# ---------------------------------------------------------------------------
# Session-id ordering (real tmux) — mocked, since psmux stubs ids to $0
# ---------------------------------------------------------------------------


def test_get_session_list_orders_by_session_id_first(monkeypatch):
    """On real tmux, session_id ($0, $1, ...) is exact start order, even when
    creation epochs tie or disagree. psmux stubs all ids to $0, so on Windows
    the fallback is the creation epoch."""
    from subprocess import CompletedProcess

    def _fake_tmux(*args, **kw):
        # Out-of-order ids on purpose: id must win over created/name.
        out = "\n".join(
            [
                "zeta\t2\tdetached\t500\tC:\\z\t$2",
                "beta\t1\tattached\t100\tC:\\b\t$1",
                "alpha\t1\tdetached\t100\tC:\\a\t$0",
            ]
        )
        return CompletedProcess(args=args, returncode=0, stdout=out, stderr="")

    monkeypatch.setattr(tmx, "_tmux", _fake_tmux)

    sessions = tmx._get_session_list()
    assert [s["name"] for s in sessions] == ["alpha", "beta", "zeta"]
    assert [s.get("sid") for s in sessions] == [0, 1, 2]
    # ttt index resolution agrees with the canonical order
    assert ttt._resolve_index("0") == "alpha"
    assert ttt._resolve_index("2") == "zeta"


def test_get_session_list_psmux_fallback_orders_by_created(monkeypatch):
    """psmux reports $0 for every session — order then falls back to the
    creation epoch, so oldest first still holds."""
    from subprocess import CompletedProcess

    def _fake_tmux(*args, **kw):
        out = "\n".join(
            [
                "late\t2\tdetached\t200\tC:\\l\t$0",
                "early\t1\tattached\t100\tC:\\e\t$0",
            ]
        )
        return CompletedProcess(args=args, returncode=0, stdout=out, stderr="")

    monkeypatch.setattr(tmx, "_tmux", _fake_tmux)

    sessions = tmx._get_session_list()
    assert [s["name"] for s in sessions] == ["early", "late"]
    assert ttt._resolve_index("0") == "early"


# ---------------------------------------------------------------------------
# Index resolution
# ---------------------------------------------------------------------------


def test_resolve_index_oldest_first(tmp_path, make_session):
    d1 = _unique_dir(tmp_path, "ttt-aa")
    d2 = _unique_dir(tmp_path, "ttt-bb")
    name_old = _unique_session()
    name_new = _unique_session()
    make_session(name_old, str(d1))
    time.sleep(1.1)  # distinct creation seconds (psmux ties within a second)
    make_session(name_new, str(d2))

    sessions = tmx._get_session_list()
    idx_old = next(i for i, s in enumerate(sessions) if s["name"] == name_old)
    idx_new = next(i for i, s in enumerate(sessions) if s["name"] == name_new)
    assert idx_old == 0  # oldest live session resolves to index 0
    assert idx_new > idx_old
    assert ttt._resolve_index(str(idx_old)) == name_old
    assert ttt._resolve_index(str(idx_new)) == name_new


def test_resolve_index_out_of_range_lists_available(tmp_path, make_session, runner):
    name = _unique_session()
    make_session(name, str(_unique_dir(tmp_path, "ttt-xx")))

    result = runner.invoke(ttt.main, ["5"])
    assert result.exit_code != 0
    assert "no such index 5 — current sessions:" in result.output
    assert name in result.output


def test_resolve_index_no_sessions_error(runner):
    if tmx._get_session_list():
        pytest.skip("live sessions present; no-session path not testable")
    result = runner.invoke(ttt.main, ["0"])
    assert result.exit_code != 0
    assert "no sessions — run tttn" in result.output


# ---------------------------------------------------------------------------
# new_and_attach: auto-name from cwd, dedupe, attach
# ---------------------------------------------------------------------------


def test_new_and_attach_uses_cwd_name(tmp_path, monkeypatch, fake_attach):
    work = _unique_dir(tmp_path, "new-attach")
    monkeypatch.chdir(work)
    expected = work.name.lower()

    ttt.new_and_attach()

    assert fake_attach == [expected]
    assert tmx._session_exists(expected)
    tmx._tmux("kill-session", "-t", expected)


def test_new_and_attach_dedupes_on_collision(tmp_path, monkeypatch, make_session, fake_attach):
    work = _unique_dir(tmp_path, "dedupe")
    monkeypatch.chdir(work)
    base = work.name.lower()
    make_session(base)  # occupy the plain name first

    ttt.new_and_attach()

    assert fake_attach == [f"{base}-2"]
    assert tmx._session_exists(f"{base}-2")
    tmx._tmux("kill-session", "-t", f"{base}-2")


def test_attach_invokes_real_tmux_attach_cmd(tmp_path, monkeypatch, make_session):
    name = _unique_session("at")
    make_session(name, str(_unique_dir(tmp_path, "ttt-attach")))

    # Only intercept the blocking attach call; everything else (has-session,
    # list-sessions...) must still hit the real binary via tmx._tmux.
    real_run = subprocess.run
    calls: list[list[str]] = []

    def _fake_run(args, **kw):
        if "attach" in args:
            calls.append(list(args))
            return None
        return real_run(args, **kw)

    monkeypatch.setattr(ttt.subprocess, "run", _fake_run)

    result = click.testing.CliRunner().invoke(ttt.main, [name])

    assert result.exit_code == 0
    assert calls and calls[0][:3] == [tmx._find_tmux(), "attach", "-t"] and calls[0][3] == name


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------


def test_main_no_target_delegates_to_run_manager(monkeypatch, runner):
    called: list[str] = []
    monkeypatch.setattr(ttt, "run_manager", lambda: called.append("run_manager"))
    result = runner.invoke(ttt.main, [])
    assert result.exit_code == 0
    assert called == ["run_manager"]


def test_main_n_shortcut_creates_and_attaches(tmp_path, monkeypatch, runner, fake_attach):
    work = _unique_dir(tmp_path, "cli-n")
    monkeypatch.chdir(work)
    name = work.name.lower()

    result = runner.invoke(ttt.main, ["n"])

    assert result.exit_code == 0
    assert fake_attach == [name]
    assert tmx._session_exists(name)
    tmx._tmux("kill-session", "-t", name)


def test_main_new_equals_n(tmp_path, monkeypatch, runner, fake_attach):
    work = _unique_dir(tmp_path, "cli-new")
    monkeypatch.chdir(work)
    name = work.name.lower()

    result = runner.invoke(ttt.main, ["new"])

    assert result.exit_code == 0
    assert fake_attach == [name]
    tmx._tmux("kill-session", "-t", name)


def test_main_index_attaches_to_resolved_name(tmp_path, make_session, runner, fake_attach):
    name = _unique_session("idx")
    make_session(name, str(_unique_dir(tmp_path, "ttt-idx")))

    sessions = tmx._get_session_list()
    idx = next(i for i, s in enumerate(sessions) if s["name"] == name)

    result = runner.invoke(ttt.main, [str(idx)])

    assert result.exit_code == 0
    assert fake_attach == [name]


def test_main_name_attaches(tmp_path, make_session, runner, fake_attach):
    name = _unique_session("nm")
    make_session(name, str(_unique_dir(tmp_path, "ttt-name")))

    result = runner.invoke(ttt.main, [name])

    assert result.exit_code == 0
    assert fake_attach == [name]


def test_main_unknown_name_errors(runner):
    result = runner.invoke(ttt.main, ["no-such-session-xyz"])
    assert result.exit_code != 0
    assert "no session named 'no-such-session-xyz'" in result.output


def test_main_n_ignores_extra_args(tmp_path, monkeypatch, runner, fake_attach):
    work = _unique_dir(tmp_path, "cli-main-n")
    monkeypatch.chdir(work)
    name = work.name.lower()

    result = runner.invoke(ttt.main_n, ["bogus", "--whatever"])

    assert result.exit_code == 0
    assert fake_attach == [name]
    tmx._tmux("kill-session", "-t", name)


def test_picker_renders_index_and_path(capsys):
    """Render the picker rows and confirm index + path show up, oldest first."""
    from rich.console import Console

    sessions: list[tmx._SessionInfo] = [
        {"name": "zeta", "windows": 2, "status": "detached", "created": 300, "path": r"C:\z"},
        {"name": "alpha", "windows": 1, "status": "attached", "created": 100, "path": r"C:\a"},
    ]
    # _get_session_list sorts by created; emulate that here (alpha first).
    ordered = sorted(sessions, key=lambda s: s.get("created", 0))
    console = Console(record=True)
    import agent_sommelier.tmx as tmx_mod

    original = tmx_mod.Console
    tmx_mod.Console = lambda: console  # type: ignore[assignment]
    try:
        tmx_mod._render_picker(ordered, cursor=1)
    finally:
        tmx_mod.Console = original

    out = console.export_text()
    assert " 0 " in out and "alpha" in out and "C:\\a" in out
    assert " 1 " in out and "zeta" in out and "C:\\z" in out
    assert out.index("alpha") < out.index("zeta")
