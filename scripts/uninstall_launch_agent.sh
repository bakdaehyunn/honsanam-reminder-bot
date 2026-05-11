#!/usr/bin/env bash
set -euo pipefail

PLIST="$HOME/Library/LaunchAgents/com.hennei.honsanam-reminder-bot.plist"

launchctl unload "$PLIST" 2>/dev/null || true
rm -f "$PLIST"
echo "removed $PLIST"
