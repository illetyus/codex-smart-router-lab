[CmdletBinding()]
param(
    [string]$SessionsRoot = (Join-Path $env:USERPROFILE '.codex\sessions')
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $SessionsRoot)) {
    throw "Codex sessions directory not found: $SessionsRoot"
}

$files = Get-ChildItem -LiteralPath $SessionsRoot -Recurse -File -Filter 'rollout-*.jsonl' |
    Sort-Object LastWriteTime -Descending

foreach ($file in $files) {
    $sessionMeta = $null
    $lastTurn = $null

    foreach ($line in Get-Content -LiteralPath $file.FullName) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        try {
            $item = $line | ConvertFrom-Json -Depth 100
        }
        catch {
            continue
        }

        if ($item.type -eq 'session_meta' -and $null -eq $sessionMeta) {
            $sessionMeta = $item.payload
            continue
        }

        if ($item.type -eq 'turn_context') {
            $lastTurn = $item.payload
        }
    }

    if ($null -eq $lastTurn -or [string]::IsNullOrWhiteSpace([string]$lastTurn.model)) {
        continue
    }

    if ([string]$lastTurn.model -eq 'codex-auto-review') {
        continue
    }

    $meta = $sessionMeta
    if ($null -ne $sessionMeta -and $null -ne $sessionMeta.meta) {
        $meta = $sessionMeta.meta
    }

    $source = $null
    if ($null -ne $meta -and $null -ne $meta.source) {
        if ($meta.source -is [string]) {
            $source = [string]$meta.source
        }
        else {
            $source = $meta.source | ConvertTo-Json -Compress -Depth 20
        }
    }

    [PSCustomObject]@{
        File      = $file.FullName
        Model     = [string]$lastTurn.model
        Effort    = if ($null -ne $lastTurn.effort) { [string]$lastTurn.effort } else { $null }
        Parent    = if ($null -ne $meta -and $null -ne $meta.parent_thread_id) { [string]$meta.parent_thread_id } else { $null }
        AgentRole = if ($null -ne $meta -and $null -ne $meta.agent_role) { [string]$meta.agent_role } else { $null }
        Source    = $source
    } | ConvertTo-Json -Compress -Depth 20
    exit 0
}

throw "No non-auto-review Codex rollout with a turn_context was found under $SessionsRoot"
