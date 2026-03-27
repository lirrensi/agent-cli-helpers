# FILE: tests/test_bg_redesign.py
# PURPOSE: Exercise bg redesign through the real CLI paths with a temp storage root.
# OWNS: End-to-end regression coverage for naming, collisions, list/status, and broken records.
# DOCS: agent_chat/plan_bg_name_redesign_2026-03-27.md, agent_chat/plan_bg_wait_notifications_2026-03-28.md, docs/product.md, docs/arch.md, skills/bg-jobs/SKILL.md

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BG_SRC = ROOT / "src"


class TestBgRedesign(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp(prefix="bg_redesign_cli_"))
        self.jobs_root = self.temp_root / "agentcli_bgjobs"
        self.jobs_root.mkdir(parents=True, exist_ok=True)

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
            from agentcli_helpers import bg
            bg.FRIENDLY_WORDS = ['sleepy']
            sys.argv = ['bg', {", ".join(repr(a) for a in args)}]
            bg.main()
            """
        )

        return subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=env,
        )

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

    def test_collision_suffix_run_and_read_rm(self) -> None:
        first = self.cli("run", 'python -c "print(1)"')
        self.assertEqual(first.returncode, 0, first.stderr)
        name1 = first.stdout.strip()
        self.assertEqual(name1, "sleepy-python")

        second = self.cli("run", 'python -c "print(2)"')
        self.assertEqual(second.returncode, 0, second.stderr)
        name2 = second.stdout.strip()
        self.assertRegex(name2, r"^sleepy-python-[a-z0-9]{2}$")
        self.assertNotEqual(name1, name2)

        read = self.cli("read", name1)
        self.assertEqual(read.returncode, 0, read.stderr)
        self.assertIn("1", read.stdout)

        rm = self.cli("rm", name1)
        self.assertEqual(rm.returncode, 0, rm.stderr)
        self.assertIn("Removed job", rm.stdout)

        missing = self.cli("status", name1)
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("Job not found", missing.stderr)

    def test_list_and_status_surface_live_and_dead_process_states(self) -> None:
        live_uid = "live123"
        dead_uid = "dead123"

        live_dir = self.write_meta(
            live_uid,
            {
                "uid": live_uid,
                "id": live_uid,
                "name": "sleepy-live",
                "cmd": 'python -c "print(1)"',
                "command_root": "python",
                "started_at": "2026-03-27T00:00:00",
                "status": "running",
                "pid": os.getpid(),
                "finished_at": None,
                "exit_code": None,
            },
        )
        dead_dir = self.write_meta(
            dead_uid,
            {
                "uid": dead_uid,
                "id": dead_uid,
                "name": "sleepy-dead",
                "cmd": 'python -c "print(2)"',
                "command_root": "python",
                "started_at": "2026-03-27T00:00:00",
                "status": "running",
                "pid": 99999999,
                "finished_at": None,
                "exit_code": None,
            },
        )
        self.write_index(
            records={
                live_uid: {
                    "name": "sleepy-live",
                    "record_relpath": str(
                        live_dir.relative_to(self.jobs_root).as_posix()
                    ),
                    "cmd": 'python -c "print(1)"',
                    "created_at": "2026-03-27T00:00:00",
                },
                dead_uid: {
                    "name": "sleepy-dead",
                    "record_relpath": str(
                        dead_dir.relative_to(self.jobs_root).as_posix()
                    ),
                    "cmd": 'python -c "print(2)"',
                    "created_at": "2026-03-27T00:00:00",
                },
            },
            names={"sleepy-live": live_uid, "sleepy-dead": dead_uid},
        )

        running = self.cli("status", "sleepy-live")
        self.assertEqual(running.returncode, 0, running.stderr)
        running_json = json.loads(running.stdout)
        self.assertEqual(running_json["record_state"], "ok")
        self.assertEqual(running_json["process_state"], "alive")
        self.assertEqual(running_json["status"], "running")

        dead = self.cli("status", "sleepy-dead")
        self.assertEqual(dead.returncode, 0, dead.stderr)
        dead_json = json.loads(dead.stdout)
        self.assertEqual(dead_json["record_state"], "ok")
        self.assertEqual(dead_json["process_state"], "dead")
        self.assertEqual(dead_json["status"], "stale")

        listed = self.cli("list", "--json")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        jobs = json.loads(listed.stdout)
        self.assertTrue(
            any(
                job["name"] == "sleepy-live" and job["process_state"] == "alive"
                for job in jobs
            )
        )
        self.assertTrue(
            any(
                job["name"] == "sleepy-dead" and job["process_state"] == "dead"
                for job in jobs
            )
        )

    def test_orphan_missing_and_corrupt_are_visible_in_cli_list_and_status(
        self,
    ) -> None:
        orphan_dir = self.jobs_root / "records" / "orphan123"
        orphan_dir.mkdir(parents=True, exist_ok=True)

        missing_uid = "missing123"
        corrupt_uid = "corrupt123"
        healthy_uid = "healthy123"

        self.write_index(
            records={
                missing_uid: {
                    "name": "sleepy-missing",
                    "record_relpath": f"records/{missing_uid}",
                    "cmd": "python -m pytest",
                    "created_at": "2026-03-27T00:00:00",
                },
                healthy_uid: {
                    "name": "sleepy-healthy",
                    "record_relpath": f"records/{healthy_uid}",
                    "cmd": "python -m pytest",
                    "created_at": "2026-03-27T00:00:00",
                },
            },
            names={"sleepy-missing": missing_uid, "sleepy-healthy": healthy_uid},
        )

        self.write_meta(
            healthy_uid,
            {
                "uid": healthy_uid,
                "id": healthy_uid,
                "name": "sleepy-healthy",
                "cmd": "python -c \"print('ok')\"",
                "command_root": "python",
                "started_at": "2026-03-27T00:00:00",
                "status": "running",
                "pid": os.getpid(),
                "finished_at": None,
                "exit_code": None,
            },
        )

        corrupt_dir = self.jobs_root / "records" / corrupt_uid
        corrupt_dir.mkdir(parents=True, exist_ok=True)
        (corrupt_dir / "meta.json").write_text("{broken", encoding="utf-8")

        list_result = self.cli("list", "--json")
        self.assertEqual(list_result.returncode, 0, list_result.stderr)
        listed = json.loads(list_result.stdout)
        states = {job["record_state"] for job in listed}
        self.assertTrue({"orphaned", "missing", "corrupt"}.issubset(states))

        orphan = self.cli("status", "orphan123")
        self.assertNotEqual(orphan.returncode, 0)
        orphan_json = json.loads(orphan.stdout)
        self.assertEqual(orphan_json["record_state"], "orphaned")

        missing = self.cli("status", "sleepy-missing")
        self.assertNotEqual(missing.returncode, 0)
        missing_json = json.loads(missing.stdout)
        self.assertEqual(missing_json["record_state"], "missing")

        corrupt = self.cli("status", "corrupt123")
        self.assertNotEqual(corrupt.returncode, 0)
        corrupt_json = json.loads(corrupt.stdout)
        self.assertEqual(corrupt_json["record_state"], "corrupt")

    def test_wait_completion_blocks_until_done_and_marks_event(self) -> None:
        run = self.cli("run", 'python -c "import time; time.sleep(0.4)"')
        self.assertEqual(run.returncode, 0, run.stderr)
        job_name = run.stdout.strip()

        start = time.perf_counter()
        wait = self.cli("wait", job_name)
        elapsed = time.perf_counter() - start

        self.assertEqual(wait.returncode, 0, wait.stderr)
        self.assertGreaterEqual(elapsed, 0.2)

        status = self.cli("status", job_name)
        self.assertEqual(status.returncode, 0, status.stderr)
        status_json = json.loads(status.stdout)
        self.assertEqual(status_json["status"], "completed")
        self.assertEqual(status_json["last_event_type"], "completed")
        self.assertEqual(status_json["update_marker"], "completed")

    def test_wait_match_tracks_stderr_and_surfaces_update_marker(self) -> None:
        run = self.cli(
            "run",
            "python -c \"import sys,time; sys.stderr.write('needle\\n'); sys.stderr.flush(); time.sleep(1.5)\"",
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        job_name = run.stdout.strip()

        start = time.perf_counter()
        wait = self.cli("wait", job_name, "--match", "needle")
        elapsed = time.perf_counter() - start

        self.assertEqual(wait.returncode, 0, wait.stderr)
        self.assertGreaterEqual(elapsed, 0.15)

        listed = self.cli("list", "--json")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        jobs = json.loads(listed.stdout)
        match = next(job for job in jobs if job["name"] == job_name)
        self.assertIn(match["status"], {"running", "completed"})
        self.assertEqual(match["matched_pattern"], "needle")
        self.assertEqual(match["matched_stream"], "stderr")
        self.assertIn("matched: needle", match["update_marker"])

        status = self.cli("status", job_name)
        self.assertEqual(status.returncode, 0, status.stderr)
        status_json = json.loads(status.stdout)
        self.assertEqual(status_json["matched_stream"], "stderr")
        self.assertIn("matched: needle", status_json["update_marker"])

    def test_wait_all_waits_for_multiple_jobs(self) -> None:
        first = self.cli("run", 'python -c "import time; time.sleep(0.35)"')
        self.assertEqual(first.returncode, 0, first.stderr)
        first_name = first.stdout.strip()

        second = self.cli("run", 'python -c "import time; time.sleep(0.55)"')
        self.assertEqual(second.returncode, 0, second.stderr)
        second_name = second.stdout.strip()

        start = time.perf_counter()
        wait_all = self.cli("wait-all")
        elapsed = time.perf_counter() - start

        self.assertEqual(wait_all.returncode, 0, wait_all.stderr)
        self.assertGreaterEqual(elapsed, 0.3)

        for name in (first_name, second_name):
            status = self.cli("status", name)
            self.assertEqual(status.returncode, 0, status.stderr)
            status_json = json.loads(status.stdout)
            self.assertEqual(status_json["status"], "completed")
            self.assertEqual(status_json["last_event_type"], "completed")
            self.assertEqual(status_json["update_marker"], "completed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
