#!/usr/bin/env pwsh
# tmx - tmux/psmux helper for agents
# Works on Windows (psmux) and Unix (tmux)

<#
.SYNOPSIS
    tmux/psmux helper for agents - simple named session workflow

.DESCRIPTION
    Control tmux sessions programmatically. Works with native tmux on Unix
    and psmux on Windows. Provides sync commands that send keys and
    automatically capture output.

.EXAMPLE
    tmx new mysession
    tmx sync mysession "ls -la"
    tmx capture mysession
    tmx kill mysession
#>

param(
    [Parameter(Position=0)]
    [string]$Command,

    [Parameter(Position=1)]
    [string]$Session,

    [Parameter(Position=2)]
    [string]$CmdStr,

    [string]$Prompt,
    [int]$Timeout,
    [int]$Lines = 500
)

# Detect if we're using psmux (Windows) or tmux (Unix)
$TmuxCmd = if ($IsWindows -or $env:OS -eq "Windows_NT") {
    # Check for psmux/tmux on Windows
    if (Get-Command psmux -ErrorAction SilentlyContinue) { "psmux" }
    elseif (Get-Command tmux -ErrorAction SilentlyContinue) { "tmux" }
    else {
        Write-Error "Neither psmux nor tmux found. Install psmux: winget install psmux"
        exit 1
    }
} else {
    "tmux"
}

# Default prompt patterns
$DefaultPrompts = '(\$|❯|#|>|>>>|\.\.\.)\s*$'

function Show-Help {
    @'
tmx - tmux/psmux helper for agents

Usage:
  tmx new <name>                    Create new detached session
  tmx new <name> "<cmd>"            Create session and run command
  
  tmx send <session> "<cmd>"        Send keys to session
  tmx capture <session> [lines]     Capture pane output (default: 500 lines)
  
  tmx sync <session> "<cmd>"        Sync: send, wait for prompt, capture
    -Prompt <pattern>               Wait for pattern (default: common prompts)
    -Timeout <sec>                  Fixed wait mode: wait N seconds, return
  
  tmx list                          List all sessions
  tmx kill <session>                Kill session
  tmx attach <session>              Attach to session (interactive)

Examples:
  tmx new agent1
  tmx new python-repl "python -q"
  
  tmx send agent1 "ls -la"
  
  tmx capture agent1
  tmx capture agent1 1000
  
  tmx sync agent1 "pip install numpy"              # waits for prompt
  tmx sync agent1 "make build" -Timeout 30         # wait 30s, return
  tmx sync agent1 "python script.py" -Prompt ">>>" # wait for custom prompt
  
  tmx list
  tmx kill agent1

Windows users: Install psmux first
  winget install psmux
  # or: scoop install psmux
  # or: choco install psmux
'@
}

function Invoke-Tmux {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )
    & $TmuxCmd @Arguments
}

function Test-SessionExists {
    param([string]$Name)
    $output = Invoke-Tmux "list-sessions" 2>$null
    if (-not $output) { return $false }
    # Parse "session-name: ..." format
    foreach ($line in $output) {
        if ($line -match "^$Name\s*:") {
            return $true
        }
    }
    return $false
}

function Wait-ForPrompt {
    param(
        [string]$Session,
        [string]$Pattern,
        [int]$MaxWait = 60
    )
    
    $waited = 0
    $interval = 0.5
    
    while ($waited -lt $MaxWait) {
        $output = Invoke-Tmux "capture-pane" "-p" "-J" "-t" $Session "-S" "-100" 2>$null
        # Filter out empty lines and check for prompt
        $nonEmptyLines = $output | Where-Object { $_.Trim() -ne "" }
        $lastLines = $nonEmptyLines | Select-Object -Last 5
        
        if ($lastLines -match $Pattern) {
            return $true
        }
        
        Start-Sleep -Seconds $interval
        $waited += $interval
    }
    
    Write-Warning "Timeout waiting for prompt after ${MaxWait}s"
    return $false
}

switch ($Command) {
    { $_ -in "new", "n" } {
        if (-not $Session) {
            Write-Error "Usage: tmx new <name> [cmd]"
            exit 1
        }
        
        if (Test-SessionExists $Session) {
            Write-Error "Session '$Session' already exists"
            exit 1
        }
        
        Invoke-Tmux "new-session" "-d" "-s" $Session
        
        if ($CmdStr) {
            Invoke-Tmux "send-keys" "-t" $Session $CmdStr
            Invoke-Tmux "send-keys" "-t" $Session "Enter"
        }
        
        Write-Host "Created session: $Session"
    }
    
    { $_ -in "send", "s" } {
        if (-not $Session -or -not $CmdStr) {
            Write-Error "Usage: tmx send <session> `"<cmd>`""
            exit 1
        }
        
        if (-not (Test-SessionExists $Session)) {
            Write-Error "Session '$Session' not found"
            exit 1
        }
        
        Invoke-Tmux "send-keys" "-t" $Session $CmdStr
        Invoke-Tmux "send-keys" "-t" $Session "Enter"
    }
    
    { $_ -in "capture", "c" } {
        if (-not $Session) {
            Write-Error "Usage: tmx capture <session> [lines]"
            exit 1
        }
        
        if (-not (Test-SessionExists $Session)) {
            Write-Error "Session '$Session' not found"
            exit 1
        }
        
        Invoke-Tmux "capture-pane" "-p" "-J" "-t" $Session "-S" "-$Lines"
    }
    
    { $_ -in "sync", "sy" } {
        if (-not $Session -or -not $CmdStr) {
            Write-Error "Usage: tmx sync <session> `"<cmd>`" [-Prompt <pattern> | -Timeout <sec>]"
            exit 1
        }
        
        if (-not (Test-SessionExists $Session)) {
            Write-Error "Session '$Session' not found"
            exit 1
        }
        
        # Send command
        Invoke-Tmux "send-keys" "-t" $Session $CmdStr
        Invoke-Tmux "send-keys" "-t" $Session "Enter"
        
        # Wait mode
        if ($Timeout -gt 0) {
            # Fixed timeout mode
            Start-Sleep -Seconds $Timeout
        } else {
            # Prompt detection mode
            $pattern = if ($Prompt) { $Prompt } else { $DefaultPrompts }
            Wait-ForPrompt -Session $Session -Pattern $pattern | Out-Null
        }
        
        # Capture output
        Invoke-Tmux "capture-pane" "-p" "-J" "-t" $Session "-S" "-$Lines"
    }
    
    { $_ -in "list", "ls", "l" } {
        Invoke-Tmux "list-sessions" "-F" "#{session_name} #{session_windows}w #{?session_attached,attached,detached}" 2>$null
        if (-not $?) {
            Write-Host "No sessions"
        }
    }
    
    { $_ -in "kill", "k" } {
        if (-not $Session) {
            Write-Error "Usage: tmx kill <session>"
            exit 1
        }
        
        if (-not (Test-SessionExists $Session)) {
            Write-Error "Session '$Session' not found"
            exit 1
        }
        
        Invoke-Tmux "kill-session" "-t" $Session
        Write-Host "Killed session: $Session"
    }
    
    { $_ -in "attach", "a" } {
        if (-not $Session) {
            Write-Error "Usage: tmx attach <session>"
            exit 1
        }
        
        if (-not (Test-SessionExists $Session)) {
            Write-Error "Session '$Session' not found"
            exit 1
        }
        
        Invoke-Tmux "attach" "-t" $Session
    }
    
    { $_ -in "-h", "--help", "help" } {
        Show-Help
    }
    
    default {
        if ($Command) {
            Write-Error "Unknown command: $Command"
        }
        Show-Help
        exit 1
    }
}
