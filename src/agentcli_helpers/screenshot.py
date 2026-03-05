"""Cross-platform screenshot CLI.

Usage:
    screenshot              # Auto-names, outputs path
    screenshot output.png   # Save to specific file
"""

import sys
import platform
import subprocess
from pathlib import Path
from datetime import datetime
import tempfile
import click


def screenshot_native(output_path: str) -> bool:
    """Take screenshot using native OS tools."""
    system = platform.system()

    try:
        if system == "Linux":
            # Try various screenshot tools
            for tool in ["gnome-screenshot", "scrot", "import", "flameshot"]:
                try:
                    if tool == "gnome-screenshot":
                        subprocess.run(
                            [tool, "-f", output_path], check=True, capture_output=True
                        )
                    elif tool == "scrot":
                        subprocess.run(
                            [tool, output_path], check=True, capture_output=True
                        )
                    elif tool == "import":
                        subprocess.run(
                            [tool, "-window", "root", output_path],
                            check=True,
                            capture_output=True,
                        )
                    elif tool == "flameshot":
                        subprocess.run(
                            [tool, "full", "-p", output_path],
                            check=True,
                            capture_output=True,
                        )
                    return True
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            return False

        elif system == "Darwin":  # macOS
            subprocess.run(["screencapture", "-x", output_path], check=True)
            return True

        elif system == "Windows":
            # Use PowerShell with .NET
            ps_script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            [System.Windows.Forms.Screen]::PrimaryScreen
            $bitmap = New-Object System.Drawing.Bitmap([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width, [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height)
            $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
            $graphics.CopyFromScreen([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Location, [System.Drawing.Point]::Empty, [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Size)
            $bitmap.Save("{output_path}")
            $graphics.Dispose()
            $bitmap.Dispose()
            '''
            subprocess.run(
                ["powershell", "-Command", ps_script], check=True, capture_output=True
            )
            return True

        else:
            return False

    except Exception as e:
        click.echo(f"Screenshot failed: {e}", err=True)
        return False


def auto_name_screenshot() -> Path:
    """Generate auto-named screenshot path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"

    # Use standard temp directory
    temp_dir = Path(tempfile.gettempdir()) / "agentcli_screenshots"
    temp_dir.mkdir(parents=True, exist_ok=True)

    return temp_dir / filename


@click.command()
@click.argument("output", required=False, default=None, type=click.Path())
@click.option(
    "--all-monitors", is_flag=True, help="Capture all monitors (default behavior)"
)
def main(output: str | None, all_monitors: bool):
    """Take a screenshot.

    OUTPUT: Optional output file path. If not provided, auto-generates name.

    Examples:
        screenshot              # Auto-names, outputs path
        screenshot shot.png     # Save to shot.png
    """
    if output:
        output_path = Path(output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        output_path = auto_name_screenshot()

    # Use native method - mss has issues on some Windows systems
    success = screenshot_native(str(output_path))

    if success:
        click.echo(str(output_path))
    else:
        click.echo("Failed to take screenshot.", err=True)
        click.echo(
            "Install with: uv tool install agentcli-helpers[screenshot]", err=True
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
