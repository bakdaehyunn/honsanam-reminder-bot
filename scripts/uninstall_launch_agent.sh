#!/usr/bin/env bash
set -euo pipefail

AGENT_DIR="$HOME/Library/LaunchAgents"
BASE_LABEL="com.hennei.honsanam-reminder-bot"
PLISTS=(
  "$AGENT_DIR/$BASE_LABEL.plist"
  "$AGENT_DIR/$BASE_LABEL.replies.plist"
  "$AGENT_DIR/$BASE_LABEL.sender.plist"
)

for plist in "${PLISTS[@]}"; do
  launchctl unload "$plist" 2>/dev/null || true
  rm -f "$plist"
  echo "removed $plist"
done
