# Installs the Kronos research environment on this PC. Every line goes to the window and to kronos_pc.log.
$ErrorActionPreference = "Continue"
$Host.UI.RawUI.WindowTitle = "Kronos on this PC - install (this window stays open when done)"
$log = Join-Path $HOME "kronos_pc.log"
function Say($t) { $line = "{0} {1}" -f (Get-Date -Format "HH:mm:ss"), $t; Write-Host $line -ForegroundColor Cyan; Add-Content -Path $log -Value $line }
function Run($label, $exe, $argv) {
  Say ("> " + $label)
  & $exe @argv 2>&1 | ForEach-Object { $s = "$_"; Write-Host $s; Add-Content -Path $log -Value $s }
}
$root = Join-Path $HOME "intraday-trading-agent"
$backend = Join-Path $root "backend"
$venv = Join-Path $backend "research\.kvenv"
$py = Join-Path $venv "Scripts\python.exe"
$vendor = Join-Path $backend "research\kronos_vendor"
Say "INSTALL started. Machine: $env:COMPUTERNAME, user $env:USERNAME"
if (-not (Test-Path $py)) { Run "create the Python 3.11 environment at $venv" "py" @("-3.11", "-m", "venv", $venv) }
Run "upgrade pip" $py @("-m", "pip", "install", "--upgrade", "pip", "--progress-bar", "off")
Run "install PyTorch with CUDA 12.6 (about 2.5 GB; the longest step)" $py @("-m", "pip", "install", "torch", "--index-url", "https://download.pytorch.org/whl/cu126", "--progress-bar", "off")
Run "check torch sees the GPU" $py @("-c", "import torch; print('torch', torch.__version__, '| cuda:', torch.cuda.is_available(), '|', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no gpu')")
Run "install the project's packages and the pinned Kronos packages" $py @("-m", "pip", "install", "-r", (Join-Path $backend "requirements.txt"), "-r", (Join-Path $backend "research\requirements-kronos.txt"), "--progress-bar", "off")
Run "record the versions" $py @("-c", "import torch, pandas, numpy, einops, huggingface_hub, safetensors; print('torch', torch.__version__, 'pandas', pandas.__version__, 'numpy', numpy.__version__, 'einops', einops.__version__, 'hf', huggingface_hub.__version__, 'safetensors', safetensors.__version__)")
if (-not (Test-Path $vendor)) { Run "fetch the Kronos code" "git" @("clone", "https://github.com/shiyu-coder/Kronos", $vendor) }
Run "pin the Kronos code to commit 67b630e" "git" @("-C", $vendor, "checkout", "67b630e67f6a18c9e9be918d9b4337c960db1e9a")
Run "the pinned commit" "git" @("-C", $vendor, "log", "-1", "--format=%H %ad %s", "--date=short")
Push-Location $backend
Run "the harness's own tests (no model, no cache)" $py @("-m", "pytest", "-q", "tests\test_kronos_l40_launch.py", "tests\test_kronos_feature_ic.py", "tests\test_research_splits.py")
Pop-Location
Say "INSTALL finished. Next: stage 0 on the GPU, started from the Mac."
New-Item -ItemType File -Force -Path (Join-Path $HOME "kronos_install.done") | Out-Null
