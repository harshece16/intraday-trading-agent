param([string]$Name, [string]$Script)
schtasks /delete /tn $Name /f 2>$null | Out-Null
$tr = "powershell.exe -NoExit -ExecutionPolicy Bypass -File $HOME\$Script"
schtasks /create /tn $Name /tr $tr /sc once /st 00:00 /it /f | Out-Null
schtasks /run /tn $Name | Out-Null
Start-Sleep 2
schtasks /query /tn $Name /fo list | Select-String "Status"
