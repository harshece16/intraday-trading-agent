# Stage 0 of the Kronos look on this PC's GPU. Every line goes to the window and to kronos_pc.log.
$ErrorActionPreference = "Continue"
$Host.UI.RawUI.WindowTitle = "Kronos on this PC - stage 0 on the GPU (this window stays open when done)"
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
Say "STAGE 0 started on the GPU (KRONOS_DEVICE=cuda). Six checks in the pre-registered order; the first run downloads the model weights."
Push-Location $backend
Run "stage 0" $py @("-m", "research.kronos_l40_launch", "stage0")
Pop-Location
$out = Join-Path $HOME "intraday-trading-agent\docs\research\data\kronos_l40_stage0.json"
if (Test-Path $out) { Say ("STAGE 0 record written: " + $out) } else { Say "STAGE 0 wrote no record: read the lines above" }
New-Item -ItemType File -Force -Path (Join-Path $HOME "kronos_stage0.done") | Out-Null
