#!/usr/bin/env bash
set -euo pipefail

if ! command -v npm >/dev/null 2>&1; then
  printf 'error: npm is required to install ctp\n' >&2
  exit 1
fi

npm install --global table-printer-cli
