$Host.UI.RawUI.WindowTitle = "Kronos on this PC - live log (close any time; nothing runs in this window)"
$log = Join-Path $HOME "kronos_pc.log"
if (-not (Test-Path $log)) { New-Item -ItemType File -Path $log | Out-Null }
Get-Content -Path $log -Wait -Tail 40
