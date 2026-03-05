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

# Job storage directory - use temp for automatic OS cleanup
JOBS_DIR = Path(tempfile.gettempdir()) / "agentcli_bgjobs"


def ensure_jobs_dir():
    """Ensure jobs directory exists."""
    JOBS_DIR.mkdir(parents=True, exist_ok=True)


def generate_id() -> str:
    """Generate a short job ID."""
    import random
    import string

    return "".join(random.choices(string.ascii_lowercase + string.digits, k=6))


def create_job(cmd: str) -> str:
    """Create a new background job."""
    ensure_jobs_dir()

    job_id = generate_id()
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Write job metadata
    metadata = {
        "id": job_id,
        "cmd": cmd,
        "started_at": datetime.now().isoformat(),
        "status": "running",
        "pid": None,
    }

    (job_dir / "meta.json").write_text(json.dumps(metadata, indent=2))

    # Start the process
    stdout_file = open(job_dir / "stdout.txt", "w")
    stderr_file = open(job_dir / "stderr.txt", "w")

    # Platform-specific process start
    if sys.platform == "win32":
        # Use CREATE_NEW_PROCESS_GROUP on Windows
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=stdout_file,
            stderr=stderr_file,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS,
        )
    else:
        # Unix: use start_new_session
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=stdout_file,
            stderr=stderr_file,
            start_new_session=True,
        )

    # Update metadata with PID
    metadata["pid"] = proc.pid
    (job_dir / "meta.json").write_text(json.dumps(metadata, indent=2))

    return job_id


def get_job(job_id: str) -> dict | None:
    """Get job metadata."""
    job_dir = JOBS_DIR / job_id
    meta_file = job_dir / "meta.json"

    if not meta_file.exists():
        return None

    return json.loads(meta_file.read_text())


def update_job_status(job_id: str, status: str):
    """Update job status."""
    job = get_job(job_id)
    if job:
        job["status"] = status
        job["finished_at"] = datetime.now().isoformat()
        (JOBS_DIR / job_id / "meta.json").write_text(json.dumps(job, indent=2))


def check_job_alive(job_id: str) -> bool:
    """Check if job process is still running."""
    job = get_job(job_id)
    if not job or not job.get("pid"):
        return False

    try:
        pid = job["pid"]
        if sys.platform == "win32":
            # Windows: use tasklist
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True
            )
            return str(pid) in result.stdout
        else:
            # Unix: send signal 0
            os.kill(pid, 0)
            return True
    except (OSError, ProcessLookupError):
        return False


def list_jobs() -> list[dict]:
    """List all jobs."""
    ensure_jobs_dir()
    jobs = []

    for job_dir in JOBS_DIR.iterdir():
        if job_dir.is_dir():
            meta_file = job_dir / "meta.json"
            if meta_file.exists():
                job = json.loads(meta_file.read_text())

                # Check if still running
                if job["status"] == "running":
                    if not check_job_alive(job["id"]):
                        update_job_status(job["id"], "completed")
                        job["status"] = "completed"

                jobs.append(job)

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
        table.add_column("Started", style="dim")
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
                job.get("started_at", "?")[:19],
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

    # Update status if needed
    if job["status"] == "running" and not check_job_alive(job_id):
        update_job_status(job_id, "completed")
        job = get_job(job_id)

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
