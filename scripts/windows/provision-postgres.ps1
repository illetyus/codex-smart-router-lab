[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$HostName = '127.0.0.1',
    [int]$Port = 5432,
    [string]$AdminUser = 'postgres',
    [SecureString]$AdminPassword,
    [string]$DatabaseName = 'litellm',
    [string]$RoleName = 'litellm',
    [string]$RuntimeRoot = (Join-Path $env:LOCALAPPDATA 'CodexSmartRouter')
)

$ErrorActionPreference = 'Stop'

function Resolve-PostgresCommand([string]$Name) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -ne $command) { return $command.Source }
    $candidate = Join-Path (Join-Path (Join-Path $env:ProgramFiles 'PostgreSQL') '16') 'bin'
    $candidate = Join-Path $candidate "$Name.exe"
    if (Test-Path -LiteralPath $candidate) { return $candidate }
    return $null
}

function New-RandomHex([int]$Bytes = 24) {
    $buffer = New-Object byte[] $Bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($buffer)
    return -join ($buffer | ForEach-Object { $_.ToString('x2') })
}

function Protect-SecretFile([string]$Path) {
    $acl = Get-Acl -LiteralPath $Path
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($rule in @($acl.Access)) {
        [void]$acl.RemoveAccessRuleAll($rule)
    }
    $sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
    $rule = [System.Security.AccessControl.FileSystemAccessRule]::new(
        $sid,
        [System.Security.AccessControl.FileSystemRights]::FullControl,
        [System.Security.AccessControl.AccessControlType]::Allow
    )
    [void]$acl.AddAccessRule($rule)
    Set-Acl -LiteralPath $Path -AclObject $acl
}

function Set-DotEnvValue([string]$Path, [string]$Name, [string]$Value) {
    $lines = @()
    if (Test-Path -LiteralPath $Path) {
        $lines = @(Get-Content -LiteralPath $Path)
    }

    $replacement = "$Name=$Value"
    $found = $false
    $updated = foreach ($line in $lines) {
        if ($line -match ("^\s*{0}\s*=" -f [regex]::Escape($Name))) {
            if (-not $found) {
                $replacement
                $found = $true
            }
        }
        else {
            $line
        }
    }
    if (-not $found) {
        $updated = @($updated) + $replacement
    }
    $updated | Set-Content -LiteralPath $Path -Encoding utf8NoBOM
}

if ($HostName -notin @('127.0.0.1','localhost','::1')) {
    throw 'This lab provisions only a local PostgreSQL instance.'
}

foreach ($identifier in @($DatabaseName, $RoleName, $AdminUser)) {
    if ($identifier -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
        throw "Unsafe PostgreSQL identifier: $identifier"
    }
}

$psql = Resolve-PostgresCommand 'psql'
$createdb = Resolve-PostgresCommand 'createdb'
if ([string]::IsNullOrWhiteSpace($psql) -or [string]::IsNullOrWhiteSpace($createdb)) {
    throw 'psql/createdb were not found. Install PostgreSQL 16 command-line tools first.'
}

if ($null -eq $AdminPassword) {
    $AdminPassword = Read-Host "Password for PostgreSQL administrator '$AdminUser'" -AsSecureString
}

$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($AdminPassword)
$adminPlain = $null
try {
    $adminPlain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    $env:PGPASSWORD = $adminPlain

    & $psql -h $HostName -p $Port -U $AdminUser -d postgres -v ON_ERROR_STOP=1 -tAc 'SELECT 1;' *> $null
    if ($LASTEXITCODE -ne 0) {
        throw 'PostgreSQL administrator authentication failed.'
    }

    $serverVersion = (& $psql -h $HostName -p $Port -U $AdminUser -d postgres -v ON_ERROR_STOP=1 -tAc 'SHOW server_version;').Trim()
    if ($LASTEXITCODE -ne 0 -or $serverVersion -notmatch '^(\d+)\.(\d+)') {
        throw "Unable to verify PostgreSQL server version: $serverVersion"
    }
    $serverMajor = [int]$Matches[1]
    $serverMinor = [int]$Matches[2]
    if ($serverMajor -ne 16 -or $serverMinor -lt 15) {
        throw "PostgreSQL 16.15 or newer 16.x is required; found $serverVersion"
    }

    $listenAddresses = (& $psql -h $HostName -p $Port -U $AdminUser -d postgres -v ON_ERROR_STOP=1 -tAc 'SHOW listen_addresses;').Trim()
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to inspect PostgreSQL listen_addresses.'
    }
    $allowedListeners = @('localhost','127.0.0.1','::1')
    $listeners = @($listenAddresses.Split(',') | ForEach-Object { $_.Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($listeners.Count -eq 0 -or @($listeners | Where-Object { $_ -notin $allowedListeners }).Count -gt 0 -or $listenAddresses -in @('*','0.0.0.0')) {
        throw "PostgreSQL listen_addresses is not local-only: $listenAddresses"
    }

    $dbPassword = New-RandomHex
    $roleExists = (& $psql -h $HostName -p $Port -U $AdminUser -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname = '$RoleName';").Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Failed to inspect PostgreSQL roles.' }

    if ($roleExists -eq '1') {
        & $psql -h $HostName -p $Port -U $AdminUser -d postgres -v ON_ERROR_STOP=1 -c "ALTER ROLE $RoleName WITH LOGIN PASSWORD '$dbPassword';" *> $null
    }
    else {
        & $psql -h $HostName -p $Port -U $AdminUser -d postgres -v ON_ERROR_STOP=1 -c "CREATE ROLE $RoleName WITH LOGIN PASSWORD '$dbPassword';" *> $null
    }
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create/update the LiteLLM PostgreSQL role.' }

    $dbExists = (& $psql -h $HostName -p $Port -U $AdminUser -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$DatabaseName';").Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Failed to inspect PostgreSQL databases.' }

    if ($dbExists -ne '1') {
        & $createdb -h $HostName -p $Port -U $AdminUser -O $RoleName $DatabaseName
        if ($LASTEXITCODE -ne 0) { throw 'Failed to create the LiteLLM PostgreSQL database.' }
    }
    else {
        & $psql -h $HostName -p $Port -U $AdminUser -d postgres -v ON_ERROR_STOP=1 -c "ALTER DATABASE $DatabaseName OWNER TO $RoleName;" *> $null
        if ($LASTEXITCODE -ne 0) { throw 'Failed to set the LiteLLM database owner.' }
    }

    New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
    $envFile = Join-Path $RuntimeRoot 'router.env'
    $databaseUrl = "postgresql://${RoleName}:${dbPassword}@${HostName}:$Port/$DatabaseName"

    if ($PSCmdlet.ShouldProcess($envFile, 'store local DATABASE_URL for the native router')) {
        Set-DotEnvValue -Path $envFile -Name 'DATABASE_URL' -Value $databaseUrl
        Protect-SecretFile -Path $envFile
    }

    [PSCustomObject]@{
        Database = $DatabaseName
        Role = $RoleName
        Host = $HostName
        Port = $Port
        EnvFile = $envFile
    } | ConvertTo-Json -Compress
}
finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    $adminPlain = $null
}
