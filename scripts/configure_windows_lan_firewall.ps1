# Administrator rights are used for these firewall rules only, never inference.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$LocalAddress,
    [Parameter(Mandatory=$true)][string]$PeerAddress,
    [ValidateRange(1024,65535)][int]$Port = 11435,
    [switch]$Remove,
    [string]$ReceiptPath
)
$ErrorActionPreference = 'Stop'
$ruleGroup = 'Local Worker Bench managed LAN rules'
$names = @("LocalWorkerBench-$Port-AllowPeer", "LocalWorkerBench-$Port-BlockOthers", "LocalWorkerBench-$Port-BlockNonPrivate")
try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    if (!(New-Object Security.Principal.WindowsPrincipal($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Run this firewall script as administrator. Do not run the model server elevated.'
    }
    foreach ($text in @($LocalAddress, $PeerAddress)) {
        $ip = [Net.IPAddress]::Parse($text)
        $b = $ip.GetAddressBytes()
        if ($ip.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork -or
            !($b[0] -eq 10 -or ($b[0] -eq 172 -and $b[1] -ge 16 -and $b[1] -le 31) -or ($b[0] -eq 192 -and $b[1] -eq 168))) {
            throw 'Use numeric RFC1918 IPv4 addresses.'
        }
    }
    foreach ($name in $names) {
        $existing = Get-NetFirewallRule -Name $name -ErrorAction SilentlyContinue
        if ($existing -and $existing.Group -ne $ruleGroup) { throw "Refusing to replace an unrelated rule: $name" }
    }
    if ($Remove) {
        foreach ($name in $names) { Get-NetFirewallRule -Name $name -ErrorAction SilentlyContinue | Remove-NetFirewallRule }
        $result = @{success=$true; removed=$names}
    } else {
        $nic = Get-NetIPAddress -AddressFamily IPv4 -IPAddress $LocalAddress -ErrorAction Stop
        $profile = Get-NetConnectionProfile -InterfaceIndex $nic.InterfaceIndex -ErrorAction Stop
        if ($profile.NetworkCategory -ne 'Private') { throw 'The selected NIC must already be Private; this script does not change network trust.' }
        $exe = Join-Path $env:LOCALAPPDATA 'Programs/Ollama/ollama.exe'
        if (!(Test-Path -LiteralPath $exe)) { throw 'Ollama executable was not found.' }
        # Block the complement of the approved /32, even if another broad allow rule exists.
        $peer = [Net.IPAddress]::Parse($PeerAddress).GetAddressBytes()
        [array]::Reverse($peer)
        $number = [BitConverter]::ToUInt32($peer, 0)
        function AddressFromNumber([uint32]$value) {
            $bytes = [BitConverter]::GetBytes($value)
            [array]::Reverse($bytes)
            return (New-Object Net.IPAddress -ArgumentList (,$bytes)).ToString()
        }
        $blocked = @("0.0.0.0-$(AddressFromNumber ($number - 1))", "$(AddressFromNumber ($number + 1))-255.255.255.255")
        $common = @{Direction='Inbound'; Protocol='TCP'; LocalPort=$Port; LocalAddress=$LocalAddress;
                    Program=$exe; InterfaceAlias=$nic.InterfaceAlias; Group=$ruleGroup; Enabled='True'; EdgeTraversalPolicy='Block'}
        # Install deny rules before the allow. Only this script's three rules are touched.
        foreach ($index in @(1,2,0)) {
            $name = $names[$index]
            Get-NetFirewallRule -Name $name -ErrorAction SilentlyContinue | Remove-NetFirewallRule
            if ($index -eq 1) { New-NetFirewallRule @common -Name $name -DisplayName $name -Action Block -Profile Any -RemoteAddress $blocked | Out-Null }
            elseif ($index -eq 2) { New-NetFirewallRule @common -Name $name -DisplayName $name -Action Block -Profile Public,Domain -RemoteAddress Any | Out-Null }
            else { New-NetFirewallRule @common -Name $name -DisplayName $name -Action Allow -Profile Private -RemoteAddress $PeerAddress | Out-Null }
        }
        $result = @{success=$true; local_address=$LocalAddress; peer_address=$PeerAddress; port=$Port; rules=$names}
    }
    $encoded = $result | ConvertTo-Json -Depth 4
    if ($ReceiptPath) { $encoded | Set-Content -LiteralPath $ReceiptPath -Encoding UTF8 }
    Write-Output $encoded
} catch {
    $encoded = @{success=$false; error=$_.Exception.Message} | ConvertTo-Json
    if ($ReceiptPath) { $encoded | Set-Content -LiteralPath $ReceiptPath -Encoding UTF8 }
    Write-Error $encoded
    exit 1
}
