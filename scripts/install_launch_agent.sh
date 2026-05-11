#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/hennei/workspace/honsanam-reminder-bot"
PLIST="$HOME/Library/LaunchAgents/com.hennei.honsanam-reminder-bot.plist"

mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/.local/logs"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.hennei.honsanam-reminder-bot</string>
  <key>ProgramArguments</key>
  <array>
    <string>$ROOT/.venv/bin/honsanam-reminder</string>
    <string>run-once</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$ROOT</string>
  <key>StartInterval</key>
  <integer>300</integer>
  <key>StandardOutPath</key>
  <string>$ROOT/.local/logs/launchd.out</string>
  <key>StandardErrorPath</key>
  <string>$ROOT/.local/logs/launchd.err</string>
</dict>
</plist>
PLIST

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "installed $PLIST"
