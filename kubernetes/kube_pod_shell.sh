#!/usr/bin/env bash
# Open a shell (or run a command) in a pod found by fuzzy name search.
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
. "$SCRIPT_DIR/kube_lib.sh"

usage() {
  cat <<'EOF'
Usage: ./kubernetes/kube_pod_shell.sh [-x CONTEXT] [-n NAMESPACE] [-c CONTAINER] [-a] QUERY [-- COMMAND...]

  QUERY         fuzzy pod name; several space-separated terms must all match
                (e.g. "email-api", "encbf", "staging email")
  -x CONTEXT    fuzzy kube context to use (default: current context)
  -n NAMESPACE  only search this namespace (default: all namespaces)
  -c CONTAINER  container to exec into (default: the pod's default container)
  -a            include pods that are not Running (Pending, Succeeded, Failed)
  -- COMMAND    run COMMAND instead of an interactive shell (bash, falling back to sh)
  -h            show this help

With more than one match you get a picker (fzf when installed, otherwise a numbered menu).

Examples:
  ./kubernetes/kube_pod_shell.sh email-api
  ./kubernetes/kube_pod_shell.sh -x stag-eks -n staging encryption backfill
  ./kubernetes/kube_pod_shell.sh email-api -- printenv SPRING_PROFILES_ACTIVE
EOF
}

context_query=""
namespace=""
container=""
include_all=false

while getopts ":x:n:c:ah" opt; do
  case "$opt" in
    x) context_query="$OPTARG" ;;
    n) namespace="$OPTARG" ;;
    c) container="$OPTARG" ;;
    a) include_all=true ;;
    h) usage; exit 0 ;;
    :) die "-$OPTARG needs a value" ;;
    *) usage >&2; exit 2 ;;
  esac
done
shift $((OPTIND - 1))

# Everything before "--" is the query; everything after is the command.
query=""
while [ $# -gt 0 ] && [ "$1" != "--" ]; do
  query="${query:+$query }$1"
  shift
done
[ "${1:-}" = "--" ] && shift

[ -n "$query" ] || { usage >&2; exit 2; }

require_cmd kubectl

kube=(kubectl)
if [ -n "$context_query" ]; then
  current_context=$(resolve_context "$context_query")
  kube+=(--context "$current_context")
else
  current_context=$(kubectl config current-context 2>/dev/null) \
    || die "no kube context set; run ./kubernetes/kube_setup.sh or ./kubernetes/kube_context.sh first (or pass -x)"
fi

if [ -n "$namespace" ]; then
  scope=(-n "$namespace")
else
  scope=(--all-namespaces)
fi

pods=$("${kube[@]}" get pods "${scope[@]}" --no-headers \
  -o custom-columns='NS:.metadata.namespace,STATUS:.status.phase,NAME:.metadata.name') \
  || die "could not list pods in context '$current_context'. If that was Forbidden, your AWS role has no k8s RBAC: re-run ./kubernetes/kube_setup.sh -p <profile> with a profile for the staging-k8s-developer / production-k8s-developer role (ITSD ticket if you have none)"

if [ "$include_all" = false ]; then
  pods=$(printf '%s\n' "$pods" | awk '$2 == "Running"')
fi

matches=$(printf '%s\n' "$pods" | awk 'NF { printf "%-28s %-10s %s\n", $1, $2, $3 }' | fuzzy_filter "$query")
if [ -z "$matches" ]; then
  hint=""
  [ "$include_all" = false ] && hint=" (only Running pods searched; use -a to include others)"
  die "no pod in context '$current_context' matches '$query'$hint"
fi

selected=$(printf '%s\n' "$matches" | pick_one "pod") || die "no pod selected"
pod_ns=$(printf '%s\n' "$selected" | awk '{print $1}')
pod_name=$(printf '%s\n' "$selected" | awk '{print $NF}')
pod_status=$(printf '%s\n' "$selected" | awk '{print $2}')

if [ "$pod_status" != "Running" ]; then
  die "pod $pod_ns/$pod_name is $pod_status, so there is no running container to exec into. Read its output with: ${kube[*]} logs -n $pod_ns $pod_name${container:+ -c $container}"
fi

exec_args=(exec -it -n "$pod_ns" "$pod_name")
[ -n "$container" ] && exec_args+=(-c "$container")

if [ $# -gt 0 ]; then
  printf 'Running in %s/%s (%s): %s\n' "$pod_ns" "$pod_name" "$current_context" "$*" >&2
  exec "${kube[@]}" "${exec_args[@]}" -- "$@"
fi

printf 'Opening shell in %s/%s (%s)\n' "$pod_ns" "$pod_name" "$current_context" >&2
exec "${kube[@]}" "${exec_args[@]}" -- sh -c 'if command -v bash >/dev/null 2>&1; then exec bash; else exec sh; fi'
