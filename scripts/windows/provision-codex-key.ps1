[CmdletBinding(SupportsShouldProcess)]
param(
    [ValidateSet('k2','k3','runtime')]
    [string]$Profile = 'k2',
    [string]$BaseUrl = 'http://127.0.0.1:4000',
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path,
    [string]$CodexHome = (Join-Path $env:USERPROFILE '.codex')
)

$ErrorActionPreference = 'Stop'

function Get-DotEnvValue {
    param(
        [Parameter(Mandatory)]
        [string]$Path,
        [Parameter(Mandatory)]
        [string]$Name
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Required env file not found: $Path"
    }

    $escaped = [regex]::Escape($Name)
    $line = Get-Content -LiteralPath $Path |
        Where-Object { $_ -match "^\s*$escaped\s*=\s*.+$" } |
        Select-Object -First 1

    if ($null -eq $line) {
        throw "$Name was not found in $Path"
    }

    return ($line -split '=', 2)[1].Trim()
}

$repoEnv = Join-Path $RepoRoot '.env'
$masterKey = Get-DotEnvValue -Path $repoEnv -Name 'LITELLM_MASTER_KEY'
if (-not $masterKey.StartsWith('sk-')) {
    throw 'LITELLM_MASTER_KEY has an unexpected format.'
}

$models = switch ($Profile) {
    'k2' { @('gpt-6.1-sol', 'gpt-image-2', 'codex-*') }
    'k3' { @('gpt-6.1-sol', 'gpt-6-luna', 'gpt-6.1-terra', 'gpt-6-sol', 'gpt-6-astra', 'gpt-image-2', 'codex-*') }
    'runtime' { @('gpt-6.1-sol', 'gpt-6-luna', 'gpt-6.1-terra', 'gpt-6-sol', 'gpt-6-astra', 'gpt-image-2', 'codex-*') }
}

$base = $BaseUrl.TrimEnd('/')
$masterHeaders = @{ Authorization = "Bearer $masterKey" }
$body = @{
    key_alias = "codex-$Profile"
    models = $models
} | ConvertTo-Json -Depth 10

$created = Invoke-RestMethod -Method Post -Uri "$base/key/generate" -Headers $masterHeaders -ContentType 'application/json' -Body $body -TimeoutSec 30

$virtualKey = [string]$created.key
if ([string]::IsNullOrWhiteSpace($virtualKey) -or -not $virtualKey.StartsWith('sk-')) {
    throw 'LiteLLM did not return a virtual key.'
}

$encodedVirtualKey = [uri]::EscapeDataString($virtualKey)
$keyInfo = Invoke-RestMethod -Method Get -Uri "$base/key/info?key=$encodedVirtualKey" -Headers $masterHeaders -TimeoutSec 30

$actualModels = @($keyInfo.info.models | ForEach-Object { [string]$_ } | Sort-Object)
$expectedModels = @($models | Sort-Object)
if (($actualModels -join [char]0) -ne ($expectedModels -join [char]0)) {
    throw "LiteLLM returned an unexpected model allowlist: $($actualModels -join ', ')"
}

if (-not (Test-Path -LiteralPath $CodexHome)) {
    New-Item -ItemType Directory -Force -Path $CodexHome | Out-Null
}

$codexEnv = Join-Path $CodexHome '.env'
$backup = Join-Path $CodexHome '.env.pre-litellm-backup'

if ((Test-Path -LiteralPath $codexEnv) -and -not (Test-Path -LiteralPath $backup)) {
    Copy-Item -LiteralPath $codexEnv -Destination $backup
}

$existing = @()
if (Test-Path -LiteralPath $codexEnv) {
    $existing = @(Get-Content -LiteralPath $codexEnv)
}

$replacement = "LITELLM_API_KEY=$virtualKey"
$found = $false
$updated = foreach ($line in $existing) {
    if ($line -match '^\s*LITELLM_API_KEY\s*=') {
        if (-not $found) {
            $found = $true
            $replacement
        }
    }
    else {
        $line
    }
}

if (-not $found) {
    $updated = @($updated) + $replacement
}

if ($PSCmdlet.ShouldProcess($codexEnv, "store restricted LiteLLM $Profile virtual key")) {
    $updated | Set-Content -LiteralPath $codexEnv -Encoding utf8NoBOM
    $appliedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $codexEnv).Hash
    Set-Content -LiteralPath (Join-Path $CodexHome '.env.pre-litellm-applied.sha256') -Value $appliedHash -Encoding ascii
}

[PSCustomObject]@{
    Profile = $Profile
    Models = $expectedModels
    CodexEnv = $codexEnv
    BackupCreated = (Test-Path -LiteralPath $backup)
} | ConvertTo-Json -Compress
