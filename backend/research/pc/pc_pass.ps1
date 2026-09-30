# Replication R1 of the Kronos look on this PC: the one measurement pass at three samples a forecast, on the GPU.
$ErrorActionPreference = "Continue"
$Host.UI.RawUI.WindowTitle = "Kronos on this PC - replication R1, the measurement pass (this window stays open when done)"
$log = Join-Path $HOME "kronos_pc.log"
function Say($t) { $line = "{0} {1}" -f (Get-Date -Format "HH:mm:ss"), $t; Write-Host $line -ForegroundColor Cyan; Add-Content -Path $log -Value $line }
function Run($label, $exe, $argv) {
  Say ("> " + $label)
  & $exe @argv 2>&1 | ForEach-Object { $s = "$_"; Write-Host $s; Add-Content -Path $log -Value $s }
}
$backend = Join-Path $HOME "intraday-trading-agent\backend"
$py = Join-Path $backend "research\.kvenv\Scripts\python.exe"
$env:KRONOS_DEVICE = "cuda"
$env:PYTHONUNBUFFERED = "1"
$env:HF_HUB_DISABLE_PROGRESS_BARS = "1"
Say "REPLICATION R1 started: stage 0 again (the sample count must match the record: 3), then 43,362 forecasts at three samples on the GPU, then the statistics and the gate. Progress lines come every 20 session-times."
Push-Location $backend
Run "the pass" $py @("-m", "research.kronos_l40_launch", "worker", "run")
Pop-Location
$out = Join-Path $HOME "intraday-trading-agent\docs\research\data\kronos_l40_result.json"
if (Test-Path $out) { Say ("R1 result written: " + $out) } else { Say "R1 wrote no result: read the lines above" }
New-Item -ItemType File -Force -Path (Join-Path $HOME "kronos_pass.done") | Out-Null
