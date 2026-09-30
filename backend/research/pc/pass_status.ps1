# What the pass is doing right now: forecasts written, the latest ones, and the GPU's state.
$rows = Join-Path $HOME "intraday-trading-agent\backend\research\kronos_rows_l40.jsonl"
$total = 43362
if (Test-Path $rows) {
  $n = 0; $last = @()
  $fs = [System.IO.File]::Open($rows, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite); $sr = New-Object System.IO.StreamReader($fs)
  while (($line = $sr.ReadLine()) -ne $null) { $n++; $last += $line; if ($last.Count -gt 4) { $last = $last[1..4] } }
  $sr.Close(); $fs.Close()
  "forecasts written: {0} of {1}  ({2:N1}%)" -f $n, $total, ($n * 100 / $total)
  "the latest forecasts (one stock at one decision time: the last 512 five-minute bars go in, 12 bars come out). What happened next is not shown: nothing is compared with a return until every forecast is done."
  foreach ($l in $last) {
    $r = $l | ConvertFrom-Json
    "  {0}  {1}  {2,-11}  last close {3,9:N2}  Kronos says the next 15 / 30 / 60 min: {4,7:N1} / {5,7:N1} / {6,7:N1} bp" -f $r.date, $r.hhmm, $r.sym, $r.c0, $r.features.f15, $r.features.f30, $r.features.f60
  }
} else {
  "forecasts written: none yet - stage 0 is repeating first (regression test, revisions, lookahead, timing), about two minutes on this PC"
}
$q = (& nvidia-smi --query-gpu=temperature.gpu,fan.speed,power.draw,utilization.gpu --format=csv,noheader,nounits) -split ","
"gpu now: {0} C, fan {1}%, {2} W, busy {3}%" -f $q[0].Trim(), $q[1].Trim(), $q[2].Trim(), $q[3].Trim()
