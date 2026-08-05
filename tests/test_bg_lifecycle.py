# FILE: tests/test_bg_lifecycle.py
# PURPOSE: Cover bg lifecycle visibility: cwd recording/override, two-tier list with pagination, and tail reads.
# OWNS: End-to-end coverage for `bg run --cwd`, default cwd capture, list default/--all/pagination, read --tail offsets, restart cwd reuse, legacy records.
# DOCS: .agents/reports/plan_bg-lifecycle-2026-08-06.md, docs/product.md, docs/arch.md, skills/bg-jobs/SKILL.md

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BG_SRC = ROOT / "src"
sys.path.insert(0, str(BG_SRC))


class TestBgLifecycle(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp(prefix="bg_lifecycle_cli_"))
        self.jobs_root = self.temp_root / "agentcli_bgjobs"
        self.jobs_root.mkdir(parents=True, exist_ok=True)

        import agent_sommelier.bg as bg

        bg.JOBS_DIR = self.jobs_root
        bg.RECORDS_DIR = self.jobs_root / "records"
        bg.INDEX_FILE = self.jobs_root / "index.json"

    def cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(
            {
                "TEMP": str(self.temp_root),
                "TMP": str(self.temp_root),
                "TMPDIR": str(self.temp_root),
            }
        )

        script = textwrap.dedent(
            f"""
            import sys
            sys.path.insert(0, {str(BG_SRC)!r})
            from agent_sommelier import bg
            bg.FRIENDLY_WORDS = ['sleepy']
            sys.argv = ['bg', {", ".join(repr(a) for a in args)}]
            bg.main()
            """
        )

        return subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

    def wait_for_status(self, job_name: str, timeout: float = 8.0) -> dict:
        deadline = time.time() + timeout
        last_snapshot: dict | None = None
        while time.time() < deadline:
            status = self.cli("status", job_name)
            if status.returncode == 0:
                last_snapshot = json.loads(status.stdout)
                assert last_snapshot is not None
                if last_snapshot.get("pid") is not None:
                    return last_snapshot
            time.sleep(0.1)

        self.fail(f"Timed out waiting for pid metadata for {job_name}: {last_snapshot}")

    def write_index(self, records: dict[str, dict], names: dict[str, str]) -> None:
        payload = {"version": 1, "records": records, "names": names}
        (self.jobs_root / "index.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    def write_meta(self, uid: str, meta: dict) -> Path:
        record_dir = self.jobs_root / "records" / uid
        record_dir.mkdir(parents=True, exist_ok=True)
        (record_dir / "meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        return record_dir

    # --- 1. --cwd override: recorded AND actually used ---------------------

    def test_run_with_cwd_records_it_and_executes_there(self) -> None:
        work_dir = self.temp_root / "workdir"
        work_dir.mkdir(parents=True, exist_ok=True)

        run = self.cli(
            "run",
            "--cwd",
            str(work_dir),
            'python -c "import os,time; print(os.getcwd(), flush=True); time.sleep(20)"',
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        name = run.stdout.strip()

        status = self.wait_for_status(name)
        self.assertEqual(status["cwd"], str(work_dir))
        self.assertIn(status["status"], {"running", "completed"})

        # Job output proves the process actually ran in that directory.
        deadline = time.time() + 8
        content = ""
        while time.time() < deadline:
            read = self.cli("read", name)
            self.assertEqual(read.returncode, 0, read.stderr)
            content = read.stdout
            if str(work_dir) in content:
                break
            time.sleep(0.2)
        self.assertIn(str(work_dir), content)

        # Dir column in the list table surfaces the cwd (prefix survives the
        # ~40-char cell truncation).
        listed = self.cli("list", "--all")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertIn(str(work_dir)[:20], listed.stdout)

    # --- 2. default cwd = caller cwd ---------------------------------------

    def test_run_without_cwd_records_caller_cwd(self) -> None:
        run = self.cli(
            "run",
            'python -c "import os,time; print(os.getcwd(), flush=True); time.sleep(20)"',
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        name = run.stdout.strip()

        status = self.wait_for_status(name)
        self.assertEqual(status["cwd"], os.getcwd())

        deadline = time.time() + 8
        content = ""
        while time.time() < deadline:
            read = self.cli("read", name)
            self.assertEqual(read.returncode, 0, read.stderr)
            content = read.stdout
            if os.getcwd() in content:
                break
            time.sleep(0.2)
        self.assertIn(os.getcwd(), content)

    # --- 3. invalid --cwd fails cleanly with no record ---------------------

    def test_run_with_invalid_cwd_fails_without_record(self) -> None:
        bad_dir = self.temp_root / "does-not-exist-xyz"
        run = self.cli("run", "--cwd", str(bad_dir), 'python -c "print(1)"')
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("cwd is not a directory", run.stderr)

        self.assertFalse((self.jobs_root / "index.json").exists())
        records_dir = self.jobs_root / "records"
        self.assertFalse(records_dir.exists() and any(records_dir.iterdir()))

    # --- 4. default list hides settled; --all shows them --------------------

    def test_list_default_hides_settled_and_all_shows_them(self) -> None:
        run = self.cli("run", 'python -c "print(1)"')
        self.assertEqual(run.returncode, 0, run.stderr)
        name = run.stdout.strip()

        wait = self.cli("wait", name)
        self.assertEqual(wait.returncode, 0, wait.stderr)

        status = self.cli("status", name)
        self.assertEqual(json.loads(status.stdout)["status"], "completed")

        default_table = self.cli("list")
        self.assertEqual(default_table.returncode, 0, default_table.stderr)
        self.assertNotIn(name, default_table.stdout)

        default_json = self.cli("list", "--json")
        self.assertEqual(default_json.returncode, 0, default_json.stderr)
        self.assertEqual(json.loads(default_json.stdout), [])

        all_table = self.cli("list", "--all")
        self.assertEqual(all_table.returncode, 0, all_table.stderr)
        self.assertIn(name, all_table.stdout)

        all_json = self.cli("list", "--all", "--json")
        self.assertEqual(all_json.returncode, 0, all_json.stderr)
        jobs = json.loads(all_json.stdout)
        self.assertTrue(any(job["name"] == name for job in jobs))

    # --- 5. fabricated settled records: sections + pagination + json --------

    def test_list_all_paginates_and_json_is_full_dump(self) -> None:
        now = datetime.now()
        records: dict[str, dict] = {}
        names: dict[str, str] = {}
        for i in range(25):
            uid = f"settle{i:03d}"
            started_at = (now - timedelta(seconds=(i + 1) * 10)).isoformat()
            finished_at = (now - timedelta(seconds=(i + 1) * 10 - 5)).isoformat()
            record_dir = self.write_meta(
                uid,
                {
                    "uid": uid,
                    "id": uid,
                    "name": f"sleepy-{uid}",
                    "cmd": f'python -c "print({i})"',
                    "command_root": "python",
                    "started_at": started_at,
                    "status": "completed" if i % 5 != 0 else "failed",
                    "pid": None,
                    "finished_at": finished_at,
                    "exit_code": 0 if i % 5 != 0 else 1,
                    "last_event_type": "completed" if i % 5 != 0 else "failed",
                    "last_event_at": finished_at,
                    "matched_pattern": None,
                    "matched_stream": None,
                },
            )
            records[uid] = {
                "name": f"sleepy-{uid}",
                "record_relpath": str(
                    record_dir.relative_to(self.jobs_root).as_posix()
                ),
                "cmd": f'python -c "print({i})"',
                "created_at": started_at,
            }
            names[f"sleepy-{uid}"] = uid
        self.write_index(records, names)

        # Default list: running only -> none of the fabricated settled jobs.
        default_json = self.cli("list", "--json")
        self.assertEqual(default_json.returncode, 0, default_json.stderr)
        self.assertEqual(json.loads(default_json.stdout), [])

        default_table = self.cli("list")
        self.assertEqual(default_table.returncode, 0, default_table.stderr)
        self.assertIn("No jobs found.", default_table.stdout)
        self.assertNotIn("settle", default_table.stdout)

        # --all page 1: 20 rows + Settled section + footer + hint.
        page1 = self.cli("list", "--all")
        self.assertEqual(page1.returncode, 0, page1.stderr)
        self.assertIn("Settled", page1.stdout)
        self.assertIn("sleepy-settle000", page1.stdout)
        self.assertIn("sleepy-settle019", page1.stdout)
        self.assertNotIn("sleepy-settle020", page1.stdout)
        self.assertIn("Showing 1-20 of 25 (page 1/2)", page1.stdout)
        self.assertIn("use --page 2", page1.stdout)

        # --all page 2: the remaining 5 + footer without hint.
        page2 = self.cli("list", "--all", "--page", "2")
        self.assertEqual(page2.returncode, 0, page2.stderr)
        self.assertIn("sleepy-settle020", page2.stdout)
        self.assertIn("sleepy-settle024", page2.stdout)
        self.assertNotIn("sleepy-settle000", page2.stdout)
        self.assertIn("Showing 21-25 of 25 (page 2/2)", page2.stdout)
        self.assertNotIn("use --page", page2.stdout)

        # Out-of-range page: empty result + hint (-a alias for --all).
        page3 = self.cli("list", "-a", "--page", "3")
        self.assertEqual(page3.returncode, 0, page3.stderr)
        self.assertIn("No jobs on page 3.", page3.stdout)
        self.assertIn("use --page 2", page3.stdout)

        # JSON is never paginated and contains everything with --all.
        all_json = self.cli("list", "--all", "--json")
        self.assertEqual(all_json.returncode, 0, all_json.stderr)
        jobs = json.loads(all_json.stdout)
        self.assertEqual(len(jobs), 25)
        self.assertEqual({job["status"] for job in jobs}, {"completed", "failed"})

    # --- 6. read --tail: incremental, no re-prints -------------------------

    def test_read_tail_is_incremental_and_never_reprints(self) -> None:
        writer_script = self.temp_root / "tail_writer.py"
        writer_script.write_text(
            textwrap.dedent(
                """
                import pathlib
                import sys
                import time

                print("line-one", flush=True)
                go = pathlib.Path(sys.argv[1])
                while not go.exists():
                    time.sleep(0.1)
                print("line-two", flush=True)
                time.sleep(3)
                """
            ).lstrip(),
            encoding="utf-8",
        )
        go_marker = self.temp_root / "go.marker"

        cmd = f'python "{writer_script}" "{go_marker}"'
        run = self.cli("run", cmd)
        self.assertEqual(run.returncode, 0, run.stderr)
        name = run.stdout.strip()
        self.wait_for_status(name)

        def tail_until(substring: str, timeout: float = 10.0) -> str:
            deadline = time.time() + timeout
            last_out = ""
            while time.time() < deadline:
                result = self.cli("read", name, "--tail")
                self.assertEqual(result.returncode, 0, result.stderr)
                last_out = result.stdout
                if substring in last_out:
                    return last_out
                time.sleep(0.1)
            self.fail(f"tail never produced {substring!r}; last output: {last_out!r}")

        first = tail_until("line-one")
        self.assertNotIn("line-two", first)

        go_marker.write_text("go", encoding="utf-8")

        second = tail_until("line-two")
        self.assertNotIn("line-one", second)

        # Plain read still shows everything.
        plain = self.cli("read", name)
        self.assertEqual(plain.returncode, 0, plain.stderr)
        self.assertIn("line-one", plain.stdout)
        self.assertIn("line-two", plain.stdout)

        # Nothing new -> tail prints only the cwd header.
        final = self.cli("read", name, "--tail")
        self.assertEqual(final.returncode, 0, final.stderr)
        self.assertNotIn("line-one", final.stdout)
        self.assertNotIn("line-two", final.stdout)

    # --- 7. restart preserves cwd ------------------------------------------

    def test_restart_preserves_cwd(self) -> None:
        work_dir = self.temp_root / "workdir"
        work_dir.mkdir(parents=True, exist_ok=True)

        run = self.cli(
            "run",
            "--cwd",
            str(work_dir),
            'python -c "import time; time.sleep(30)"',
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        name = run.stdout.strip()

        before = self.wait_for_status(name)
        self.assertEqual(before["cwd"], str(work_dir))
        first_pid = before["pid"]

        restart = self.cli("restart", name)
        self.assertEqual(restart.returncode, 0, restart.stderr)

        after = self.wait_for_status(name)
        self.assertEqual(after["cwd"], str(work_dir))
        self.assertNotEqual(after["pid"], first_pid)

    # --- 8. legacy record: cwd null, Dir '-', no header --------------------

    def test_legacy_record_without_cwd(self) -> None:
        uid = "legacy001"
        now = datetime.now()
        started_at = (now - timedelta(minutes=5)).isoformat()
        finished_at = (now - timedelta(minutes=4)).isoformat()
        record_dir = self.write_meta(
            uid,
            {
                "uid": uid,
                "id": uid,
                "name": "sleepy-legacy",
                "cmd": 'python -c "print(1)"',
                "command_root": "python",
                "started_at": started_at,
                "status": "completed",
                "pid": None,
                "finished_at": finished_at,
                "exit_code": 0,
                "last_event_type": "completed",
                "last_event_at": finished_at,
                "matched_pattern": None,
                "matched_stream": None,
            },
        )
        (record_dir / "stdout.txt").write_text("legacy-output\n", encoding="utf-8")
        self.write_index(
            records={
                uid: {
                    "name": "sleepy-legacy",
                    "record_relpath": str(
                        record_dir.relative_to(self.jobs_root).as_posix()
                    ),
                    "cmd": 'python -c "print(1)"',
                    "created_at": started_at,
                }
            },
            names={"sleepy-legacy": uid},
        )

        status = self.cli("status", "sleepy-legacy")
        self.assertEqual(status.returncode, 0, status.stderr)
        status_json = json.loads(status.stdout)
        self.assertIsNone(status_json["cwd"])

        # List table: legacy row shows no path in the Dir column.
        listed = self.cli("list", "--all")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        row = next(
            line for line in listed.stdout.splitlines() if "sleepy-legacy" in line
        )
        self.assertNotIn(str(self.temp_root), row)
        cells = [cell.strip() for cell in row.split("│")]
        self.assertGreater(len(cells), 10)
        self.assertEqual(cells[10], "-")  # Dir column

        # read / logs print no cwd header for legacy records.
        read = self.cli("read", "sleepy-legacy")
        self.assertEqual(read.returncode, 0, read.stderr)
        self.assertIn("legacy-output", read.stdout)
        self.assertNotIn("cwd:", read.stdout)

        logs = self.cli("logs", "sleepy-legacy")
        self.assertEqual(logs.returncode, 0, logs.stderr)
        self.assertNotIn("cwd:", logs.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
