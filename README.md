# 혼사남 알림봇

혼사남 알림봇은 혼자 사는 남자를 위한 생활 루틴 알림 프로젝트입니다.

미용실 예약, 손톱과 발톱 정리, 집 청소, 분리수거, 이불 빨래처럼 반복적으로 신경 써야 하는 일을 정해진 시간에 알려 줍니다. 자주 필요한 생활 루틴은 기본 항목으로 제공되며, 각 항목은 원하는 주기와 시간에 맞게 설정할 수 있습니다.

macOS 자동 실행이 정해진 시간마다 CLI를 실행해 루틴을 확인하고, 보낼 알림이 있으면 텔레그램 알림봇으로 메시지를 전송합니다. 필요한 루틴은 CLI로 추가하거나 수정할 수 있고, Codex skill은 AI 에이전트가 이 CLI를 쉽게 활용할 수 있도록 돕습니다.

기본 일정은 한 번에 몰리지 않도록 나누어 배치했습니다. 귀찮아서 미루지 않게, 한 번에 하나씩 처리하는 흐름을 기준으로 합니다.

## 기본 생활 루틴

| ID | 알림 | 기본 일정 |
| --- | --- | --- |
| `haircut` | 미용실 예약 | 월 1회 기준, 월요일 08:45 |
| `fingernails` | 손톱 관리 | 7일 주기, 수요일 21:00 |
| `toenails` | 발톱 관리 | 21일 주기, 수요일 21:00 |
| `nose-hair` | 코털 정리 | 14일 주기, 금요일 20:30 |
| `earwax` | 귀지 정리 | 21일 주기, 월요일 21:00 |
| `trash` | 분리수거 | 화/목/일 20:00 |
| `mac-status` | 맥북 상태점검 | 토요일 10:00 |
| `weekend-cleaning` | 주말 청소 | 토요일 14:00 |
| `bathroom-cleaning` | 화장실 청소 | 14일 주기, 일요일 10:30 |
| `bedding-wash` | 이불 빨래 | 14일 주기, 다른 일요일 14:00 |

## 설치

### Telegram Bot 준비

1. Telegram에서 `@BotFather`에게 새 bot을 만들고 bot token을 받습니다.
2. 알림을 받을 개인 채팅이나 그룹에 bot을 추가합니다.
3. 해당 채팅방에서 bot에게 아무 메시지나 한 번 보냅니다.
4. `honsanam-reminder setup` 실행 중 chat id 자동 탐색을 선택하면 최근 메시지에서 chat id를 찾고, 표시된 채팅방이 맞는지 확인한 뒤 `.env`에 저장합니다.

빠른 설치는 `setup.sh`를 사용합니다.

```bash
git clone https://github.com/bakdaehyunn/honsanam-reminder-bot.git
cd honsanam-reminder-bot
scripts/setup.sh
```

`scripts/setup.sh`는 `.venv`를 만들고 패키지를 설치한 뒤 `honsanam-reminder setup`을 실행합니다. 설치 과정에서 Telegram bot token, timezone을 입력합니다. chat id는 자동으로 찾을 수 있고, 자동 탐색이 실패하거나 확인을 거절하면 직접 입력하면 됩니다. 설정 후 `doctor` 점검이 실패하면 setup은 완료로 처리하지 않습니다. 마지막에 macOS 자동 실행을 설치할지 선택할 수 있습니다.

이미 설치된 환경에서 다시 설정하려면 아래 명령을 사용합니다.

```bash
honsanam-reminder setup
```

이미 설치된 환경에서는 아래처럼 직접 확인할 수 있습니다.

```bash
.venv/bin/honsanam-reminder doctor
.venv/bin/honsanam-reminder next --days 14
.venv/bin/honsanam-reminder send-test
```

`setup` 중에는 실제 Telegram 테스트 메시지를 보내지 않습니다. readiness checklist가 나온 뒤 `honsanam-reminder send-test`를 직접 실행하면 한 번의 테스트 메시지를 보낼 수 있습니다.

## 기본 명령어

```bash
honsanam-reminder init
honsanam-reminder setup
honsanam-reminder doctor
honsanam-reminder discover-chat
honsanam-reminder preview --date 2026-06-01 --time 08:45
honsanam-reminder next --days 14
honsanam-reminder run-once --dry-run
honsanam-reminder poll-replies
honsanam-reminder poll-replies --watch
honsanam-reminder pending
honsanam-reminder interactions
honsanam-reminder answer haircut-booking-2026-06-07 yes
honsanam-reminder run-once
honsanam-reminder send-test
```

## 알림 관리

일상적인 알림 변경은 `.local/config/*.json` 파일을 직접 수정하기보다 CLI로 관리합니다.

```bash
honsanam-reminder list
honsanam-reminder show trash
honsanam-reminder next --days 14
honsanam-reminder disable trash
honsanam-reminder enable trash
honsanam-reminder add custom --id water-plants --title "화분 물주기" --kind weekly --weekday sat --time 09:00 --action "화분 물주기"
honsanam-reminder update water-plants --time 09:30 --note "거실 먼저 확인"
honsanam-reminder remove water-plants
honsanam-reminder pattern show
honsanam-reminder pattern set --prefix "생활알림" --schedule-label "언제" --action-label "해야 할 일" --note-label "관리 포인트"
honsanam-reminder validate
```

기본 생활 루틴은 켜기, 끄기, 일정 수정이 가능하며, 필요한 루틴은 커스텀 알림으로 추가해 관리할 수 있습니다.

## 확인 알림과 반응 버튼

미용실 예약처럼 실제로 했는지 확인이 필요한 알림은 Telegram 메시지에 `예약했음` / `아직` 버튼이 함께 전송됩니다.

`예약했음`을 누르면 해당 미용실 예약 주기는 완료 처리되고, 더 이상 같은 예약 건을 묻지 않습니다. `아직`을 누르거나 답하지 않으면 대기 상태로 남고, 7일 뒤 같은 요일과 시간에 다시 물어봅니다.

수동으로 확인 상태를 보거나 처리할 수도 있습니다.

```bash
honsanam-reminder pending
honsanam-reminder answer haircut-booking-2026-06-07 yes
honsanam-reminder answer haircut-booking-2026-06-07 no
honsanam-reminder poll-replies
```

그 외 일반 생활 루틴에도 가벼운 반응 버튼이 붙습니다. 예를 들어 분리수거는 `내놨음` / `나중에`, 맥북 상태점검은 `확인했음`처럼 표시됩니다. 이 반응은 재알림을 만들지 않고, 나중에 통계로 볼 수 있도록 `.local/state/interactions.json`에만 기록합니다.

```bash
honsanam-reminder interactions
honsanam-reminder interactions --json
```

## AI 에이전트용 skill

AI 에이전트가 CLI 명령어를 안정적으로 사용할 수 있도록 `skills/honsanam-reminder`에 Codex skill을 제공합니다.

이 skill은 초기 설정, 상태 점검, 미리보기, 알림 발송, 기본 알림 관리, 커스텀 알림 추가와 수정, 메시지 패턴 변경, 설정 검증에 필요한 CLI 사용 기준을 담고 있습니다.

## launchd

```bash
scripts/install_launch_agent.sh
scripts/uninstall_launch_agent.sh
```

LaunchAgent는 두 개로 나누어 설치됩니다.

- `com.hennei.honsanam-reminder-bot.replies`: `honsanam-reminder poll-replies --watch`를 계속 실행하며 Telegram 버튼 응답을 long polling으로 처리합니다.
- `com.hennei.honsanam-reminder-bot.sender`: `honsanam-reminder run-once`를 5분마다 실행해 보낼 알림이 있는지 확인합니다.

알림은 정해진 시간 근처에만 전송됩니다. sender가 5분마다 확인하므로 기본 알림 시간을 바꾸거나 커스텀 알림을 추가해도 launchd 일정을 따로 수정할 필요가 없습니다. Telegram 버튼 응답은 replies watcher가 계속 처리합니다.

중복 알림 발송은 `.local/state/sent.json` 파일로 방지하고, 확인 알림 상태는 `.local/state/confirmations.json`, 일반 반응 기록은 `.local/state/interactions.json` 파일로 관리합니다. `scripts/run_launchd_once.sh`는 수동 점검용으로 남겨 두지만, 일반 launchd 설치 흐름에서는 사용하지 않습니다.
