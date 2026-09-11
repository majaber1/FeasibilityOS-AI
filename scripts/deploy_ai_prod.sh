#!/usr/bin/env bash
# Deploy feasibilityos-ai using the Python serverless config.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
CFG="${ROOT}/vercel.ai.json"
if [[ ! -f "$CFG" ]]; then
  echo "Missing vercel.ai.json" >&2
  exit 1
fi
vercel deploy --prod --yes --project feasibilityos-ai --local-config "$CFG" "$@"
