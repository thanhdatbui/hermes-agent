from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

scripts_dir = Path(__file__).resolve().parent.parent / "deploy" / "hermes-home" / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

import post_noon_chain_watchdog as watchdog


def test_lane_all_backward_compatible_runs_gmail_only(capsys):
    calls: list[str] = []

    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog, "run_gmail_batch", side_effect=lambda **kw: (calls.append("gmail") or (0, "TOTAL=2 SUCCESS=2 FAILED=0"))),
        patch.object(watchdog, "run_tiktok_2fa_batch", side_effect=lambda **kw: (calls.append("tiktok") or (0, ""))),
        patch.object(watchdog, "save_state") as save_state,
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--lane", "all", "--dry-run"]),
    ):
        assert watchdog.main() == 0

    assert calls == ["gmail"]
    output = capsys.readouterr().out
    assert "[LANE GMAIL]" in output
    assert "Phase 1 (Reg Gmail - Code 0)" in output
    assert "• Đã hoàn tất: 2 máy" in output
    assert "Phase 2" not in output
    save_state.assert_not_called()


def test_lane_all_live_saves_state():
    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog, "run_gmail_batch", return_value=(0, "TOTAL=1 SUCCESS=1 FAILED=0")),
        patch.object(watchdog, "save_state") as save_state,
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--lane", "all", "--force"]),
    ):
        assert watchdog.main() == 0
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
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--dry-run"]),
    ):
        assert watchdog.main() == 0

    gmail_batch.assert_called_once_with(dry_run=True)
    tiktok_batch.assert_not_called()
    output = capsys.readouterr().out
    assert "[LANE GMAIL]" in output
    assert "Phase 1 (Reg Gmail - Code 0)" in output
    assert "Phase 2" not in output


def test_gmail_report_formats_platform_and_script_errors(capsys):
    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog, "run_gmail_batch", return_value=(0, "TOTAL=3 SUCCESS=2 FAILED=1")),
        patch.object(watchdog, "parse_summary_counts", return_value={
            "total": 3, "success": 2, "failed": 1, "skip_safe": 0,
            "failure_breakdown": {
                "platform_errors": {"phone_verify": 1},
                "script_errors": {"failed_cleanup": 0}
            }
        }),
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--lane", "gmail", "--dry-run"]),
    ):
        assert watchdog.main() == 0

    output = capsys.readouterr().out
    assert "• Đã hoàn tất: 2 máy" in output
    assert "• Lỗi nền tảng (1): phone_verify: 1" in output
    assert "• Lỗi script: 0" in output


def test_gmail_report_formats_script_failure_when_success_is_zero(capsys):
    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog, "run_gmail_batch", return_value=(1, "TOTAL=2 SUCCESS=0 FAILED=2")),
        patch.object(watchdog, "parse_summary_counts", return_value={
            "total": 2, "success": 0, "failed": 2, "skip_safe": 0,
            "failure_breakdown": {"script_errors": {"failed_cleanup": 2}}
        }),
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--lane", "gmail", "--dry-run"]),
    ):
        assert watchdog.main() == 0

    output = capsys.readouterr().out
    assert "• Đã hoàn tất: 0 máy" in output
    assert "• Lỗi script (2): failed_cleanup: 2" in output


def test_gmail_report_formats_safe_skip_and_mixed_breakdown(capsys):
    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog, "run_gmail_batch", return_value=(0, "TOTAL=4 SUCCESS=1 FAILED=3")),
        patch.object(watchdog, "parse_summary_counts", return_value={
            "total": 4, "success": 1, "failed": 2, "skip_safe": 1,
            "failure_breakdown": {
                "platform_errors": {"phone_verify": 1},
                "script_errors": {"failed_other": 1}
            }
        }),
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--lane", "gmail", "--dry-run"]),
    ):
        assert watchdog.main() == 0

    output = capsys.readouterr().out
    assert "• Đã hoàn tất: 1 máy" in output
    assert "• Bỏ qua an toàn: 1 máy (đầy slot)" in output
    assert "• Lỗi nền tảng (1): phone_verify: 1" in output
    assert "• Lỗi script (1): failed_other: 1" in output


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


def test_summary_result_backward_compatibility_and_stub():
    sr = watchdog.SummaryResult({"total": 15, "success": 7, "failed": 5, "skip_safe": 3})
    tot, suc, fail = sr
    assert (tot, suc, fail) == (15, 7, 5)
    assert sr["skip_safe"] == 3
    assert watchdog.parse_chatgpt_warmup_counts() == (0, 0)

