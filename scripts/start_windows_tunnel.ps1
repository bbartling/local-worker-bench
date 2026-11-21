# Explicit, temporary access for an agent on a trusted SSH host. No inference at startup.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Remote,
    [ValidateRange(1024,65535)][int]$RemotePort = 11435,
    [ValidateRange(1024,65535)][int]$LocalPort = 11435,
    [ValidateRange(15,3600)][int]$DurationSeconds = 900
)
$ErrorActionPreference = 'Stop'
if ($Remote -notmatch '^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+$') {
    throw 'Use a user@host SSH destination without spaces or options.'
}
$ollamaExe = Join-Path $env:LOCALAPPDATA 'Programs/Ollama/ollama.exe'
if (!(Test-Path -LiteralPath $ollamaExe)) { throw 'Ollama is not installed in the default Windows location.' }
if (Get-NetTCPConnection -State Listen -LocalPort $LocalPort -ErrorAction SilentlyContinue) {
    throw 'Local port is already in use. Do not interrupt another worker; choose another port.'
}
$server = $null
$tunnel = $null
try {
    $serverInfo = New-Object System.Diagnostics.ProcessStartInfo
    $serverInfo.FileName = $ollamaExe
    $serverInfo.Arguments = 'serve'
    $serverInfo.UseShellExecute = $false
    $serverInfo.CreateNoWindow = $true
    $serverInfo.EnvironmentVariables['OLLAMA_HOST'] = "127.0.0.1:$LocalPort"
    $serverInfo.EnvironmentVariables['OLLAMA_NO_CLOUD'] = 'true'
    $serverInfo.EnvironmentVariables['OLLAMA_NOPRUNE'] = 'true'
    $serverInfo.EnvironmentVariables['OLLAMA_DEBUG_LOG_REQUESTS'] = 'false'
    $serverInfo.EnvironmentVariables['OLLAMA_NUM_PARALLEL'] = '1'
    $serverInfo.EnvironmentVariables['OLLAMA_MAX_LOADED_MODELS'] = '1'
    $server = [System.Diagnostics.Process]::Start($serverInfo)
    $ready = $false
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        if ($server.HasExited) { throw 'Owned Ollama server exited during startup.' }
        try {
            $null = Invoke-RestMethod "http://127.0.0.1:$LocalPort/api/version" -TimeoutSec 1
            $ready = $true
            break
        } catch { Start-Sleep -Milliseconds 250 }
    }
    if (!$ready) { throw 'Ollama did not become ready.' }
    $sshInfo = New-Object System.Diagnostics.ProcessStartInfo
    $sshInfo.FileName = (Get-Command ssh.exe).Source
    $sshInfo.Arguments = "-N -T -o BatchMode=yes -o ConnectTimeout=5 -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=2 -R 127.0.0.1:${RemotePort}:127.0.0.1:${LocalPort} $Remote"
    $sshInfo.UseShellExecute = $false
    $sshInfo.CreateNoWindow = $true
    $tunnel = [System.Diagnostics.Process]::Start($sshInfo)
    Start-Sleep -Milliseconds 800
    $listeners = & ssh.exe -o BatchMode=yes -o ConnectTimeout=5 $Remote "ss -H -ltn 'sport = :$RemotePort'"
    if ($LASTEXITCODE -ne 0 -or !$listeners -or
        ($listeners -notmatch "\s127\.0\.0\.1:$RemotePort\s") -or
        ($listeners -match "\s(0\.0\.0\.0|\*|\[::\]):$RemotePort\s")) {
        throw 'Remote listener is absent or not loopback-only; refusing this tunnel.'
    }
    Write-Output "Temporary helper route requested: remote loopback port $RemotePort. Verify /api/version on the remote host. No inference has started."
    $deadline = (Get-Date).AddSeconds($DurationSeconds)
    while ((Get-Date) -lt $deadline) {
        if ($server.HasExited) { throw 'Owned Ollama server exited.' }
        if ($tunnel.WaitForExit(1000)) { throw 'SSH forwarding exited; check key authentication and remote port availability.' }
    }
} finally {
    foreach ($owned in @($tunnel, $server)) {
        if ($null -ne $owned -and !$owned.HasExited) {
            # Exact owned process tree only; never kill other Ollama/SSH sessions by name.
            & taskkill.exe /PID $owned.Id /T /F | Out-Null
            $owned.WaitForExit(5000) | Out-Null
        }
    }
    Write-Output 'Owned tunnel and server stopped. No firewall or global Ollama settings changed.'
}
