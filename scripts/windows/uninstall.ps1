[CmdletBinding(SupportsShouldProcess)]
param(
    [ValidateSet('native','docker')]
    [string]$Runtime = 'native',
    [switch]$RemoveData,
    [string]$RuntimeRoot = (Join-Path $env:LOCALAPPDATA 'CodexSmartRouter'),
    [string]$TaskName = 'Codex Smart Router'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

if ($Runtime -eq 'docker') {
    Push-Location $RepoRoot
    try {
        if ($RemoveData) {
            if ($PSCmdlet.ShouldProcess('LiteLLM containers and Postgres volume', 'docker compose down -v')) {
                docker compose down -v
            }
        }
        else {
            if ($PSCmdlet.ShouldProcess('LiteLLM containers', 'docker compose down')) {
                docker compose down
            }
        }
    }
    finally {
        Pop-Location
    }
    exit 0
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -ne $task) {
    if ($PSCmdlet.ShouldProcess($TaskName, 'stop and unregister native router task')) {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
}

if ($RemoveData -and (Test-Path -LiteralPath $RuntimeRoot)) {
    if ($PSCmdlet.ShouldProcess($RuntimeRoot, 'remove native LiteLLM source, configs, secrets, and logs')) {
        Remove-Item -LiteralPath $RuntimeRoot -Recurse -Force
    }
}

Write-Host 'Native router task removed. PostgreSQL database is preserved.'
if (-not $RemoveData) {
    Write-Host "Runtime files are preserved at $RuntimeRoot."
}
