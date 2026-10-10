from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

scripts_dir = Path(__file__).resolve().parent.parent / "deploy" / "hermes-home" / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

import post_noon_chain_watchdog as watchdog


def test_lane_all_runs_both_gmail_and_tiktok(capsys):
    calls: list[str] = []

    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog, "run_gmail_batch", side_effect=lambda **kw: (calls.append("gmail") or (0, "TOTAL=2 SUCCESS=2 FAILED=0"))),
        patch.object(watchdog, "run_tiktok_2fa_batch", side_effect=lambda **kw: (calls.append("tiktok") or (0, "TOTAL=2 SUCCESS=2 FAILED=0"))),
        patch.object(watchdog, "save_state") as save_state,
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--lane", "all", "--dry-run"]),
    ):
        assert watchdog.main() == 0

    assert calls == ["gmail", "tiktok"]
    output = capsys.readouterr().out
    assert "[LANE ALL (GMAIL + TIKTOK 2FA)]" in output
    assert "Phase 1 (Reg Gmail - Code 0)" in output
    assert "Phase 2 (Add 2FA TikTok - Code 0)" in output
    save_state.assert_not_called()


def test_lane_all_live_saves_state():
    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog, "run_gmail_batch", return_value=(0, "TOTAL=1 SUCCESS=1 FAILED=0")),
        patch.object(watchdog, "run_tiktok_2fa_batch", return_value=(0, "TOTAL=1 SUCCESS=1 FAILED=0")),
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


def test_default_lane_runs_all(capsys):
    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog, "run_gmail_batch", return_value=(0, "TOTAL=1 SUCCESS=1 FAILED=0")) as gmail_batch,
        patch.object(watchdog, "run_tiktok_2fa_batch", return_value=(0, "TOTAL=1 SUCCESS=1 FAILED=0")) as tiktok_batch,
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--dry-run"]),
    ):
        assert watchdog.main() == 0

    gmail_batch.assert_called_once_with(dry_run=True)
    tiktok_batch.assert_called_once_with(dry_run=True)
    output = capsys.readouterr().out
    assert "[LANE ALL (GMAIL + TIKTOK 2FA)]" in output
    assert "Phase 1 (Reg Gmail - Code 0)" in output
    assert "Phase 2 (Add 2FA TikTok - Code 0)" in output


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
    assert "• Bỏ qua an toàn: 1 máy (đầy slot / nhường cron khác)" in output
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
    assert "[LANE TIKTOK 2FA]" in output
    assert "Phase 1" not in output
    assert "Phase 2 (Add 2FA TikTok - Code 0)" in output


def test_summary_result_backward_compatibility_and_stub():
    sr = watchdog.SummaryResult({"total": 15, "success": 7, "failed": 5, "skip_safe": 3})
    tot, suc, fail = sr
    assert (tot, suc, fail) == (15, 7, 5)
    assert sr["skip_safe"] == 3
    assert watchdog.parse_chatgpt_warmup_counts() == (0, 0)


def test_cluster_failure_and_partial_error_reporting(capsys):
    kibe_out = "=== CLUSTER KIBE (MÁY 1-80) ===\n1 | 2 | u1 | success | -\n2 | 3 | u2 | failed | UI_ERROR\n"
    admin_out = "=== CLUSTER ADMIN (MÁY 201-280) ===\nLỗi chạy Admin 2FA: ssh timeout\n"
    combined_out = kibe_out + admin_out

    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog, "run_gmail_batch", return_value=(0, "TOTAL=2 SUCCESS=1 FAILED=1")),
        patch.object(watchdog, "run_tiktok_2fa_batch", return_value=(1, combined_out)),
        patch.object(watchdog, "save_state") as save_state,
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--lane", "all", "--force"]),
    ):
        assert watchdog.main() == 0
        save_state.assert_called_once()
        details = save_state.call_args[0][1]
        assert details["gmail_status"] == "success"
        assert details["2fa_status"] == "failed"
        assert details["lane_status"] == "failed"

    output = capsys.readouterr().out
    assert "Farm Kibe (Máy 1-80): Hoàn tất 1 máy | Bỏ qua 0 | Lỗi 1" in output
    assert "Farm Admin (Máy 201-280): Hoàn tất 0 máy" in output


def test_save_state_preserves_previous_success_on_failure(tmp_path):
    state_file = tmp_path / "post_noon_chain_state.json"
    with patch.object(watchdog, "STATE_FILE", state_file), patch.object(watchdog, "STATE_DIR", tmp_path):
        watchdog.save_state("2026-10-06", {"lane_status": "success", "2fa_status": "success"})
        assert watchdog.already_ran_today("2026-10-06") is True

        watchdog.save_state("2026-10-07", {"lane_status": "failed", "2fa_status": "failed"})
        data = watchdog.json.loads(state_file.read_text(encoding="utf-8"))
        assert data["last_success_date"] == "2026-10-06"
        assert watchdog.already_ran_today("2026-10-07") is False


def test_dry_run_batch_runners_contract():
    g_code, g_out = watchdog.run_gmail_batch(dry_run=True)
    assert g_code == 0
    assert "dry-run" in g_out

    t_code, t_out = watchdog.run_tiktok_2fa_batch(dry_run=True)
    assert t_code == 0
    assert "dry-run" in t_out


def test_mixed_lane_state_combinations(tmp_path):
    state_file = tmp_path / "post_noon_chain_state.json"
    with patch.object(watchdog, "STATE_FILE", state_file), patch.object(watchdog, "STATE_DIR", tmp_path):
        # Case 1: Gmail failed (1), TikTok 2FA succeeded (0) -> lane_status must be failed, NOT marked success
        watchdog.save_state("2026-10-07", {
            "gmail_code": 1,
            "2fa_code": 0,
            "lane": "all",
            "gmail_status": "failed",
            "2fa_status": "success",
            "lane_status": "failed",
        })
        assert watchdog.already_ran_today("2026-10-07") is False

        # Case 2: Gmail succeeded (0), TikTok 2FA succeeded (4) -> lane_status must be success
        watchdog.save_state("2026-10-07", {
            "gmail_code": 0,
            "2fa_code": 4,
            "lane": "all",
            "gmail_status": "success",
            "2fa_status": "success",
            "lane_status": "success",
        })
        assert watchdog.already_ran_today("2026-10-07") is True


def test_gmail_batch_code_1_with_total_greater_than_zero_marks_success():
    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog, "run_gmail_batch", return_value=(1, "TOTAL=5 SUCCESS=2 FAILED=3")),
        patch.object(watchdog, "run_tiktok_2fa_batch", return_value=(0, "TOTAL=1 SUCCESS=1 FAILED=0")),
        patch.object(watchdog, "save_state") as save_state,
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--lane", "all", "--force"]),
    ):
        assert watchdog.main() == 0
        save_state.assert_called_once()
        details = save_state.call_args[0][1]
        assert details["gmail_status"] == "success"
        assert details["lane_status"] == "success"


