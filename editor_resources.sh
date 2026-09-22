#!/usr/bin/env bash
# Compare total CPU and memory usage of Zed vs VS Code processes (all helpers included).
set -euo pipefail

ZED_PATTERN='Zed\.app|(^|/)zed( |$)'
CODE_PATTERN='Visual Studio Code\.app|Code Helper'

sum_resources() {
  local pattern="$1"
  ps -axo pid,%cpu,%mem,rss,command \
    | awk -v pattern="$pattern" '
        NR > 1 && $0 !~ /grep|editor_resources\.sh/ && tolower($0) ~ tolower(pattern) {
          cpu += $2; mem += $3; rss += $4; count++
        }
        END { printf "%d %.1f %.1f %.1f\n", count, cpu, mem, rss / 1024 }
      '
}

print_row() {
  local name="$1" stats="$2"
  read -r count cpu mem rss_mb <<< "$stats"
  printf "%-14s %8s %10s%% %10s%% %12s MB\n" "$name" "$count" "$cpu" "$mem" "$rss_mb"
}

zed_stats=$(sum_resources "$ZED_PATTERN")
code_stats=$(sum_resources "$CODE_PATTERN")

# Default to zero if no matching processes found (empty awk output).
zed_stats=${zed_stats:-"0 0.0 0.0 0.0"}
code_stats=${code_stats:-"0 0.0 0.0 0.0"}

echo "Editor resource usage (sum across all processes/helpers) - $(date '+%Y-%m-%d %H:%M:%S')"
echo "-----------------------------------------------------------------------------"
printf "%-14s %8s %11s %11s %15s\n" "Editor" "Procs" "CPU" "Memory" "RSS"
print_row "Zed" "$zed_stats"
print_row "VS Code" "$code_stats"
echo "-----------------------------------------------------------------------------"
echo "Note: CPU% is summed across all matching processes (100% = one core, per 'ps')."
echo "      Memory% is summed %MEM as reported by 'ps'; RSS is summed resident memory."
