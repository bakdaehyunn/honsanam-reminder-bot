from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_install_launch_agent_writes_replies_and_sender_plists() -> None:
    script = ROOT.joinpath("scripts/install_launch_agent.sh").read_text(encoding="utf-8")

    assert 'BASE_LABEL="com.hennei.honsanam-reminder-bot"' in script
    assert 'REPLIES_LABEL="$BASE_LABEL.replies"' in script
    assert 'SENDER_LABEL="$BASE_LABEL.sender"' in script
    assert "<string>poll-replies</string>" in script
    assert "<string>--watch</string>" in script
    assert "<key>KeepAlive</key>" in script
    assert "<true/>" in script
    assert "<string>run-once</string>" in script
    assert "<key>StartInterval</key>" in script
    assert "<integer>300</integer>" in script
    assert "<key>StartCalendarInterval</key>" not in script


def test_uninstall_launch_agent_removes_legacy_and_split_plists() -> None:
    script = ROOT.joinpath("scripts/uninstall_launch_agent.sh").read_text(encoding="utf-8")

    assert "$BASE_LABEL.plist" in script
    assert "$BASE_LABEL.replies.plist" in script
    assert "$BASE_LABEL.sender.plist" in script
