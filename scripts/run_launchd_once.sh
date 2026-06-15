#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CLI="$ROOT/.venv/bin/honsanam-reminder"

cd "$ROOT"

"$CLI" poll-replies || echo "poll-replies failed"
"$CLI" run-once
