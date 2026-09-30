param([int]$N = 12, [string]$Task = "")
if ($Task) { schtasks /query /tn $Task /fo list 2>$null | Select-String "Status" | ForEach-Object { $_.Line.Trim() } }
Select-String -Path "$HOME\kronos_pc.log" -Pattern "cuda:" | Select-Object -Last 1 | ForEach-Object { "gpu line: " + $_.Line }
"--- log tail:"
Get-Content "$HOME\kronos_pc.log" -Tail $N
