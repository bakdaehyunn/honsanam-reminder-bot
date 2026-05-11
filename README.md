# 혼사남 알림봇

혼사남 알림봇은 혼자 사는 남자를 위한 생활 루틴 알림 프로젝트입니다.

미용실 예약, 손톱과 발톱 정리, 집 청소, 분리수거, 이불 빨래처럼 반복적으로 신경 써야 하는 일을 정해진 시간에 알려 줍니다. 자주 필요한 생활 루틴은 기본 항목으로 제공되며, 각 항목은 원하는 주기와 시간에 맞게 설정할 수 있습니다.

macOS 자동 실행이 정해진 시간마다 CLI를 실행해 루틴을 확인하고, 보낼 알림이 있으면 텔레그램 알림봇으로 메시지를 전송합니다. 필요한 루틴은 CLI로 추가하거나 수정할 수 있고, Codex skill은 AI 에이전트가 이 CLI를 쉽게 활용할 수 있도록 돕습니다.

## 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
honsanam-reminder init
honsanam-reminder doctor
honsanam-reminder send-test
```

## 기본 명령어

```bash
honsanam-reminder init
honsanam-reminder doctor
honsanam-reminder preview --date 2026-06-01 --time 08:45
honsanam-reminder run-once --dry-run
honsanam-reminder run-once
honsanam-reminder send-test
```

## 알림 관리

일상적인 알림 변경은 `.local/config/*.json` 파일을 직접 수정하기보다 CLI로 관리합니다.

```bash
honsanam-reminder list
honsanam-reminder show trash
honsanam-reminder disable trash
honsanam-reminder enable trash
honsanam-reminder add custom --id water-plants --title "화분 물주기" --kind weekly --weekday sat --time 09:00 --action "화분 물주기"
honsanam-reminder update water-plants --time 09:30 --note "거실 먼저 확인"
honsanam-reminder remove water-plants
honsanam-reminder pattern show
honsanam-reminder pattern set --prefix "생활알림" --schedule-label "언제" --action-label "해야 할 일" --note-label "확인할 점"
honsanam-reminder validate
```

기본 알림은 켜기, 끄기, 수정이 가능합니다. 삭제는 사용자가 추가한 커스텀 알림만 가능합니다.

## AI 에이전트용 skill

AI 에이전트가 CLI 명령어를 안정적으로 사용할 수 있도록 `skills/honsanam-reminder`에 Codex skill을 제공합니다.

이 skill은 초기 설정, 상태 점검, 미리보기, 알림 발송, 기본 알림 관리, 커스텀 알림 추가와 수정, 메시지 패턴 변경, 설정 검증에 필요한 CLI 사용 기준을 담고 있습니다.

## launchd

```bash
scripts/install_launch_agent.sh
scripts/uninstall_launch_agent.sh
```

LaunchAgent는 5분마다 `honsanam-reminder run-once`를 실행합니다. 중복 알림 발송은 `.local/state/sent.json` 파일로 방지합니다.
