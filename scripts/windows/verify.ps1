[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$health = Invoke-RestMethod -Method Get -Uri 'http://127.0.0.1:4000/health/liveliness' -TimeoutSec 10
Write-Host 'LiteLLM health endpoint: OK'

if (-not $env:LITELLM_API_KEY) {
    Write-Warning 'LITELLM_API_KEY is not set in this PowerShell process; gateway-authenticated request test skipped.'
    exit 2
}

Write-Host 'Gateway key environment variable is present. Live ChatGPT subscription verification must be executed from Codex so its OAuth Authorization header is forwarded.'
exit 0
