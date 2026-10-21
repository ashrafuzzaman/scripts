#!/usr/bin/env bash
# Pull kubeconfig contexts for every EKS cluster visible to an AWS profile.
# Non-interactive version of the gist in Confluence "HOW-TO: Setup kubectl on your local
# dev machine" (IN2/3535536293). Contexts are named "<profile>/<cluster>", same as the gist.
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
. "$SCRIPT_DIR/kube_lib.sh"

usage() {
  cat <<'EOF'
Usage: ./kubernetes/kube_setup.sh [-p PROFILE] [-r REGION] [-k KUBECONFIG] [-c CONTEXT_QUERY]

  -p PROFILE        AWS profile with EKS access (default: $AWS_PROFILE or "default")
  -r REGION         AWS region (default: $AWS_REGION or us-east-1)
  -k KUBECONFIG     kubeconfig file to write (default: $KUBECONFIG or ~/.kube/config)
  -c CONTEXT_QUERY  after setup, switch to the context fuzzy-matching this (e.g. "stag-eks")
  -h                show this help

Per the doc, use the staging-k8s-developer / production-k8s-developer SSO roles for
read access to MoneyLion clusters. Raise an ITSD ticket if you have no EKS access.
EOF
}

profile="${AWS_PROFILE:-default}"
region="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
kubeconfig="${KUBECONFIG:-$HOME/.kube/config}"
context_query=""

while getopts ":p:r:k:c:h" opt; do
  case "$opt" in
    p) profile="$OPTARG" ;;
    r) region="$OPTARG" ;;
    k) kubeconfig="$OPTARG" ;;
    c) context_query="$OPTARG" ;;
    h) usage; exit 0 ;;
    :) die "-$OPTARG needs a value" ;;
    *) usage >&2; exit 2 ;;
  esac
done

require_cmd aws kubectl

printf 'kubectl %s | %s\n' \
  "$(kubectl version --client 2>/dev/null | awk '/Client Version/{print $3}')" \
  "$(aws --version 2>&1)"

if ! identity=$(aws sts get-caller-identity --profile "$profile" --query Arn --output text 2>&1); then
  printf '%s\n' "$identity" >&2
  die "AWS profile '$profile' has no valid session. Log in (Leapp, or 'aws sso login --profile $profile') and retry."
fi
printf 'AWS identity: %s\n' "$identity"

clusters=$(aws eks list-clusters --profile "$profile" --region "$region" \
  --query 'clusters[]' --output text | tr '\t' '\n' | grep -v -e '^$' -e '^None$' | sort || true)
[ -n "$clusters" ] || die "no EKS clusters visible to profile '$profile' in $region"

mkdir -p "$(dirname "$kubeconfig")"
for cluster in $clusters; do
  aws eks update-kubeconfig \
    --profile "$profile" \
    --region "$region" \
    --kubeconfig "$kubeconfig" \
    --alias "$profile/$cluster" \
    --name "$cluster"
done

if [ -n "$context_query" ]; then
  context=$(KUBECONFIG="$kubeconfig" resolve_context "$context_query")
  KUBECONFIG="$kubeconfig" kubectl config use-context "$context"
else
  printf "Run './kubernetes/kube_context.sh <query>' or 'kubectl config use-context <name>' to pick a context.\n"
fi
