# Writes the GPU's temperature, fan, power and clock to the live log every two minutes while the pass runs.
# If the card sits at or above 83 C for two readings in a row, the power cap is lowered to 180 W and that is logged.
$log = Join-Path $HOME "kronos_pc.log"
$hot = 0; $capped = $false
while (-not (Test-Path (Join-Path $HOME "kronos_pass.done"))) {
  $q = (& nvidia-smi --query-gpu=temperature.gpu,fan.speed,power.draw,clocks.sm,utilization.gpu --format=csv,noheader,nounits) -split ","
  $temp = [int]$q[0].Trim()
  $line = "{0} gpu {1} C | fan {2}% | {3} W | {4} MHz | busy {5}%" -f (Get-Date -Format "HH:mm:ss"), $temp, $q[1].Trim(), $q[2].Trim(), $q[3].Trim(), $q[4].Trim()
  if ($temp -ge 83) { $hot++ } else { $hot = 0 }
  if ($hot -ge 2 -and -not $capped) {
    & nvidia-smi -pl 180 | Out-Null
    $capped = $true
    $line += " | HOT: power cap lowered to 180 W"
  }
  Add-Content -Path $log -Value $line
  Start-Sleep 120
}
if ($capped) { & nvidia-smi -pl 220 | Out-Null; Add-Content -Path $log -Value ("{0} power cap restored to 220 W" -f (Get-Date -Format "HH:mm:ss")) }
