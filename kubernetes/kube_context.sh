#!/usr/bin/env bash
# Switch kubectl context with a fuzzy name search (a minimal kubectx).
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
. "$SCRIPT_DIR/kube_lib.sh"

usage() {
  cat <<'EOF'
Usage: ./kubernetes/kube_context.sh [QUERY]

  QUERY  fuzzy context name, e.g. "stag-eks", "prod core". Omit to choose from all contexts.

Examples:
  ./kubernetes/kube_context.sh stag-eks     # exact cluster name wins over stag-eks-2
  ./kubernetes/kube_context.sh prodcore     # matches default/prod-core-be
EOF
}

case "${1:-}" in
  -h|--help) usage; exit 0 ;;
esac

require_cmd kubectl

context=$(resolve_context "${*:-}")
kubectl config use-context "$context"
