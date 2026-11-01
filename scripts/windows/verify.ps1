[CmdletBinding()]
param(
    [string]$CodexHome = (Join-Path $env:USERPROFILE '.codex')
)

$ErrorActionPreference = 'Stop'
$health = Invoke-RestMethod -Method Get -Uri 'http://127.0.0.1:4000/health/liveliness' -TimeoutSec 10
Write-Host 'LiteLLM health endpoint: OK'

$CodexEnvFile = Join-Path $CodexHome '.env'
$keyPresent = -not [string]::IsNullOrWhiteSpace($env:LITELLM_API_KEY)

if (-not $keyPresent -and (Test-Path $CodexEnvFile)) {
    $keyLine = Get-Content -Path $CodexEnvFile |
        Where-Object { $_ -match '^\s*LITELLM_API_KEY\s*=\s*.+$' } |
        Select-Object -First 1

    if ($null -ne $keyLine) {
        $keyValue = ($keyLine -split '=', 2)[1].Trim()
        $keyPresent = -not [string]::IsNullOrWhiteSpace($keyValue)
    }
}

if (-not $keyPresent) {
    Write-Warning "LITELLM_API_KEY was not found in the current process or $CodexEnvFile. Codex will omit x-litellm-api-key until one of those sources contains the gateway key."
    exit 2
}

Write-Host 'LiteLLM gateway key source is available without printing the key.'
Write-Host 'Live ChatGPT subscription verification must be executed from Codex so its OAuth Authorization header is forwarded.'
exit 0
