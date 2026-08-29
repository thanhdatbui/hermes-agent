import io
import json
import multiprocessing
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import pytest

# Repo-relative import of watchdog script under test
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import feed_session_watchdog
from feed_session_watchdog import (
    ProcessLock,
    parse_run_machines,
    parse_follow_results,
    parse_upload_results,
    get_expected_machines_for_row,
    SESSION_WINDOWS,
    main,
)


def _child_lock_worker(lock_path, queue):
    lock = ProcessLock(lock_path)
    res = lock.acquire()
    queue.put(res)
    if res:
        time.sleep(0.5)
        lock.release()


def test_process_lock_cross_process_mutual_exclusion(tmp_path):
    lock_file = str(tmp_path / "test.proc_lock")
    lock1 = ProcessLock(lock_file)
    assert lock1.acquire() is True
    assert lock1.acquire() is False  # Re-entrant returns False

    queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=_child_lock_worker, args=(lock_file, queue))
    p.start()
    child_acquired = queue.get(timeout=5)
    p.join()
    assert child_acquired is False

    lock1.release()

    p2 = multiprocessing.Process(target=_child_lock_worker, args=(lock_file, queue))
    p2.start()
    child_acquired_after = queue.get(timeout=5)
    p2.join()
    assert child_acquired_after is True


def test_process_lock_basename_only(tmp_path, monkeypatch):
    # Test acquiring a lock with a relative basename
    monkeypatch.chdir(tmp_path)
    lock = ProcessLock("local_basename.lock")
    assert lock.acquire() is True
    lock.release()


def test_load_reported_sessions_malformed_state(tmp_path):
    # Test handling of malformed state files
    f1 = tmp_path / "null_state.json"
    f1.write_text("null", encoding="utf-8")
    assert feed_session_watchdog._load_reported_sessions(str(f1)) == set()

    f2 = tmp_path / "list_state.json"
    f2.write_text("[]", encoding="utf-8")
    assert feed_session_watchdog._load_reported_sessions(str(f2)) == set()

    f3 = tmp_path / "null_field_state.json"
    f3.write_text(json.dumps({"reported_sessions": None}), encoding="utf-8")
    assert feed_session_watchdog._load_reported_sessions(str(f3)) == set()

    f4 = tmp_path / "valid_state.json"
    f4.write_text(json.dumps({"reported_sessions": ["s1", "s2"]}), encoding="utf-8")
    assert feed_session_watchdog._load_reported_sessions(str(f4)) == {"s1", "s2"}


def test_watchdog_boundary_run_selection(tmp_path, monkeypatch, capsys):
    live_root = tmp_path / "live"
    today = "2026-08-28"
    today_dir = live_root / today
    today_dir.mkdir(parents=True)

    state_file = tmp_path / "feed_session_reported.json"
    source_config = tmp_path / "source_config.json"
    source_config.write_text(
        json.dumps({
            "feed_source": {
                "accounts": [
                    {"machine": 1, "account_row": "1"},
                    {"machine": 2, "account_row": "1"},
                ]
            }
        }),
        encoding="utf-8",
    )

    # 1. Create run at exact 07:30 boundary (belongs to Ca 1 Phiên 2 [07:30, 09:30), NOT Phiên 1 [06:00, 07:30))
    run_0730 = today_dir / "row-1-073000-run" / "machines" / "machine_1"
    run_0730.mkdir(parents=True)
    (run_0730 / "summary.txt").write_text("final_status: success\n", encoding="utf-8")

    monkeypatch.setattr(feed_session_watchdog, "LIVE_ROOT", str(live_root))
    monkeypatch.setattr(feed_session_watchdog, "STATE_FILE", str(state_file))
    monkeypatch.setattr(feed_session_watchdog, "SOURCE_CONFIG", str(source_config))
    monkeypatch.setattr(feed_session_watchdog, "is_feed_runner_active", lambda: False)

    # Run watchdog at 09:35 (after Ca 1 Phiên 2 window end 09:30)
    fake_now = datetime(2026, 8, 28, 9, 35, 0, tzinfo=feed_session_watchdog.HCMC)
    with patch("feed_session_watchdog.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        main()

    out = capsys.readouterr().out
    # 07:30 run must be reported under Phiên 2
    assert "Ca 1 - Phiên 2/3 (Sáng)" in out
    assert "Success (1): 1" in out
    assert "Ca 1 - Phiên 1/3" not in out

    # 2. Incomplete final window on today at 23:59:00 (only machine 2 completed out of 2 expected)
    # MUST stay deferred (not report prematurely)
    run_2359 = today_dir / "row-1-235900-run" / "machines" / "machine_2"
    run_2359.mkdir(parents=True)
    (run_2359 / "summary.txt").write_text("final_status: success\n", encoding="utf-8")

    fake_now_late = datetime(2026, 8, 28, 23, 59, 0, tzinfo=feed_session_watchdog.HCMC)
    with patch("feed_session_watchdog.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now_late
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        main()

    out_incomplete = capsys.readouterr().out
    # Final window should NOT report yet because only 1 of 2 expected machines completed
    assert "Ca 3 - Phiên 3/3 (Tối)" not in out_incomplete

    # 3. When second expected machine completes, it reports immediately
    m1_final = today_dir / "row-1-235900-run" / "machines" / "machine_1"
    m1_final.mkdir(parents=True)
    (m1_final / "summary.txt").write_text("final_status: success\n", encoding="utf-8")

    with patch("feed_session_watchdog.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now_late
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        main()

    out_complete = capsys.readouterr().out
    assert "Ca 3 - Phiên 3/3 (Tối)" in out_complete
    assert "Success (2): 1, 2" in out_complete


def test_watchdog_multi_day_backlog_recovery(tmp_path, monkeypatch, capsys):
    live_root = tmp_path / "live"
    # Three days ago backlog
    old_date = "2026-08-25"
    old_dir = live_root / old_date
    old_dir.mkdir(parents=True)

    state_file = tmp_path / "feed_session_reported.json"
    source_config = tmp_path / "source_config.json"

    run_dir = old_dir / "row-1-223000-run" / "machines" / "machine_5"
    run_dir.mkdir(parents=True)
    (run_dir / "summary.txt").write_text("final_status: success\n", encoding="utf-8")

    monkeypatch.setattr(feed_session_watchdog, "LIVE_ROOT", str(live_root))
    monkeypatch.setattr(feed_session_watchdog, "STATE_FILE", str(state_file))
    monkeypatch.setattr(feed_session_watchdog, "SOURCE_CONFIG", str(source_config))
    monkeypatch.setattr(feed_session_watchdog, "is_feed_runner_active", lambda: False)

    # Watchdog runs today (2026-08-28)
    fake_now = datetime(2026, 8, 28, 10, 0, 0, tzinfo=feed_session_watchdog.HCMC)
    with patch("feed_session_watchdog.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        main()

    out = capsys.readouterr().out
    assert "Ca 3 - Phiên 3" in out
    assert "Success (1): 5" in out
    state_data = json.loads(state_file.read_text(encoding="utf-8"))
    assert "2026-08-25_ca3_phien3" in state_data["reported_sessions"]


def test_parse_upload_results_safe_types(tmp_path):
    run_dir = tmp_path / "run_1"
    run_dir.mkdir(parents=True)

    # Valid int
    (run_dir / "upload_result.json").write_text(
        json.dumps({"machine": 1, "status": "success", "exit_code": 0}),
        encoding="utf-8",
    )
    res = parse_upload_results(str(run_dir))
    assert res["1"]["status"] == "success"
    assert res["1"]["exit_code"] == 0

    # Non-int exit_code
    (run_dir / "upload_result.json").write_text(
        json.dumps({"machine": 2, "status": "failed", "exit_code": "bad_code"}),
        encoding="utf-8",
    )
    res = parse_upload_results(str(run_dir))
    assert res["2"]["status"] == "failed"
    assert res["2"]["exit_code"] == 1


def test_watchdog_full_session_flow_and_filtering(tmp_path, monkeypatch, capsys):
    live_root = tmp_path / "live"
    today = "2026-08-28"
    today_dir = live_root / today
    today_dir.mkdir(parents=True)

    state_file = tmp_path / "feed_session_reported.json"
    source_config = tmp_path / "source_config.json"
    source_config.write_text(
        json.dumps({
            "feed_source": {
                "accounts": [
                    {"machine": 37, "account_row": "1"},
                    {"machine": 38, "account_row": "1"},
                ]
            }
        }),
        encoding="utf-8",
    )

    # Create run directories for Ca 1 Phiên 3 (10:00 - 12:00)
    # 1. Malformed row run (should be skipped)
    malformed_run = today_dir / "row-invalid-100500-run"
    malformed_run.mkdir()

    # 2. Older run row 2 (should not set active_row because later run is row 1)
    old_r2 = today_dir / "row-2-101000-run" / "machines" / "machine_37"
    old_r2.mkdir(parents=True)
    (old_r2 / "summary.txt").write_text("final_status: success\n", encoding="utf-8")

    # 3. Latest run row 1 (determines active_row = 1)
    latest_r1 = today_dir / "row-1-102000-run" / "machines" / "machine_37"
    latest_r1.mkdir(parents=True)
    (latest_r1 / "summary.txt").write_text("final_status: success\n", encoding="utf-8")
    (latest_r1 / "follow_result.json").write_text(
        json.dumps({"machine": 37, "status": "OK", "followed": ["nickA"]}),
        encoding="utf-8",
    )
    (latest_r1 / "upload_result.json").write_text(
        json.dumps({"machine": 37, "status": "success", "exit_code": 0}),
        encoding="utf-8",
    )

    # Machine 38 failed feed
    m38_dir = today_dir / "row-1-102000-run" / "machines" / "machine_38"
    m38_dir.mkdir(parents=True)
    (m38_dir / "summary.txt").write_text("final_status: fail\nreason: network_timeout\n", encoding="utf-8")
    (m38_dir / "follow_result.json").write_text(
        json.dumps({"machine": 38, "status": "FOLLOW_FAILED", "follow_failed": True}),
        encoding="utf-8",
    )
    (m38_dir / "upload_result.json").write_text(
        json.dumps({"machine": 38, "status": "failed", "reason": "auth_error", "exit_code": 1}),
        encoding="utf-8",
    )

    # Monkeypatch paths
    monkeypatch.setattr(feed_session_watchdog, "LIVE_ROOT", str(live_root))
    monkeypatch.setattr(feed_session_watchdog, "STATE_FILE", str(state_file))
    monkeypatch.setattr(feed_session_watchdog, "SOURCE_CONFIG", str(source_config))
    monkeypatch.setattr(feed_session_watchdog, "is_feed_runner_active", lambda: False)

    # Run watchdog at 12:05 (after window end 12:00)
    fake_now = datetime(2026, 8, 28, 12, 5, 0, tzinfo=feed_session_watchdog.HCMC)
    with patch("feed_session_watchdog.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        main()

    out = capsys.readouterr().out
    assert "Ca 1 - Phiên 3/3 (Sáng) hoàn tất (Row 1)" in out
    assert "Success (1): 37" in out
    assert "Fail (1): M38" in out
    assert "Nhả follow (1): 38" in out
    assert "Đăng Video (Phiên 3):" in out
    assert "Success (1): 37" in out
    assert "Fail (1): M38(auth_error)" in out

    # Verify state was saved
    assert state_file.exists()
    state_data = json.loads(state_file.read_text(encoding="utf-8"))
    assert "2026-08-28_ca1_phien3" in state_data["reported_sessions"]


def test_watchdog_midnight_rollover(tmp_path, monkeypatch, capsys):
    live_root = tmp_path / "live"
    yesterday = "2026-08-27"
    yesterday_dir = live_root / yesterday
    yesterday_dir.mkdir(parents=True)

    state_file = tmp_path / "feed_session_reported.json"
    source_config = tmp_path / "source_config.json"

    # Yesterday's final session Ca 3 Phiên 3 (22:00 - 23:59)
    run_dir = yesterday_dir / "row-1-223000-run" / "machines" / "machine_10"
    run_dir.mkdir(parents=True)
    (run_dir / "summary.txt").write_text("final_status: success\n", encoding="utf-8")

    monkeypatch.setattr(feed_session_watchdog, "LIVE_ROOT", str(live_root))
    monkeypatch.setattr(feed_session_watchdog, "STATE_FILE", str(state_file))
    monkeypatch.setattr(feed_session_watchdog, "SOURCE_CONFIG", str(source_config))
    monkeypatch.setattr(feed_session_watchdog, "is_feed_runner_active", lambda: False)

    # Watchdog runs at 00:05 the next day (2026-08-28)
    fake_now = datetime(2026, 8, 28, 0, 5, 0, tzinfo=feed_session_watchdog.HCMC)
    with patch("feed_session_watchdog.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        main()

    out = capsys.readouterr().out
    assert "Ca 3 - Phiên 3" in out
    assert "Success (1): 10" in out
    assert state_file.exists()
    state_data = json.loads(state_file.read_text(encoding="utf-8"))
    assert "2026-08-27_ca3_phien3" in state_data["reported_sessions"]
