[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$CodexHome = (Join-Path $env:USERPROFILE '.codex')
)

$ErrorActionPreference = 'Stop'
$begin = '<!-- CODEX-SMART-ROUTER:BEGIN -->'
$end = '<!-- CODEX-SMART-ROUTER:END -->'
$agentsPath = Join-Path $CodexHome 'AGENTS.md'

if (-not (Test-Path -LiteralPath $agentsPath)) {
    [PSCustomObject]@{ Agents = $agentsPath; Removed = $false } | ConvertTo-Json -Compress
    exit 0
}

$existing = Get-Content -LiteralPath $agentsPath -Raw
$pattern = '(?s)' + [regex]::Escape($begin) + '.*?' + [regex]::Escape($end)
if ($existing -notmatch $pattern) {
    [PSCustomObject]@{ Agents = $agentsPath; Removed = $false } | ConvertTo-Json -Compress
    exit 0
}

$clean = [regex]::Replace($existing, $pattern, '').Trim()
if ($PSCmdlet.ShouldProcess($agentsPath, 'remove managed smart-router orchestration policy')) {
    if ([string]::IsNullOrWhiteSpace($clean)) {
        Remove-Item -LiteralPath $agentsPath -Force
    } else {
        Set-Content -LiteralPath $agentsPath -Value ($clean + [Environment]::NewLine) -Encoding utf8NoBOM
    }
}

[PSCustomObject]@{ Agents = $agentsPath; Removed = $true } | ConvertTo-Json -Compress
