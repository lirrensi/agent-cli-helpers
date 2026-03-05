#!/usr/bin/env bash
# tmx - tmux helper for agents
# Simple named-session workflow, no socket nonsense.

set -euo pipefail

# === FUNCTIONS (must be defined before use) ===

usage() {
  cat <<'USAGE'
tmx - tmux helper for agents

Usage:
  tmx new <name>                    Create new detached session
  tmx new <name> "<cmd>"            Create session and run command
  
  tmx send <session> "<cmd>"        Send keys to session
  tmx capture <session> [lines]     Capture pane output (default: 500 lines)
  
  tmx sync <session> "<cmd>"        Sync: send, wait for prompt, capture
    --prompt <pattern>              Wait for pattern (default: common prompts)
    --timeout <sec>                 Fixed wait mode: wait N seconds, return
  
  tmx list                          List all sessions
  tmx kill <session>                Kill session
  tmx attach <session>              Attach to session (interactive)

Examples:
  tmx new agent1
  tmx new python-repl "python3 -q"
  
  tmx send agent1 "ls -la"
  
  tmx capture agent1
  tmx capture agent1 1000
  
  tmx sync agent1 "pip install numpy"              # waits for prompt
  tmx sync agent1 "make build" --timeout 30        # wait 30s, return
  tmx sync agent1 "python script.py" --prompt ">>" # wait for custom prompt
  
  tmx list
  tmx kill agent1
USAGE
}

# Wait for prompt pattern with timeout
# Uses deciseconds internally to avoid floating point
wait_for_prompt() {
  local session="$1"
  local pattern="$2"
  local max_wait_ds=600  # 60 seconds in deciseconds
  local interval_ds=5    # 0.5 seconds
  local waited_ds=0
  
  while (( waited_ds < max_wait_ds )); do
    local output
    output=$(tmux capture-pane -p -J -t "$session" -S -100 2>/dev/null || true)
    
    # Check last few lines for prompt
    if echo "$output" | tail -5 | grep -qE "$pattern"; then
      return 0
    fi
    
    sleep 0.5
    ((waited_ds += interval_ds))
  done
  
  echo "Timeout waiting for prompt after 60s" >&2
  return 1
}

# === CONSTANTS ===

DEFAULT_PROMPTS='(\$|❯|#|>|>>>|\.\.\.)\s*$'

# === MAIN ===

cmd="${1:-}"
shift || true

case "$cmd" in
  new)
    name="${1:-}"
    [[ -z "$name" ]] && { echo "Usage: tmx new <name> [cmd]" >&2; exit 1; }
    shift || true
    
    # Create session
    if tmux has-session -t "$name" 2>/dev/null; then
      echo "Session '$name' already exists" >&2
      exit 1
    fi
    
    tmux new-session -d -s "$name"
    
    # Run initial command if provided
    if [[ $# -gt 0 ]]; then
      init_cmd="$1"
      tmux send-keys -t "$name" -l -- "$init_cmd"
      tmux send-keys -t "$name" Enter
    fi
    
    echo "Created session: $name"
    ;;
    
  send)
    session="${1:-}"
    cmd_str="${2:-}"
    [[ -z "$session" || -z "$cmd_str" ]] && { echo "Usage: tmx send <session> \"<cmd>\"" >&2; exit 1; }
    
    if ! tmux has-session -t "$session" 2>/dev/null; then
      echo "Session '$session' not found" >&2
      exit 1
    fi
    
    tmux send-keys -t "$session" -l -- "$cmd_str"
    tmux send-keys -t "$session" Enter
    ;;
    
  capture)
    session="${1:-}"
    lines="${2:-500}"
    [[ -z "$session" ]] && { echo "Usage: tmx capture <session> [lines]" >&2; exit 1; }
    
    if ! tmux has-session -t "$session" 2>/dev/null; then
      echo "Session '$session' not found" >&2
      exit 1
    fi
    
    tmux capture-pane -p -J -t "$session" -S "-${lines}"
    ;;
    
  sync)
    session="${1:-}"
    cmd_str="${2:-}"
    [[ -z "$session" || -z "$cmd_str" ]] && { echo "Usage: tmx sync <session> \"<cmd>\" [--prompt <pattern>|--timeout <sec>]" >&2; exit 1; }
    shift 2 || true
    
    if ! tmux has-session -t "$session" 2>/dev/null; then
      echo "Session '$session' not found" >&2
      exit 1
    fi
    
    # Parse options
    mode="prompt"
    pattern="$DEFAULT_PROMPTS"
    timeout_sec=5
    
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --prompt)  mode="prompt"; pattern="${2:-}"; shift 2 ;;
        --timeout) mode="timeout"; timeout_sec="${2:-5}"; shift 2 ;;
        *) shift ;;
      esac
    done
    
    # Send command
    tmux send-keys -t "$session" -l -- "$cmd_str"
    tmux send-keys -t "$session" Enter
    
    if [[ "$mode" == "timeout" ]]; then
      # Fixed timeout mode
      sleep "$timeout_sec"
    else
      # Prompt detection mode
      wait_for_prompt "$session" "$pattern"
    fi
    
    # Capture output
    tmux capture-pane -p -J -t "$session" -S -500
    ;;
    
  list)
    tmux list-sessions -F '#{session_name} #{session_windows}w #{?session_attached,attached,detached}' 2>/dev/null || echo "No sessions"
    ;;
    
  kill)
    session="${1:-}"
    [[ -z "$session" ]] && { echo "Usage: tmx kill <session>" >&2; exit 1; }
    
    if ! tmux has-session -t "$session" 2>/dev/null; then
      echo "Session '$session' not found" >&2
      exit 1
    fi
    
    tmux kill-session -t "$session"
    echo "Killed session: $session"
    ;;
    
  attach)
    session="${1:-}"
    [[ -z "$session" ]] && { echo "Usage: tmx attach <session>" >&2; exit 1; }
    
    if ! tmux has-session -t "$session" 2>/dev/null; then
      echo "Session '$session' not found" >&2
      exit 1
    fi
    
    tmux attach -t "$session"
    ;;
    
  -h|--help|help)
    usage
    ;;
    
  *)
    echo "Unknown command: $cmd" >&2
    usage
    exit 1
    ;;
esac
