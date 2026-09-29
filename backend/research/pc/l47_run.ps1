# L47 on this PC (docs/research/prereg-qlib-lgbm-alpha158.md): one mode per run.
#   install : the Python 3.11 environment at venvs\l47 with lightgbm, pandas, numpy, scipy
#   stage0  : the seven stage 0 checks        -> docs\research\data\l47_stage0.json
#   train   : trains once, hashes the models  -> docs\research\data\l47_frozen.json
#   score   : the one scoring pass            -> docs\research\data\l47_result.json
# Every line goes to this window and to kronos_pc.log. Started as a visible scheduled task:
#   powershell -NoProfile -ExecutionPolicy Bypass -File run_task.ps1 -Name L47Stage0 -Script "l47_run.ps1 stage0"
# CPU only. Decision D2b: L47 never runs while an L46 model runs; this script refuses if one does.
param([Parameter(Position = 0)][string]$Mode)
$ErrorActionPreference = "Continue"
$modes = @("install", "stage0", "train", "score")
if ($modes -notcontains $Mode) { Write-Host "usage: l47_run.ps1 install|stage0|train|score"; exit 2 }
$Host.UI.RawUI.WindowTitle = "L47 on this PC - ${Mode} (this window stays open when done)"
$log = Join-Path $HOME "kronos_pc.log"
function Say($t) { $line = "{0} {1}" -f (Get-Date -Format "HH:mm:ss"), $t; Write-Host $line -ForegroundColor Cyan; Add-Content -Path $log -Value $line }
function Run($label, $exe, $argv) {
  Say ("> " + $label)
  & $exe @argv 2>&1 | ForEach-Object { $s = "$_"; if ($s -notmatch "symlink|Developer Mode|warnings.warn|UserWarning|HF_TOKEN|Fetching|Loading weights|use_return_dict") { Write-Host $s; Add-Content -Path $log -Value $s } }
  return $LASTEXITCODE
}
$repo = Join-Path $HOME "sahab-overnight"
$bundle = Join-Path $HOME "overnight.bundle"
$branch = "research/overnight-2026-09-30"
$venv = Join-Path $HOME "venvs\l47"
$py = Join-Path $venv "Scripts\python.exe"
$marker = Join-Path $HOME "l47_${Mode}.done"
Remove-Item -Force -ErrorAction SilentlyContinue $marker

if ($Mode -eq "install") {
  Say "L47 INSTALL started: Python 3.11 environment at ${venv} (lightgbm, pandas, numpy, scipy; CPU only)"
  if (-not (Test-Path $py)) { $null = Run "create the environment" "py" @("-3.11", "-m", "venv", $venv) }
  $null = Run "upgrade pip" $py @("-m", "pip", "install", "--upgrade", "pip", "--progress-bar", "off", "-q")
  $code = Run "install lightgbm pandas numpy scipy" $py @("-m", "pip", "install", "--progress-bar", "off", "-q", "lightgbm", "pandas", "numpy", "scipy")
  $null = Run "record the versions" $py @("-c", "import sys, platform, lightgbm, pandas, numpy, scipy; print('python', sys.version.split()[0], platform.machine(), '| lightgbm', lightgbm.__version__, '| pandas', pandas.__version__, '| numpy', numpy.__version__, '| scipy', scipy.__version__)")
  Say "L47 INSTALL finished (pip exit ${code})"
  Set-Content -Path $marker -Value "install exit ${code}"
  exit
}

if (-not (Test-Path $py)) { Say "L47 ${Mode} refused: no environment at ${venv}; run install first"; Set-Content -Path $marker -Value "refused: no venv"; exit 2 }
$l46 = @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*tsfm_family_ic*" })
if ($l46.Count -gt 0) {
  Say "L47 ${Mode} refused: an L46 model is running (pid $($l46[0].ProcessId)); decision D2b keeps L47 off the PC until L46 has finished"
  Set-Content -Path $marker -Value "refused: L46 running"
  exit 2
}
if (-not (Test-Path (Join-Path $HOME "l46_all.done"))) { Say "note: no l46_all.done marker, but no L46 process is running either" }

# Update the clone from the bundle. An untracked file the bundle now adds (a result written
# here and committed on the Mac) would block the fast-forward: it is moved aside first, then
# compared with the committed copy, and put back if the pull did not bring it.
$backup = Join-Path $HOME ("l47_backup\" + (Get-Date -Format "yyyyMMdd_HHmmss"))
$null = Run "fetch the bundle" "git" @("-C", $repo, "fetch", "-q", $bundle, $branch)
$incoming = @(& git -C $repo diff --name-only --diff-filter=A HEAD FETCH_HEAD)
$moved = @()
foreach ($f in $incoming) {
  if (-not $f) { continue }
  $p = Join-Path $repo $f
  if (Test-Path $p) {
    $st = (@(& git -C $repo status --porcelain -- $f) -join "")
    if ($st.StartsWith("??")) {
      $dest = Join-Path $backup $f
      New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
      Move-Item -Force $p $dest
      $moved += $f
      Say "moved the untracked ${f} aside, the bundle adds it (copy at ${dest})"
    }
  }
}
$pull = Run "update the overnight branch" "git" @("-C", $repo, "pull", "-q", "--ff-only", $bundle, $branch)
foreach ($f in $moved) {
  $p = Join-Path $repo $f
  $dest = Join-Path $backup $f
  if (-not (Test-Path $p)) { Move-Item -Force $dest $p; Say "restored ${f} (the pull did not bring it)" }
  elseif ((Get-FileHash $p).Hash -eq (Get-FileHash $dest).Hash) { Say "${f}: the committed copy is identical to this PC's" }
  else { Say "${f}: the committed copy DIFFERS from this PC's; this PC's copy is kept at ${dest}" }
}
$null = Run "branch head" "git" @("-C", $repo, "log", "--oneline", "-1")
if ($pull -ne 0) { Say "L47 ${Mode} refused: the clone did not fast-forward (git exit ${pull}); read the lines above"; Set-Content -Path $marker -Value "refused: pull failed"; exit 2 }

$env:PYTHONUNBUFFERED = "1"
$env:KRONOS_CANDLE_DB = Join-Path $HOME "kite_cache\kite_history.db"
$outs = @{ "stage0" = "l47_stage0.json"; "train" = "l47_frozen.json"; "score" = "l47_result.json" }
$out = Join-Path $repo ("docs\research\data\" + $outs[$Mode])
Say "=== L47 ${Mode} started (candle cache ${env:KRONOS_CANDLE_DB}) ==="
Push-Location (Join-Path $repo "backend")
$code = Run "L47 ${Mode}" $py @("-m", "research.qlib_alpha158_l47", $Mode)
Pop-Location
if (Test-Path $out) {
  $status = & $py -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('status', 'written'))" $out
  Say "L47 ${Mode} finished (exit ${code}); ${out} status ${status}"
} else {
  Say "L47 ${Mode} finished (exit ${code}); it wrote no ${out} - read the lines above"
}
Set-Content -Path $marker -Value "${Mode} exit ${code}"
