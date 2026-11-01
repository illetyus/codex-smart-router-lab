[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$CodexHome = (Join-Path $env:USERPROFILE '.codex')
)

$ErrorActionPreference = 'Stop'
$configPath = Join-Path $CodexHome 'config.toml'
$backupPath = Join-Path $CodexHome 'config.toml.pre-litellm-backup'

if (-not (Test-Path -LiteralPath $configPath)) {
    throw "Codex config.toml was not found: $configPath"
}

if (-not (Test-Path -LiteralPath $backupPath)) {
    Copy-Item -LiteralPath $configPath -Destination $backupPath
}

$lines = @(Get-Content -LiteralPath $configPath)

# Remove an existing LiteLLM provider table so repeated runs are idempotent.
$withoutProvider = New-Object System.Collections.Generic.List[string]
$insideTarget = $false
foreach ($line in $lines) {
    if ($line -match '^\s*\[model_providers\.litellm_subscription\]\s*$') {
        $insideTarget = $true
        continue
    }

    if ($insideTarget -and $line -match '^\s*\[') {
        $insideTarget = $false
    }

    if (-not $insideTarget) {
        [void]$withoutProvider.Add($line)
    }
}

# Set only the top-level model_provider assignment, before the first TOML table.
$patched = New-Object System.Collections.Generic.List[string]
$seenTable = $false
$providerWritten = $false
foreach ($line in $withoutProvider) {
    if (-not $seenTable -and $line -match '^\s*\[') {
        if (-not $providerWritten) {
            [void]$patched.Add('model_provider = "litellm_subscription"')
            $providerWritten = $true
        }
        $seenTable = $true
    }

    if (-not $seenTable -and $line -match '^\s*model_provider\s*=') {
        if (-not $providerWritten) {
            [void]$patched.Add('model_provider = "litellm_subscription"')
            $providerWritten = $true
        }
        continue
    }

    [void]$patched.Add($line)
}

if (-not $providerWritten) {
    [void]$patched.Add('model_provider = "litellm_subscription"')
}

while ($patched.Count -gt 0 -and [string]::IsNullOrWhiteSpace($patched[$patched.Count - 1])) {
    $patched.RemoveAt($patched.Count - 1)
}

$providerBlock = @(
    '',
    '[model_providers.litellm_subscription]',
    'name = "LiteLLM subscription"',
    'base_url = "http://127.0.0.1:4000/v1"',
    'wire_api = "responses"',
    'supports_websockets = false',
    'requires_openai_auth = true',
    'env_http_headers = { "x-litellm-api-key" = "LITELLM_API_KEY" }'
)

$output = @($patched) + $providerBlock
if ($PSCmdlet.ShouldProcess($configPath, 'configure LiteLLM subscription provider')) {
    $output | Set-Content -LiteralPath $configPath -Encoding utf8NoBOM
    $appliedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $configPath).Hash
    Set-Content -LiteralPath (Join-Path $CodexHome 'config.toml.pre-litellm-applied.sha256') -Value $appliedHash -Encoding ascii
}

[PSCustomObject]@{
    Config = $configPath
    Backup = $backupPath
    Provider = 'litellm_subscription'
} | ConvertTo-Json -Compress
