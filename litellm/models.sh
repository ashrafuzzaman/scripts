#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
MODELS_URL='https://litellm.prod.aws.lifelock.com/models?return_wildcard_routes=false&include_model_access_groups=false&only_model_access_groups=false&include_metadata=false'
PYTHON=${PYTHON:-python3}

if [ -z "${LITELLM_API_KEY:-}" ]; then
  printf 'error: LITELLM_API_KEY is required\n' >&2
  exit 2
fi
case "$LITELLM_API_KEY" in
  *$'\n'*|*$'\r'*)
    printf 'error: LITELLM_API_KEY must not contain a newline\n' >&2
    exit 2
    ;;
esac
for command_name in curl "$PYTHON"; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf "error: '%s' is required\n" "$command_name" >&2
    exit 1
  fi
done
if ! command -v ctp >/dev/null 2>&1; then
  printf 'error: ctp is required; run %s/setup.sh\n' "$SCRIPT_DIR" >&2
  exit 1
fi

CACHE_ROOT=${XDG_CACHE_HOME:-"$HOME/.cache"}
CACHE_DIR="$CACHE_ROOT/litellm-model-list"
MODELS_CACHE="$CACHE_DIR/models.json"
ETAG_CACHE="$CACHE_DIR/models.etag"
mkdir -p "$CACHE_DIR"
chmod 700 "$CACHE_DIR"
[ -f "$ETAG_CACHE" ] || : > "$ETAG_CACHE"
chmod 600 "$ETAG_CACHE"
if [ -f "$MODELS_CACHE" ]; then
  chmod 600 "$MODELS_CACHE"
fi

request_headers=$(mktemp "${TMPDIR:-/tmp}/litellm-headers.XXXXXX")
response_body=$(mktemp "$CACHE_DIR/models.XXXXXX")
cleanup() {
  rm -f "$request_headers" "$response_body"
}
trap cleanup EXIT HUP INT TERM
chmod 600 "$request_headers" "$response_body"
printf 'accept: application/json\nx-litellm-api-key: %s\n' "$LITELLM_API_KEY" > "$request_headers"

if http_status=$(curl --location --silent --show-error --max-time 30 \
  --header "@$request_headers" \
  --etag-compare "$ETAG_CACHE" \
  --etag-save "$ETAG_CACHE" \
  --output "$response_body" \
  --write-out '%{http_code}' \
  "$MODELS_URL"); then
  case "$http_status" in
    200)
      if ! "$PYTHON" -m json.tool "$response_body" >/dev/null; then
        printf 'error: LiteLLM returned invalid JSON\n' >&2
        exit 1
      fi
      mv "$response_body" "$MODELS_CACHE"
      chmod 600 "$MODELS_CACHE"
      ;;
    304)
      if [ ! -s "$MODELS_CACHE" ]; then
        printf 'error: LiteLLM returned HTTP 304 but there is no cached model response\n' >&2
        exit 1
      fi
      ;;
    *)
      printf 'error: LiteLLM returned HTTP %s\n' "$http_status" >&2
      exit 1
      ;;
  esac
else
  if [ -s "$MODELS_CACHE" ]; then
    printf 'warning: LiteLLM request failed; using the cached model response\n' >&2
  else
    printf 'error: LiteLLM request failed and no cached response is available\n' >&2
    exit 1
  fi
fi

"$PYTHON" "$SCRIPT_DIR/list_models.py" \
  --models-file "$MODELS_CACHE" \
  --cache-dir "$CACHE_DIR"
