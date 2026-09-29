# Kronos on the Windows PC — setup steps

For research look L40 (`prereg-kronos-feature-ic.md`) and what follows it. The PC is
faster than the Mac and has a GPU, so a pass that takes the Mac about 21 hours of
computing should take it an hour or two, and it can afford the pre-registration's
default of three samples a forecast. Research only: nothing on the PC touches the
engine, Kite or any order path.

**What the PC does and does not run.** The run of record for L40 is on the Mac
(amendment 3: CPU, one sample a forecast). The PC is for what comes after: a
replication at three samples if that is worth doing, and the confirmation and the
trial if the gate clears. Any of those gets its own dated note before it runs.

## Once

1. Install [Git for Windows](https://git-scm.com/download/win) and
   [Python 3.11](https://www.python.org/downloads/windows/). In the Python installer
   tick **Add python.exe to PATH**.
2. Open PowerShell and clone the repository (it is private; Git will ask you to sign
   in to GitHub the first time):

   ```powershell
   cd $HOME
   git clone https://github.com/harshece16/intraday-trading-agent.git
   cd intraday-trading-agent
   git checkout research/kronos-l40-run
   ```

3. Copy the candle cache from the Mac. It is not in the repository. On the Mac it is
   `~/Projects/webapp/backend/data/kite_history.db`, about 410 MB. AirDrop, a USB
   stick or a shared folder all work. Put it at `backend\data\kite_history.db` in
   the clone. Nothing else from the Mac is needed: no key, no session file.
4. Run the setup script. It creates `backend\research\.kvenv`, installs the pinned
   packages, installs the CUDA build of PyTorch if `nvidia-smi` finds an NVIDIA GPU,
   fetches the Kronos code at the pinned commit, and runs the harness's tests:

   ```powershell
   Set-ExecutionPolicy -Scope Process Bypass
   .\backend\research\kronos_pc_setup.ps1
   ```

   If the GPU is not NVIDIA, the script keeps the CPU build, which still runs; a
   desktop CPU with many cores is much faster than the Mac's four threads.

## Check the install: stage 0 on the PC

```powershell
cd backend
$env:KRONOS_DEVICE = 'cuda'      # leave this out to run on the CPU
research\.kvenv\Scripts\python.exe -m research.kronos_l40_launch stage0
```

About 25 minutes. The first run downloads the model weights (about 110 MB) from
Hugging Face. It runs the six pre-registered checks in order and writes
`docs\research\data\kronos_l40_stage0.json` in the clone. Do not commit that file;
send it over. Two of its numbers matter for the PC:

- **Timing:** seconds a forecast at three samples, and the hours the full pass would
  take. Under 36 hours means the PC can run at three samples.
- **Lookahead:** must be 20 of 20 identical. On a GPU this is the check that shows the
  device gives reproducible forecasts.

## What not to do

- Do not run the full pass (`start`) on the PC without a dated note in the
  pre-registration saying which run it is. The Mac's run is the one of record.
- Do not commit anything the run writes. The files are gitignored except the
  stage 0 and results JSON, which are committed from the Mac with the write-up.
- Do not put the dashboard key or the Kite session file on the PC. The PC reads the
  candle cache only.
