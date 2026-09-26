from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

scripts_dir = Path(__file__).resolve().parent.parent / "deploy" / "hermes-home" / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

import post_noon_chain_watchdog as watchdog


def test_lane_all_runs_gmail_then_tiktok_and_reports_both(capsys):
    calls: list[str] = []

    def fake_gmail_batch(*, dry_run: bool):
        calls.append("gmail")
        assert dry_run is True
        return 0, "TOTAL=2 SUCCESS=2 FAILED=0"

    def fake_tiktok_batch(*, dry_run: bool):
        calls.append("tiktok")
        assert dry_run is True
        return 0, "TOTAL=3 SUCCESS=3 FAILED=0"

    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog, "run_gmail_batch", side_effect=fake_gmail_batch),
        patch.object(watchdog, "run_tiktok_2fa_batch", side_effect=fake_tiktok_batch),
        patch.object(watchdog, "parse_chatgpt_warmup_counts", return_value=(0, 0)),
        patch.object(watchdog, "save_state") as save_state,
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--lane", "all", "--dry-run"]),
    ):
        assert watchdog.main() == 0

    assert calls == ["gmail", "tiktok"]
    output = capsys.readouterr().out
    assert "[LANE ALL]" in output
    assert "Phase 1 (Reg Gmail - Code 0)" in output
    assert "Phase 2 (Add 2FA TikTok - Code 0)" in output
    assert "Tổng máy: 2" in output
    assert "Tổng máy: 3" in output
    save_state.assert_not_called()


def test_lane_all_live_saves_state():
    calls: list[str] = []

    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog, "run_gmail_batch", return_value=(0, "TOTAL=1 SUCCESS=1 FAILED=0")),
        patch.object(watchdog, "run_tiktok_2fa_batch", return_value=(0, "TOTAL=1 SUCCESS=1 FAILED=0")),
        patch.object(watchdog, "parse_chatgpt_warmup_counts", return_value=(0, 0)),
        patch.object(watchdog, "time") as mock_time,
        patch.object(watchdog, "save_state") as save_state,
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--lane", "all", "--force"]),
    ):
        assert watchdog.main() == 0
        mock_time.sleep.assert_called_once_with(15)
        save_state.assert_called_once()
        args = save_state.call_args[0]
        assert args[1]["lane"] == "all"
        assert args[1]["lane_status"] == "success"
        assert args[1]["gmail_code"] == 0
        assert args[1]["2fa_code"] == 0


def test_lane_gmail_only(capsys):
    calls: list[str] = []

    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog, "run_gmail_batch", side_effect=lambda **kw: (calls.append("gmail") or (0, "TOTAL=1 SUCCESS=1 FAILED=0"))),
        patch.object(watchdog, "run_tiktok_2fa_batch", side_effect=lambda **kw: (calls.append("tiktok") or (0, ""))),
        patch.object(watchdog, "parse_chatgpt_warmup_counts", return_value=(0, 0)),
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--lane", "gmail", "--dry-run"]),
    ):
        assert watchdog.main() == 0

    assert calls == ["gmail"]
    output = capsys.readouterr().out
    assert "[LANE GMAIL]" in output
    assert "Phase 1 (Reg Gmail - Code 0)" in output
    assert "Phase 2" not in output


def test_default_lane_preserves_legacy_gmail_only_behavior(capsys):
    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog, "run_gmail_batch", return_value=(0, "TOTAL=1 SUCCESS=1 FAILED=0")) as gmail_batch,
        patch.object(watchdog, "run_tiktok_2fa_batch") as tiktok_batch,
        patch.object(watchdog, "parse_chatgpt_warmup_counts", return_value=(0, 0)),
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--dry-run"]),
    ):
        assert watchdog.main() == 0

    gmail_batch.assert_called_once_with(dry_run=True)
    tiktok_batch.assert_not_called()
    output = capsys.readouterr().out
    assert "[LANE GMAIL]" in output
    assert "Phase 1 (Reg Gmail - Code 0)" in output
    assert "Phase 2" not in output


def test_gmail_report_preserves_chatgpt_warmup_detail(capsys):
    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog, "run_gmail_batch", return_value=(0, "TOTAL=3 SUCCESS=2 FAILED=1")),
        patch.object(watchdog, "parse_chatgpt_warmup_counts", return_value=(2, 1)),
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--lane", "gmail", "--dry-run"]),
    ):
        assert watchdog.main() == 0

    output = capsys.readouterr().out
    assert "ChatGPT linked: 2/2 (1 fail)" in output


def test_lane_tiktok_only(capsys):
    calls: list[str] = []

    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog, "run_gmail_batch", side_effect=lambda **kw: (calls.append("gmail") or (0, ""))),
        patch.object(watchdog, "run_tiktok_2fa_batch", side_effect=lambda **kw: (calls.append("tiktok") or (0, "TOTAL=1 SUCCESS=1 FAILED=0"))),
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--lane", "tiktok", "--dry-run"]),
    ):
        assert watchdog.main() == 0

    assert calls == ["tiktok"]
    output = capsys.readouterr().out
    assert "[LANE TIKTOK]" in output
    assert "Phase 1" not in output
    assert "Phase 2 (Add 2FA TikTok - Code 0)" in output
