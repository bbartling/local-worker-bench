# Run as the ordinary desktop user. No inference is started by Start or Status.
[CmdletBinding()]
param(
    [ValidateSet('Start','Status','Stop')][string]$Action = 'Status',
    [string]$LocalAddress,
    [ValidateRange(1024,65535)][int]$Port = 11435
)
$ErrorActionPreference = 'Stop'
$folder = Join-Path $env:LOCALAPPDATA 'LocalWorkerBench'
$statePath = Join-Path $folder "lan-server-$Port.json"
function Get-OwnedServer {
    if (!(Test-Path -LiteralPath $statePath)) { return $null }
    $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    $owned = Get-Process -Id $state.pid -ErrorAction SilentlyContinue
    if (!$owned) { return $null }
    if ($owned.Path -ne $state.exe -or $owned.StartTime.ToUniversalTime().Ticks -ne ([datetime]$state.started_utc).ToUniversalTime().Ticks) {
        throw 'Saved PID belongs to a different process; refusing to stop or reuse it.'
    }
    return @{state=$state; process=$owned}
}
$current = Get-OwnedServer
if ($Action -eq 'Stop') {
    if ($current) { & taskkill.exe /PID $current.process.Id /T /F | Out-Null }
    if (Test-Path -LiteralPath $statePath) { Remove-Item -LiteralPath $statePath }
    Write-Output 'Owned LAN server stopped; firewall configuration is unchanged.'
    exit 0
}
if ($Action -eq 'Start') {
    if ($current) { throw 'The owned server is already running; use Status.' }
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    if ((New-Object Security.Principal.WindowsPrincipal($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Start inference as the ordinary desktop user, not as administrator.'
    }
    if (!$LocalAddress) { throw 'Start requires -LocalAddress: the specific private LAN IPv4 address.' }
    $ip = [Net.IPAddress]::Parse($LocalAddress)
    $bytes = $ip.GetAddressBytes()
    if ($ip.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork -or
        !($bytes[0] -eq 10 -or ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31) -or ($bytes[0] -eq 192 -and $bytes[1] -eq 168))) {
        throw 'Use a numeric RFC1918 IPv4 address.'
    }
    $nic = Get-NetIPAddress -IPAddress $LocalAddress -AddressFamily IPv4 -ErrorAction Stop
    if ((Get-NetConnectionProfile -InterfaceIndex $nic.InterfaceIndex).NetworkCategory -ne 'Private') {
        throw 'Selected interface is not Private.'
    }
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { throw 'Port is already in use; no existing process was stopped.' }
    $exe = Join-Path $env:LOCALAPPDATA 'Programs/Ollama/ollama.exe'
    if (!(Test-Path -LiteralPath $exe)) { throw 'Ollama is not installed in its default Windows location.' }
    New-Item -ItemType Directory -Path $folder -Force | Out-Null
    $settings = @{OLLAMA_HOST="${LocalAddress}:$Port"; OLLAMA_NO_CLOUD='true'; OLLAMA_NOPRUNE='true';
                  OLLAMA_DEBUG_LOG_REQUESTS='false'; OLLAMA_NUM_PARALLEL='1'; OLLAMA_MAX_LOADED_MODELS='1';
                  OLLAMA_CONTEXT_LENGTH='2048'; OLLAMA_KEEP_ALIVE='0'}
    $previous = @{}
    try {
        foreach ($key in $settings.Keys) {
            $previous[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
            [Environment]::SetEnvironmentVariable($key, $settings[$key], 'Process')
        }
        $server = Start-Process -FilePath $exe -ArgumentList 'serve' -WindowStyle Hidden -PassThru -WorkingDirectory (Split-Path $exe) -RedirectStandardOutput (Join-Path $folder 'lan-server.stdout.log') -RedirectStandardError (Join-Path $folder 'lan-server.stderr.log')
    } finally {
        foreach ($key in $previous.Keys) { [Environment]::SetEnvironmentVariable($key, $previous[$key], 'Process') }
    }
    try {
        $ready = $false
        for ($attempt = 0; $attempt -lt 40; $attempt++) {
            if ($server.HasExited) { throw 'Owned Ollama server exited; inspect the local server log.' }
            try { $null = Invoke-RestMethod "http://${LocalAddress}:$Port/api/version" -TimeoutSec 1; $ready=$true; break }
            catch { Start-Sleep -Milliseconds 250 }
        }
        if (!$ready) { throw 'LAN server startup timed out.' }
        $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen
        if ($listeners.LocalAddress -ne $LocalAddress -or $listeners.OwningProcess -ne $server.Id) {
            throw 'Listener ownership/address does not match the requested server.'
        }
        @{pid=$server.Id; exe=$exe; started_utc=$server.StartTime.ToUniversalTime().ToString('o');
          endpoint="http://${LocalAddress}:$Port"; local_address=$LocalAddress} | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8
    } catch {
        if (!$server.HasExited) { & taskkill.exe /PID $server.Id /T /F | Out-Null }
        throw
    }
    $current = Get-OwnedServer
}
if (!$current) { @{running=$false; inference_started=$false} | ConvertTo-Json; exit 0 }
$endpoint = $current.state.endpoint
$version = Invoke-RestMethod "$endpoint/api/version" -TimeoutSec 3
$loaded = Invoke-RestMethod "$endpoint/api/ps" -TimeoutSec 3
$cached = Invoke-RestMethod "$endpoint/api/tags" -TimeoutSec 3
@{running=$true; pid=$current.process.Id; endpoint=$endpoint; version=$version.version;
  loaded_models=@($loaded.models | ForEach-Object {$_.name}); cached_models=@($cached.models | ForEach-Object {$_.name});
  free_ram_gib=[math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,2);
  inference_started=$false} | ConvertTo-Json -Depth 4
