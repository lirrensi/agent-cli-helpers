#!/usr/bin/env bash
# reinstall.sh — Force reinstall agent-sommelier CLI tool (bash / git-bash).
# Bash counterpart of reinstall.ps1 (PowerShell). Same behavior:
# kills processes locking the uv tool install dir, then reinstalls.
#
# Usage:
#   ./reinstall.sh          # kill lockers, then reinstall
#   ./reinstall.sh --no-kill  # skip the process-kill step (like -NoKill)

set -euo pipefail

NO_KILL=0
for arg in "$@"; do
  case "$arg" in
    --no-kill) NO_KILL=1 ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

if [ "$NO_KILL" -eq 0 ]; then
  echo "Killing processes locking the tool install dir ..."
  # Same logic as reinstall.ps1 — delegate to PowerShell (works on Windows git-bash).
  if powershell -NoProfile -Command '
    $procs = Get-Process | Where-Object { $_.Path -like "*agent-sommelier*" }
    if ($procs) {
      $procs | ForEach-Object {
        Write-Host ("  Killing PID {0} ({1})" -f $_.Id, $_.ProcessName)
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
      }
    } else {
      Write-Host "  No locking processes found."
    }'; then
    :
  else
    echo "  (PowerShell unavailable — skipping kill. If install fails, close running tools first.)"
  fi
fi

echo "Installing..."
uv tool install ".[all]" --force --reinstall
echo "Done."
