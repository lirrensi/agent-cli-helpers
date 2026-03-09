"""Background job manager CLI.

Usage:
    bg run "command"      # Run command in background, returns job ID
    bg list               # List all jobs
    bg status <id>        # Check job status
    bg read <id>          # Read stdout
    bg logs <id>          # Read stdout + stderr
    bg rm <id>            # Remove job record
"""

import os
import sys
import json
import subprocess
import signal
import tempfile
from pathlib import Path
from datetime import datetime
import click
import psutil

# Job storage directory - use temp for automatic OS cleanup
JOBS_DIR = Path(tempfile.gettempdir()) / "agentcli_bgjobs"


def ensure_jobs_dir():
    """Ensure jobs directory exists."""
    JOBS_DIR.mkdir(parents=True, exist_ok=True)


def job_dir_for(job_id: str) -> Path:
    """Return the directory for a job."""
    return JOBS_DIR / job_id


def meta_file_for(job_id: str) -> Path:
    """Return the metadata file for a job."""
    return job_dir_for(job_id) / "meta.json"


def exit_code_file_for(job_id: str) -> Path:
    """Return the exit code file for a job."""
    return job_dir_for(job_id) / "exit_code.txt"


def parse_iso_timestamp(value: str | None) -> datetime | None:
    """Parse an ISO timestamp safely."""
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def calculate_elapsed_seconds(started_at: str | None) -> float | None:
    """Calculate elapsed seconds from a start timestamp."""
    started = parse_iso_timestamp(started_at)
    if not started:
        return None

    elapsed = (datetime.now(started.tzinfo) - started).total_seconds()
    return max(0.0, elapsed)


def read_exit_code(job_id: str) -> int | None:
    """Read a persisted process exit code."""
    exit_file = exit_code_file_for(job_id)
    if not exit_file.exists():
        return None

    content = exit_file.read_text().strip()
    if not content:
        return None

    try:
        return int(content)
    except ValueError:
        return None


def inspect_process(pid: int | None) -> dict:
    """Inspect a live process with psutil."""
    if not pid:
        return {"is_running": False}

    try:
        proc = psutil.Process(pid)
        with proc.oneshot():
            status = proc.status()
            if not proc.is_running() or status == getattr(
                psutil, "STATUS_ZOMBIE", None
            ):
                return {"is_running": False}

            details: dict[str, object] = {"is_running": True}

            try:
                details["memory_bytes"] = proc.memory_info().rss
            except (psutil.Error, OSError):
                pass

            try:
                details["cpu_percent"] = proc.cpu_percent(interval=None)
            except (psutil.Error, OSError):
                pass

            return details
    except (psutil.Error, OSError):
        return {"is_running": False}


def update_job_metadata(job_id: str, job: dict) -> dict:
    """Persist job metadata to disk."""
    meta_file_for(job_id).write_text(json.dumps(job, indent=2))
    return job


def mark_finished_job(job: dict, exit_code: int | None) -> dict:
    """Mark a job as finished with terminal metadata."""
    finished_job = dict(job)

    if exit_code is None:
        return finished_job

    finished_job["exit_code"] = exit_code
    finished_job["status"] = "completed" if exit_code == 0 else "failed"

    if not finished_job.get("finished_at"):
        exit_file = exit_code_file_for(finished_job["id"])
        finished_at = datetime.now().isoformat()
        if exit_file.exists():
            finished_at = datetime.fromtimestamp(exit_file.stat().st_mtime).isoformat()
        finished_job["finished_at"] = finished_at

    return finished_job


def refresh_job(job: dict) -> dict:
    """Refresh best-effort runtime fields for a job."""
    refreshed = dict(job)

    elapsed_seconds = calculate_elapsed_seconds(refreshed.get("started_at"))
    if elapsed_seconds is not None:
        refreshed["elapsed_seconds"] = elapsed_seconds

    process_info = inspect_process(refreshed.get("pid"))
    if process_info.get("is_running"):
        refreshed["status"] = "running"
        if process_info.get("memory_bytes") is not None:
            refreshed["memory_bytes"] = process_info["memory_bytes"]
        if process_info.get("cpu_percent") is not None:
            refreshed["cpu_percent"] = process_info["cpu_percent"]
    else:
        exit_code = read_exit_code(refreshed["id"])
        if exit_code is not None or refreshed.get("status") != "running":
            refreshed = mark_finished_job(refreshed, exit_code)

    return update_job_metadata(refreshed["id"], refreshed)


def format_elapsed(seconds: float | None) -> str:
    """Format elapsed seconds for display."""
    if seconds is None:
        return "-"

    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def format_memory(memory_bytes: int | None) -> str:
    """Format memory usage for display."""
    if memory_bytes is None:
        return "-"

    if memory_bytes >= 1024**3:
        return f"{memory_bytes / (1024**3):.1f} GB"
    if memory_bytes >= 1024**2:
        return f"{memory_bytes / (1024**2):.0f} MB"
    if memory_bytes >= 1024:
        return f"{memory_bytes / 1024:.0f} KB"
    return f"{memory_bytes} B"


def build_wrapped_command(job_id: str, cmd: str) -> tuple[str | list[str], bool]:
    """Wrap a command so its exit code is persisted."""
    exit_code_file = exit_code_file_for(job_id)

    if sys.platform == "win32":
        runner_file = job_dir_for(job_id) / "runner.cmd"
        runner_file.write_text(
            "\n".join(
                [
                    "@echo off",
                    cmd,
                    "set bg_exit=%errorlevel%",
                    f'> "{exit_code_file}" echo %bg_exit%',
                    "exit /b %bg_exit%",
                ]
            )
        )
        return ["cmd.exe", "/d", "/c", str(runner_file)], False

    wrapped = f'({cmd}); printf "%s" "$?" > {json.dumps(str(exit_code_file))}'
    return wrapped, True


def generate_id() -> str:
    """Generate a short job ID."""
    import random
    import string

    return "".join(random.choices(string.ascii_lowercase + string.digits, k=6))


def create_job(cmd: str) -> str:
    """Create a new background job."""
    ensure_jobs_dir()

    job_id = generate_id()
    job_dir = job_dir_for(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)

    # Write job metadata
    metadata = {
        "id": job_id,
        "cmd": cmd,
        "started_at": datetime.now().isoformat(),
        "status": "running",
        "pid": None,
    }

    update_job_metadata(job_id, metadata)

    # Start the process
    stdout_file = open(job_dir / "stdout.txt", "w")
    stderr_file = open(job_dir / "stderr.txt", "w")

    wrapped_cmd, use_shell = build_wrapped_command(job_id, cmd)

    # Platform-specific process start
    if sys.platform == "win32":
        proc = subprocess.Popen(
            wrapped_cmd,
            shell=use_shell,
            stdout=stdout_file,
            stderr=stderr_file,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS,
        )
    else:
        proc = subprocess.Popen(
            wrapped_cmd,
            shell=use_shell,
            stdout=stdout_file,
            stderr=stderr_file,
            start_new_session=True,
        )

    # Update metadata with PID
    metadata["pid"] = proc.pid
    update_job_metadata(job_id, metadata)

    return job_id


def get_job(job_id: str) -> dict | None:
    """Get job metadata."""
    job_dir = JOBS_DIR / job_id
    meta_file = meta_file_for(job_id)

    if not meta_file.exists():
        return None

    return json.loads(meta_file.read_text())


def update_job_status(job_id: str, status: str):
    """Update job status."""
    job = get_job(job_id)
    if job:
        job["status"] = status
        job["finished_at"] = datetime.now().isoformat()
        update_job_metadata(job_id, job)


def check_job_alive(job_id: str) -> bool:
    """Check if job process is still running."""
    job = get_job(job_id)
    if not job or not job.get("pid"):
        return False

    return inspect_process(job["pid"]).get("is_running", False)


def list_jobs() -> list[dict]:
    """List all jobs."""
    ensure_jobs_dir()
    jobs = []

    for job_dir in JOBS_DIR.iterdir():
        if job_dir.is_dir():
            meta_file = job_dir / "meta.json"
            if meta_file.exists():
                job = json.loads(meta_file.read_text())

                jobs.append(refresh_job(job))

    # Sort by started_at descending
    jobs.sort(key=lambda j: j.get("started_at", ""), reverse=True)
    return jobs


def remove_job(job_id: str) -> bool:
    """Remove a job record."""
    job_dir = JOBS_DIR / job_id

    if not job_dir.exists():
        return False

    # Kill if still running
    job = get_job(job_id)
    if job and job.get("pid") and job["status"] == "running":
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(job["pid"])], capture_output=True
                )
            else:
                os.killpg(os.getpgid(job["pid"]), signal.SIGTERM)
        except (OSError, ProcessLookupError):
            pass

    # Remove directory
    import shutil

    shutil.rmtree(job_dir)
    return True


@click.group()
def main():
    """Background job manager."""
    pass


@main.command()
@click.argument("cmd")
def run(cmd: str):
    """Run a command in the background.

    CMD: Command to run

    Example:
        bg run "python long_script.py"
    """
    job_id = create_job(cmd)
    click.echo(job_id)


@main.command("list")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def list_cmd(json_output: bool):
    """List all background jobs."""
    jobs = list_jobs()

    if json_output:
        click.echo(json.dumps(jobs, indent=2))
    else:
        if not jobs:
            click.echo("No jobs found.")
            return

        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="Background Jobs")
        table.add_column("ID", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("PID", style="magenta")
        table.add_column("Started", style="dim")
        table.add_column("Elapsed", style="blue")
        table.add_column("Memory", style="blue")
        table.add_column("Command", style="white", max_width=40)

        for job in jobs:
            status = job["status"]
            status_style = {
                "running": "yellow",
                "completed": "green",
                "failed": "red",
            }.get(status, "white")
            table.add_row(
                job["id"],
                f"[{status_style}]{status}[/{status_style}]",
                str(job.get("pid") or "-"),
                job.get("started_at", "?")[:19],
                format_elapsed(job.get("elapsed_seconds")),
                format_memory(job.get("memory_bytes")),
                job.get("cmd", "?")[:40],
            )

        console.print(table)


@main.command()
@click.argument("job_id")
def status(job_id: str):
    """Check job status."""
    job = get_job(job_id)

    if not job:
        click.echo(f"Job not found: {job_id}", err=True)
        sys.exit(1)

    job = refresh_job(job)

    click.echo(json.dumps(job, indent=2))


@main.command()
@click.argument("job_id")
def read(job_id: str):
    """Read job stdout."""
    stdout_file = JOBS_DIR / job_id / "stdout.txt"

    if not stdout_file.exists():
        click.echo(f"Job not found: {job_id}", err=True)
        sys.exit(1)

    click.echo(stdout_file.read_text())


@main.command()
@click.argument("job_id")
def logs(job_id: str):
    """Read job stdout and stderr."""
    job_dir = JOBS_DIR / job_id

    if not job_dir.exists():
        click.echo(f"Job not found: {job_id}", err=True)
        sys.exit(1)

    stdout_file = job_dir / "stdout.txt"
    stderr_file = job_dir / "stderr.txt"

    if stdout_file.exists():
        click.echo("=== STDOUT ===")
        click.echo(stdout_file.read_text())

    if stderr_file.exists() and stderr_file.read_text().strip():
        click.echo("\n=== STDERR ===")
        click.echo(stderr_file.read_text())


@main.command()
@click.argument("job_id")
def rm(job_id: str):
    """Remove a job record."""
    if remove_job(job_id):
        click.echo(f"Removed job: {job_id}")
    else:
        click.echo(f"Job not found: {job_id}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
