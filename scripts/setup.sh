#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV="$ROOT/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
DRY_RUN="${HONSANAM_SETUP_DRY_RUN:-0}"

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[dry-run]'
    for arg in "$@"; do
      printf ' %q' "$arg"
    done
    printf '\n'
  else
    "$@"
  fi
}

prompt_value() {
  local name="$1"
  local current="$2"
  local secret="${3:-0}"
  local value

  if [[ -n "$current" ]]; then
    if [[ "$secret" == "1" ]]; then
      printf '%s [configured]: ' "$name" >&2
    else
      printf '%s [%s]: ' "$name" "$current" >&2
    fi
  else
    printf '%s: ' "$name" >&2
  fi

  if [[ "$secret" == "1" ]]; then
    read -rs value
    printf '\n' >&2
  else
    read -r value
  fi

  if [[ -z "$value" ]]; then
    printf '%s' "$current"
  else
    printf '%s' "$value"
  fi
}

env_value() {
  local key="$1"
  local file="$2"
  if [[ -f "$file" ]]; then
    grep -E "^${key}=" "$file" | tail -n 1 | cut -d= -f2- || true
  fi
}

write_env() {
  local env_file="$1"
  local token="$2"
  local chat_id="$3"
  local timezone="$4"

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] write $env_file"
    return
  fi

  cat > "$env_file" <<ENV
TELEGRAM_BOT_TOKEN=$token
TELEGRAM_REMINDER_CHAT_ID=$chat_id
LIFE_REMINDER_TIMEZONE=$timezone
ENV
}

main() {
  cd "$ROOT"

  echo "==> Creating virtual environment"
  if [[ ! -d "$VENV" ]]; then
    run "$PYTHON_BIN" -m venv "$VENV"
  else
    echo "existing .venv found"
  fi

  echo "==> Installing honsanam-reminder"
  run "$VENV/bin/python" -m pip install -e "."

  echo "==> Creating default project files"
  run "$VENV/bin/honsanam-reminder" init

  local env_file="$ROOT/.env"
  local current_token current_chat_id current_timezone
  current_token="$(env_value TELEGRAM_BOT_TOKEN "$env_file")"
  current_chat_id="$(env_value TELEGRAM_REMINDER_CHAT_ID "$env_file")"
  current_timezone="$(env_value LIFE_REMINDER_TIMEZONE "$env_file")"
  current_timezone="${current_timezone:-Asia/Seoul}"

  echo "==> Telegram configuration"
  local token chat_id timezone auto_discover discovered
  token="$(prompt_value "Telegram bot token" "$current_token" 1)"
  timezone="$(prompt_value "Timezone" "$current_timezone")"
  if [[ -n "$current_chat_id" ]]; then
    chat_id="$(prompt_value "Telegram reminder chat id" "$current_chat_id" 1)"
  else
    chat_id=""
    echo "Telegram chat id can be found automatically after the bot receives one message."
    printf 'Try chat id auto discovery? [Y/n]: ' >&2
    read -r auto_discover
    if [[ ! "$auto_discover" =~ ^[Nn]$ ]]; then
      write_env "$env_file" "$token" "" "$timezone"
      echo "Send any message to your Telegram bot, then press Enter here." >&2
      read -r _
      if [[ "$DRY_RUN" == "1" ]]; then
        run "$VENV/bin/honsanam-reminder" discover-chat --plain
      elif discovered="$("$VENV/bin/honsanam-reminder" discover-chat --plain 2>/dev/null)"; then
        chat_id="$discovered"
        echo "found Telegram reminder chat id"
      else
        echo "could not find chat id automatically"
      fi
    fi
    if [[ -z "$chat_id" ]]; then
      chat_id="$(prompt_value "Telegram reminder chat id" "$current_chat_id" 1)"
    fi
  fi
  write_env "$env_file" "$token" "$chat_id" "$timezone"

  echo "==> Checking configuration"
  run "$VENV/bin/honsanam-reminder" doctor || true

  echo "==> Upcoming reminders"
  run "$VENV/bin/honsanam-reminder" next --days 14 || true

  local install_launchd
  printf 'Install macOS automatic launchd schedule? [y/N]: ' >&2
  read -r install_launchd
  if [[ "$install_launchd" =~ ^[Yy]$ ]]; then
    run "$ROOT/scripts/install_launch_agent.sh"
  else
    echo "skipped launchd install"
  fi

  echo "setup complete"
}

main "$@"
