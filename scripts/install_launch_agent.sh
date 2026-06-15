#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AGENT_DIR="$HOME/Library/LaunchAgents"
BASE_LABEL="com.hennei.honsanam-reminder-bot"
OLD_PLIST="$AGENT_DIR/$BASE_LABEL.plist"
REPLIES_LABEL="$BASE_LABEL.replies"
SENDER_LABEL="$BASE_LABEL.sender"
REPLIES_PLIST="$AGENT_DIR/$REPLIES_LABEL.plist"
SENDER_PLIST="$AGENT_DIR/$SENDER_LABEL.plist"

mkdir -p "$AGENT_DIR" "$ROOT/.local/logs"

cat > "$REPLIES_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$REPLIES_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$ROOT/.venv/bin/honsanam-reminder</string>
    <string>poll-replies</string>
    <string>--watch</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$ROOT</string>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$ROOT/.local/logs/replies.out</string>
  <key>StandardErrorPath</key>
  <string>$ROOT/.local/logs/replies.err</string>
</dict>
</plist>
PLIST

cat > "$SENDER_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$SENDER_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$ROOT/.venv/bin/honsanam-reminder</string>
    <string>run-once</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$ROOT</string>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Hour</key><integer>8</integer><key>Minute</key><integer>45</integer></dict>
    <dict><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>14</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>20</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>20</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Hour</key><integer>21</integer><key>Minute</key><integer>0</integer></dict>
  </array>
  <key>StandardOutPath</key>
  <string>$ROOT/.local/logs/sender.out</string>
  <key>StandardErrorPath</key>
  <string>$ROOT/.local/logs/sender.err</string>
</dict>
</plist>
PLIST

launchctl unload "$OLD_PLIST" 2>/dev/null || true
launchctl unload "$REPLIES_PLIST" 2>/dev/null || true
launchctl unload "$SENDER_PLIST" 2>/dev/null || true
rm -f "$OLD_PLIST"
launchctl load "$REPLIES_PLIST"
launchctl load "$SENDER_PLIST"
echo "installed $REPLIES_PLIST"
echo "installed $SENDER_PLIST"
