[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$CodexHome = (Join-Path $env:USERPROFILE '.codex'),
    [string]$TemplatePath = (Resolve-Path (Join-Path $PSScriptRoot '..\..\configs\codex\AGENTS.smart-router.md')).Path
)

$ErrorActionPreference = 'Stop'
$begin = '<!-- CODEX-SMART-ROUTER:BEGIN -->'
$end = '<!-- CODEX-SMART-ROUTER:END -->'
$agentsPath = Join-Path $CodexHome 'AGENTS.md'
$backupPath = Join-Path $CodexHome 'AGENTS.md.pre-smart-router-backup'

if (-not (Test-Path -LiteralPath $CodexHome)) {
    New-Item -ItemType Directory -Force -Path $CodexHome | Out-Null
}
if (-not (Test-Path -LiteralPath $TemplatePath)) {
    throw "Policy template not found: $TemplatePath"
}

$existing = if (Test-Path -LiteralPath $agentsPath) { Get-Content -LiteralPath $agentsPath -Raw } else { '' }
if ((Test-Path -LiteralPath $agentsPath) -and -not (Test-Path -LiteralPath $backupPath)) {
    Copy-Item -LiteralPath $agentsPath -Destination $backupPath
}

$pattern = '(?s)' + [regex]::Escape($begin) + '.*?' + [regex]::Escape($end)
$clean = [regex]::Replace($existing, $pattern, '').TrimEnd()
$template = (Get-Content -LiteralPath $TemplatePath -Raw).Trim()
$block = $begin + [Environment]::NewLine + $template + [Environment]::NewLine + $end
$output = if ([string]::IsNullOrWhiteSpace($clean)) { $block + [Environment]::NewLine } else { $clean + [Environment]::NewLine + [Environment]::NewLine + $block + [Environment]::NewLine }

if ($PSCmdlet.ShouldProcess($agentsPath, 'install managed smart-router orchestration policy')) {
    Set-Content -LiteralPath $agentsPath -Value $output -Encoding utf8NoBOM
}

[PSCustomObject]@{
    Agents = $agentsPath
    Backup = if (Test-Path -LiteralPath $backupPath) { $backupPath } else { $null }
    ManagedBlock = $true
} | ConvertTo-Json -Compress
