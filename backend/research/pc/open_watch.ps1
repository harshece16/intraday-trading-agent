$script = Join-Path $HOME "watch_window.ps1"
schtasks /delete /tn KronosWatch /f 2>$null | Out-Null
$tr = "powershell.exe -NoExit -ExecutionPolicy Bypass -File $script"
schtasks /create /tn KronosWatch /tr $tr /sc once /st 00:00 /it /f | Out-Null
schtasks /run /tn KronosWatch | Out-Null
Add-Content -Path (Join-Path $HOME "kronos_pc.log") -Value ("{0} live log window opened on this PC. Everything the Mac does here is appended to this file." -f (Get-Date -Format "HH:mm:ss"))
