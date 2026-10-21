#!/usr/bin/env bash
# Shared helpers for the kube_*.sh scripts. Source this file; do not run it directly.
# Written for the macOS system bash (3.2): no mapfile, no associative arrays.

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

require_cmd() {
  local cmd
  for cmd in "$@"; do
    command -v "$cmd" >/dev/null 2>&1 || die "'$cmd' is not installed (see README.md for install steps)"
  done
}

# fuzzy_filter QUERY
# Reads candidate lines on stdin and prints the ones matching QUERY, best match first.
# Case-insensitive match, ranked:
#   1. exact match of the line's last field (the name)
#   2. QUERY is a substring of the name (earlier position and shorter line rank higher)
#   3. QUERY is a substring elsewhere in the line (for example the namespace)
#   4. QUERY's characters appear in order in the name, then in the line
#      (for example "encbf" matches "docdb-encryption-backfill-dry-run-x7k2p")
# QUERY may hold several space-separated terms, all of which must match
# (for example "staging email").
fuzzy_filter() {
  local query="$1"
  awk -v query="$query" '
    function subseq(hay, needle,   i, j, c) {
      j = 1
      for (i = 1; i <= length(hay) && j <= length(needle); i++) {
        c = substr(needle, j, 1)
        if (substr(hay, i, 1) == c) j++
      }
      return j > length(needle)
    }
    BEGIN { n = split(tolower(query), terms, /[ \t]+/) }
    {
      line = tolower($0)
      name = tolower($NF)
      score = 0
      for (t = 1; t <= n; t++) {
        term = terms[t]
        if (term == "") continue
        if (name == term) { score += 0; continue }
        pos = index(name, term)
        if (pos > 0) { score += 1000 + pos; continue }
        if (index(line, term) > 0) { score += 50000; continue }
        if (subseq(name, term)) { score += 100000; continue }
        if (subseq(line, term)) { score += 200000; continue }
        score = -1
        break
      }
      if (score >= 0) printf "%09d\t%06d\t%s\n", score, length($0), $0
    }
  ' | sort -t "$(printf '\t')" -k1,1n -k2,2n | cut -f3-
}

# pick_one PROMPT
# Reads candidate lines on stdin. With one line, prints it. With more, asks the user
# to choose (via fzf when installed, otherwise a numbered menu) and prints the choice.
pick_one() {
  local prompt="$1" candidates count choice
  candidates=$(cat)
  [ -n "$candidates" ] || return 1
  count=$(printf '%s\n' "$candidates" | wc -l | tr -d ' ')
  if [ "$count" -eq 1 ]; then
    printf '%s\n' "$candidates"
    return 0
  fi

  if command -v fzf >/dev/null 2>&1; then
    printf '%s\n' "$candidates" | fzf --height=40% --reverse --prompt="$prompt> " </dev/tty
    return $?
  fi

  printf '%s (%s matches):\n' "$prompt" "$count" >&2
  printf '%s\n' "$candidates" | awk '{ printf "  %3d) %s\n", NR, $0 }' >&2
  while :; do
    printf 'Select 1-%s (q to quit): ' "$count" >&2
    read -r choice </dev/tty || return 1
    case "$choice" in
      q|Q) return 1 ;;
      ''|*[!0-9]*) ;;
      *)
        if [ "$choice" -ge 1 ] && [ "$choice" -le "$count" ]; then
          printf '%s\n' "$candidates" | sed -n "${choice}p"
          return 0
        fi
        ;;
    esac
    printf 'Invalid selection.\n' >&2
  done
}

# resolve_context QUERY
# Prints the kubeconfig context matching QUERY (fuzzy). Exits on no match.
resolve_context() {
  local query="$1" contexts matches exact
  contexts=$(kubectl config get-contexts -o name)
  # An exact context or cluster name ("stag-eks" for "default/stag-eks") wins outright.
  exact=$(printf '%s\n' "$contexts" | awk -v q="$query" '$0 == q || substr($0, length($0) - length(q)) == "/" q' | head -1)
  if [ -n "$query" ] && [ -n "$exact" ]; then
    printf '%s\n' "$exact"
    return 0
  fi
  matches=$(printf '%s\n' "$contexts" | fuzzy_filter "$query")
  [ -n "$matches" ] || die "no kube context matches '$query' (run ./kubernetes/kube_setup.sh first?)"
  printf '%s\n' "$matches" | pick_one "context" || die "no context selected"
}
