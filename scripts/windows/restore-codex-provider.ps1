[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$CodexHome = (Join-Path $env:USERPROFILE '.codex')
)

$ErrorActionPreference = 'Stop'
$configPath = Join-Path $CodexHome 'config.toml'
$configBackup = Join-Path $CodexHome 'config.toml.pre-litellm-backup'
$envPath = Join-Path $CodexHome '.env'
$envBackup = Join-Path $CodexHome '.env.pre-litellm-backup'

if (-not (Test-Path -LiteralPath $configBackup)) {
    throw "Codex config backup was not found: $configBackup"
}

if ($PSCmdlet.ShouldProcess($configPath, 'restore pre-LiteLLM Codex configuration')) {
    Copy-Item -LiteralPath $configBackup -Destination $configPath -Force
}

$envAction = 'unchanged'
if (Test-Path -LiteralPath $envBackup) {
    if ($PSCmdlet.ShouldProcess($envPath, 'restore pre-LiteLLM Codex dotenv')) {
        Copy-Item -LiteralPath $envBackup -Destination $envPath -Force
    }
    $envAction = 'restored-backup'
}
elseif (Test-Path -LiteralPath $envPath) {
    $remaining = @(
        Get-Content -LiteralPath $envPath |
            Where-Object { $_ -notmatch '^\s*LITELLM_API_KEY\s*=' }
    )
    if ($PSCmdlet.ShouldProcess($envPath, 'remove LiteLLM virtual key from Codex dotenv')) {
        $remaining | Set-Content -LiteralPath $envPath -Encoding utf8NoBOM
    }
    $envAction = 'removed-litellm-key'
}

[PSCustomObject]@{
    Config = $configPath
    ConfigBackup = $configBackup
    Env = $envPath
    EnvAction = $envAction
} | ConvertTo-Json -Compress
