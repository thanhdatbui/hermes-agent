from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

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


def test_is_in_cooldown_behavior(tmp_path):
    from datetime import datetime, timedelta
    state_file = tmp_path / "post_noon_chain_state.json"
    with patch.object(watchdog, "STATE_FILE", state_file):
        # Case 1: Không có state file
        assert watchdog.is_in_cooldown(45) is False

        # Case 2: Vừa chạy cách đây 10 phút (< 45 phút) -> in cooldown
        recent = (datetime.now(watchdog.HCMC) - timedelta(minutes=10)).isoformat()
        state_file.write_text(watchdog.json.dumps({"last_run_at": recent}), encoding="utf-8")
        assert watchdog.is_in_cooldown(45) is True

        # Case 3: Đã chạy cách đây 50 phút (> 45 phút) -> hết cooldown
        old = (datetime.now(watchdog.HCMC) - timedelta(minutes=50)).isoformat()
        state_file.write_text(watchdog.json.dumps({"last_run_at": old}), encoding="utf-8")
        assert watchdog.is_in_cooldown(45) is False

        # Case 4: Khi main() chạy trong lúc cooldown -> exit 0 ngay lập tức mà không gọi batch
        with (
            patch.object(watchdog, "already_ran_today", return_value=False),
            patch.object(watchdog, "is_in_cooldown", return_value=True),
            patch.object(watchdog, "run_gmail_batch") as mock_gmail,
            patch.object(sys, "argv", ["post_noon_chain_watchdog.py"]),
        ):
            assert watchdog.main() == 0
            mock_gmail.assert_not_called()


def test_parse_summary_counts_tiktok_table_and_skip_table_split():
    raw_output = (
        "1 | 101 | user1 | success | OK\n"
        "2 | 102 | user2 | failed | OTP_TIMEOUT\n"
        "3 | 103 | user3 | skipped | NO_2FA_NEEDED\n"
        "Skip do device lock:\n"
        "1 | 101 | user1 | skipped | ALREADY_COUNTED\n"
    )
    res = watchdog.parse_summary_counts(raw_output)
    assert res["total"] == 3
    assert res["success"] == 1
    assert res["failed"] == 1
    assert res["skip_safe"] == 1


def test_gmail_dual_cluster_reporting(capsys):
    k_out = "=== CLUSTER KIBE (MÁY 1-80) ===\nTOTAL=10 SUCCESS=8 FAILED=2"
    a_out = "=== CLUSTER ADMIN (MÁY 201-280) ===\nTOTAL=10 SUCCESS=7 FAILED=3"
    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog, "run_gmail_batch", return_value=(0, f"{k_out}\n{a_out}")),
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--lane", "gmail", "--dry-run"]),
    ):
        assert watchdog.main() == 0

    output = capsys.readouterr().out
    assert "Farm Kibe (Máy 1-80): Hoàn tất 8 máy" in output
    assert "Farm Admin (Máy 201-280): Hoàn tất 7 máy" in output


def test_gmail_admin_ssh_error_handling(capsys):
    k_out = "=== CLUSTER KIBE (MÁY 1-80) ===\nTOTAL=5 SUCCESS=3 FAILED=2"
    a_out = "=== CLUSTER ADMIN (MÁY 201-280) ===\nRUNNER_ERROR|ADMIN|TimeoutExpired: ssh timeout"
    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog, "run_gmail_batch", return_value=(2, f"{k_out}\n{a_out}")),
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--lane", "gmail", "--dry-run"]),
    ):
        assert watchdog.main() == 0

    output = capsys.readouterr().out
    assert "Farm Kibe (Máy 1-80): Hoàn tất 3 máy" in output
    assert "Farm Admin (Máy 201-280): Hoàn tất 0 máy" in output


def test_runner_exit_code_2_persists_failed_state():
    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog, "run_gmail_batch", return_value=(2, "RUNNER_ERROR")),
        patch.object(watchdog, "run_tiktok_2fa_batch", return_value=(0, "")),
        patch.object(watchdog, "save_state") as mock_save,
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--lane", "gmail", "--force"]),
    ):
        assert watchdog.main() == 0
        details = mock_save.call_args[0][1]
        assert details["gmail_status"] == "failed"
        assert details["lane_status"] == "failed"


GMAIL_OK = "TOTAL=2 SUCCESS=2 FAILED=0"
TIKTOK_OK = "1 | 2 | u1 | success | -\n2 | 3 | u2 | success | -\n"


@pytest.fixture
def fake_repos(tmp_path, monkeypatch):
    gmail_dir = tmp_path / "gmail"
    gmail_dir.mkdir()
    (gmail_dir / "run_all.ps1").write_text("", encoding="utf-8")
    tiktok_dir = tmp_path / "tiktok"
    (tiktok_dir / "python_runner").mkdir(parents=True)
    (tiktok_dir / "python_runner" / "run_batch_live_2fa.py").write_text("", encoding="utf-8")
    monkeypatch.setattr(watchdog, "GMAIL_REPO_DIR", gmail_dir)
    monkeypatch.setattr(watchdog, "TIKTOK_2FA_REPO_DIR", tiktok_dir)
    monkeypatch.setattr(watchdog, "RUN_ID", "")
    return tmp_path


def make_fake_run(calls, *, kibe, admin):
    """kibe/admin: chuỗi stdout (cluster sống) hoặc Exception (cluster chết)."""
    def fake_run(cmd, **kwargs):
        target = "admin" if cmd[0] == "ssh" else "kibe"
        calls.append(target)
        outcome = admin if target == "admin" else kibe
        if isinstance(outcome, BaseException):
            raise outcome
        return subprocess.CompletedProcess(cmd, 0, stdout=outcome, stderr="")
    return fake_run


def stderr_events(text):
    return [json.loads(line.split(" ", 1)[1]) for line in text.splitlines() if line.startswith("WATCHDOG_EVENT ")]


SSH_TIMEOUT = subprocess.TimeoutExpired(cmd="ssh admin-farm", timeout=5400)
KIBE_TIMEOUT = subprocess.TimeoutExpired(cmd="run_all.ps1", timeout=5400)


def test_emit_event_is_structured_json_with_run_id(capsys, monkeypatch):
    monkeypatch.setattr(watchdog, "RUN_ID", "abc123def456")
    watchdog.emit_event("cluster_runner_error", cluster="ADMIN", detail="Tiếng Việt")
    (event,) = stderr_events(capsys.readouterr().err)
    assert event["run_id"] == "abc123def456"
    assert event["event"] == "cluster_runner_error"
    assert event["cluster"] == "ADMIN"
    assert event["detail"] == "Tiếng Việt"
    assert datetime.fromisoformat(event["ts"]).tzinfo is not None


def test_emit_event_schema_and_phase_correlation(fake_repos, capsys):
    calls: list[str] = []
    ok = GMAIL_OK + "\n" + TIKTOK_OK
    runner = make_fake_run(calls, kibe=KIBE_TIMEOUT, admin=ok)
    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_in_cooldown", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog.subprocess, "run", side_effect=runner),
        patch.object(watchdog, "save_state"),
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--lane", "all", "--force"]),
    ):
        watchdog.main()

    events = stderr_events(capsys.readouterr().err)
    assert events

    # Schema: mọi event đều có ts (timezone-aware), run_id, event; trường dữ liệu đi kèm phẳng trong record
    for e in events:
        assert {"ts", "run_id", "event"} <= e.keys()
        assert datetime.fromisoformat(e["ts"]).tzinfo is not None
        assert isinstance(e["event"], str) and e["event"]

    # run_id sinh 1 lần và liên tục qua chain_start -> các phase -> chain_end
    run_ids = {e["run_id"] for e in events}
    assert len(run_ids) == 1
    assert re.fullmatch(r"[0-9a-f]{12}", run_ids.pop())

    names = [e["event"] for e in events]
    assert names[0] == "chain_start" and names[-1] == "chain_end"
    phases = [e["phase"] for e in events if e["event"] == "cluster_runner_error"]
    assert phases == ["gmail", "tiktok_2fa"]


@pytest.mark.parametrize(
    "batch_name, ok_out, dead",
    [
        ("run_gmail_batch", GMAIL_OK, "KIBE"),
        ("run_gmail_batch", GMAIL_OK, "ADMIN"),
        ("run_tiktok_2fa_batch", TIKTOK_OK, "KIBE"),
        ("run_tiktok_2fa_batch", TIKTOK_OK, "ADMIN"),
    ],
)
def test_single_cluster_dies_other_cluster_still_runs(fake_repos, capsys, batch_name, ok_out, dead):
    calls: list[str] = []
    timeout = KIBE_TIMEOUT if dead == "KIBE" else SSH_TIMEOUT
    runner = make_fake_run(
        calls,
        kibe=timeout if dead == "KIBE" else ok_out,
        admin=timeout if dead == "ADMIN" else ok_out,
    )
    with patch.object(watchdog.subprocess, "run", side_effect=runner):
        code, out = getattr(watchdog, batch_name)()

    # Cả hai cluster đều được thử dù một cụm chết giữa phiên
    assert sorted(calls) == ["admin", "kibe"]
    assert code != 0
    assert f"RUNNER_ERROR|{dead}|TimeoutExpired" in out
    assert out.count("RUNNER_ERROR") == 1
    assert ok_out.strip().splitlines()[0] in out

    (event,) = stderr_events(capsys.readouterr().err)
    assert event["event"] == "cluster_runner_error"
    assert event["cluster"] == dead
    assert event["phase"] == ("gmail" if batch_name == "run_gmail_batch" else "tiktok_2fa")
    assert event["error"] == "TimeoutExpired"


@pytest.mark.parametrize("batch_name", ["run_gmail_batch", "run_tiktok_2fa_batch"])
def test_both_clusters_die_returns_failure_with_two_error_events(fake_repos, capsys, batch_name):
    calls: list[str] = []
    runner = make_fake_run(calls, kibe=KIBE_TIMEOUT, admin=SSH_TIMEOUT)
    with patch.object(watchdog.subprocess, "run", side_effect=runner):
        code, out = getattr(watchdog, batch_name)()

    assert code != 0
    assert "RUNNER_ERROR|KIBE|TimeoutExpired" in out
    assert "RUNNER_ERROR|ADMIN|TimeoutExpired" in out
    events = stderr_events(capsys.readouterr().err)
    assert [e["cluster"] for e in events] == ["KIBE", "ADMIN"]


@pytest.mark.parametrize("dead", ["KIBE", "ADMIN"])
def test_main_report_flags_dead_cluster_with_run_id_and_keeps_other_cluster(fake_repos, capsys, dead):
    calls: list[str] = []
    timeout = KIBE_TIMEOUT if dead == "KIBE" else SSH_TIMEOUT
    # Gmail: cluster còn sống in TOTAL/SUCCESS; TikTok: in bảng kết quả
    runner = make_fake_run(
        calls,
        kibe=timeout if dead == "KIBE" else GMAIL_OK + "\n" + TIKTOK_OK,
        admin=timeout if dead == "ADMIN" else GMAIL_OK + "\n" + TIKTOK_OK,
    )
    with (
        patch.object(watchdog, "already_ran_today", return_value=False),
        patch.object(watchdog, "is_in_cooldown", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
        patch.object(watchdog.subprocess, "run", side_effect=runner),
        patch.object(watchdog, "save_state") as save_state,
        patch.object(sys, "argv", ["post_noon_chain_watchdog.py", "--lane", "all", "--force"]),
    ):
        assert watchdog.main() == 0

    # Phase 2 vẫn chạy dù Phase 1 có cluster chết (thiết kế decoupled): 2 lần/phase
    assert sorted(calls) == ["admin", "admin", "kibe", "kibe"]

    captured = capsys.readouterr()
    run_id_lines = [ln for ln in captured.out.splitlines() if ln.startswith("- Mã chạy (run_id): ")]
    assert len(run_id_lines) == 1
    run_id = run_id_lines[0].split(": ", 1)[1]
    assert re.fullmatch(r"[0-9a-f]{12}", run_id)

    dead_title = "Farm Kibe (Máy 1-80)" if dead == "KIBE" else "Farm Admin (Máy 201-280)"
    alive_title = "Farm Admin (Máy 201-280)" if dead == "KIBE" else "Farm Kibe (Máy 1-80)"
    dead_lines = [ln for ln in captured.out.splitlines() if dead_title in ln]
    alive_lines = [ln for ln in captured.out.splitlines() if alive_title in ln]
    assert len(dead_lines) == 2 and len(alive_lines) == 2  # Phase 1 + Phase 2
    assert all("Hoàn tất 0 máy" in ln and "Runner lỗi: TimeoutExpired" in ln for ln in dead_lines)
    assert all("Hoàn tất 2 máy" in ln and "Runner lỗi" not in ln for ln in alive_lines)

    # Correlation id nhất quán giữa báo cáo, structured events và state
    events = stderr_events(captured.err)
    assert {e["run_id"] for e in events} == {run_id}
    names = [e["event"] for e in events]
    assert names[0] == "chain_start" and names[-1] == "chain_end"
    assert names.count("cluster_runner_error") == 2
    assert {e["cluster"] for e in events if e["event"] == "cluster_runner_error"} == {dead}

    details = save_state.call_args[0][1]
    assert details["run_id"] == run_id
    assert details["gmail_status"] == "failed"
    assert details["2fa_status"] == "failed"
    assert details["lane_status"] == "failed"


def test_dead_cluster_run_is_retried_next_cycle_and_success_recorded(fake_repos, tmp_path, capsys):
    state_file = tmp_path / "state" / "post_noon_chain_state.json"
    argv = ["post_noon_chain_watchdog.py", "--lane", "all", "--force"]
    with (
        patch.object(watchdog, "STATE_FILE", state_file),
        patch.object(watchdog, "STATE_DIR", state_file.parent),
        patch.object(watchdog, "is_in_cooldown", return_value=False),
        patch.object(watchdog, "is_feed_runner_active", return_value=False),
        patch.object(watchdog, "has_active_device_locks", return_value=False),
    ):
        # Lần 1: Admin chết giữa phiên -> state failed, không đánh dấu thành công
        broken = make_fake_run([], kibe=GMAIL_OK + "\n" + TIKTOK_OK, admin=SSH_TIMEOUT)
        with patch.object(watchdog.subprocess, "run", side_effect=broken), patch.object(sys, "argv", argv):
            assert watchdog.main() == 0
        first = json.loads(state_file.read_text(encoding="utf-8"))
        assert first["last_success_date"] is None
        assert first["details"]["lane_status"] == "failed"
        today = datetime.now(watchdog.HCMC).strftime("%Y-%m-%d")
        assert watchdog.already_ran_today(today) is False

        # Lần 2: Admin hồi phục -> state success với run_id mới
        healthy = make_fake_run([], kibe=GMAIL_OK + "\n" + TIKTOK_OK, admin=GMAIL_OK + "\n" + TIKTOK_OK)
        with patch.object(watchdog.subprocess, "run", side_effect=healthy), patch.object(sys, "argv", argv):
            assert watchdog.main() == 0
        second = json.loads(state_file.read_text(encoding="utf-8"))
        assert second["last_success_date"] == today
        assert second["details"]["lane_status"] == "success"
        assert second["details"]["run_id"] != first["details"]["run_id"]
        assert watchdog.already_ran_today(today) is True






