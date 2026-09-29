# Sets up the Kronos research environment on a Windows PC, for research look L40
# and its follow-ups (docs/research/kronos-pc-setup.md). Research only: nothing here
# touches the engine, Kite, or any order path.
#
# Run from the repository root in PowerShell:
#     Set-ExecutionPolicy -Scope Process Bypass
#     .\backend\research\kronos_pc_setup.ps1
#
# Before running it: git and Python 3.11 installed; backend\data\kite_history.db
# copied from the Mac (it is not in the repository).
$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..\..").Path
$backend = Join-Path $root "backend"
$venv = Join-Path $backend "research\.kvenv"
$vendor = Join-Path $backend "research\kronos_vendor"
$db = Join-Path $backend "data\kite_history.db"
$pinned = "67b630e67f6a18c9e9be918d9b4337c960db1e9a"

if (-not (Test-Path $db)) { throw "Copy the candle cache from the Mac to $db first (backend/data/kite_history.db, about 410 MB)." }

Write-Host "1. Python environment at $venv"
if (-not (Test-Path $venv)) { py -3.11 -m venv $venv }
$py = Join-Path $venv "Scripts\python.exe"
& $py -m pip install --quiet --upgrade pip
& $py -m pip install --quiet -r (Join-Path $backend "requirements.txt") -r (Join-Path $backend "research\requirements-kronos.txt")

Write-Host "2. PyTorch with CUDA, if an NVIDIA GPU is present"
$gpu = $false
try { $null = & nvidia-smi 2>$null; $gpu = ($LASTEXITCODE -eq 0) } catch { $gpu = $false }
if ($gpu) {
    & $py -m pip install --quiet --force-reinstall torch --index-url https://download.pytorch.org/whl/cu126
} else {
    Write-Host "   nvidia-smi not found: keeping the CPU build of torch"
}
& $py -c "import torch; print('   torch', torch.__version__, '| cuda available:', torch.cuda.is_available(), '| threads', torch.get_num_threads())"

Write-Host "3. Kronos code at the pinned commit, $vendor"
if (-not (Test-Path $vendor)) { git clone --quiet https://github.com/shiyu-coder/Kronos $vendor }
git -C $vendor checkout --quiet $pinned
git -C $vendor log -1 --format="   %H %ad" --date=short

Write-Host "4. The harness's own tests (no model, no cache)"
Push-Location $backend
& $py -m pytest -q tests\test_kronos_l40_launch.py tests\test_kronos_feature_ic.py
Pop-Location

Write-Host ""
Write-Host "Ready. Stage 0 on this machine (about 25 minutes; downloads the model weights on first use):"
Write-Host "    cd $backend"
if ($gpu) { Write-Host "    `$env:KRONOS_DEVICE = 'cuda'" }
Write-Host "    research\.kvenv\Scripts\python.exe -m research.kronos_l40_launch stage0"
Write-Host "It writes docs\research\data\kronos_l40_stage0.json in this clone. Do not commit that file; send it over."
