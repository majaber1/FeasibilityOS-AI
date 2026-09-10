#!/usr/bin/env bash
# Deploy saudi-business-web without the root Python vercel.ai.json interfering.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# Guard: never deploy web while a Python builds vercel.json sits at repo root.
if [[ -f vercel.json ]] && grep -q '@vercel/python' vercel.json; then
  echo "ERROR: root vercel.json is the AI Python config. Move it aside (vercel.ai.json) before web deploy." >&2
  exit 1
fi
# Deploy from monorepo root so Vercel Root Directory (apps/web) applies.
vercel deploy --prod --yes --project saudi-business-web "$@"
