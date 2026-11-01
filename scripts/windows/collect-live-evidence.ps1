[CmdletBinding()]
param(
    [string]$SessionsRoot = (Join-Path $env:USERPROFILE '.codex\sessions'),
    [string]$OutputPath = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path 'evidence\supported-model-effort.json')
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$collector = Join-Path $repoRoot 'tools\collect_rollout_evidence.py'

if (-not (Test-Path -LiteralPath $SessionsRoot)) {
    throw "Codex sessions directory not found: $SessionsRoot"
}
if (-not (Test-Path -LiteralPath $collector)) {
    throw "Rollout collector not found: $collector"
}

$outDir = Split-Path -Parent $OutputPath
if (-not [string]::IsNullOrWhiteSpace($outDir)) {
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
}

python $collector --sessions-root $SessionsRoot --out $OutputPath
if ($LASTEXITCODE -ne 0) {
    throw "Rollout evidence collector failed with exit code $LASTEXITCODE"
}

Write-Host "Codex rollout evidence written to $OutputPath"
Write-Host 'The file contains rollout metadata only; verify physical Auto Router selections separately in LiteLLM logs.'
