[CmdletBinding(SupportsShouldProcess)]
param([switch]$RemoveData)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Push-Location $RepoRoot
try {
    if ($RemoveData) {
        if ($PSCmdlet.ShouldProcess('LiteLLM containers and Postgres volume', 'docker compose down -v')) {
            docker compose down -v
        }
    } else {
        if ($PSCmdlet.ShouldProcess('LiteLLM containers', 'docker compose down')) {
            docker compose down
        }
    }
} finally {
    Pop-Location
}
