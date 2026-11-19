# === Step 1: Unit Tests for Hourly Gmail Watchdog ===
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "deploy" / "hermes-home" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import hourly_gmail_reg_watchdog as wd


class TestHourlyGmailReg:
    def test_safe_window(self):
        assert wd.is_safe_window(datetime(2026, 1, 1, 4, 0)) is False
        assert wd.is_safe_window(datetime(2026, 1, 1, 9, 30)) is False
        assert wd.is_safe_window(datetime(2026, 1, 1, 11, 36)) is True
        assert wd.is_safe_window(datetime(2026, 1, 1, 12, 0)) is False
        assert wd.is_safe_window(datetime(2026, 1, 1, 21, 30)) is False
        assert wd.is_safe_window(datetime(2026, 1, 1, 22, 0)) is True

    def test_candidate_selection_and_cooldown(self, tmp_path):
        db = tmp_path / "farm_master.db"
        conn = sqlite3.connect(db)
        conn.executescript(
            """
            CREATE TABLE machines (machine_id TEXT, owner TEXT, proxy_endpoint TEXT,
                                   device_serial TEXT, source TEXT, run_id TEXT);
            CREATE TABLE mailboxes (email TEXT, owner TEXT, machine_id INTEGER, created_at TEXT);
            INSERT INTO machines VALUES ('1', 'Kibe', 'http://u:p@proxy-a:1001', '', '', '');
            INSERT INTO machines VALUES ('2', 'Kibe', 'proxy-b:1002', '', '', '');
            INSERT INTO machines VALUES ('3', 'Admin', 'proxy-c:1003', '', '', '');
            INSERT INTO machines VALUES ('4', 'Admin', 'proxy-d:1004', '', '', '');
            INSERT INTO mailboxes VALUES ('old@gmail.com', 'Kibe', 1, '2026-01-01T00:00:00');
            INSERT INTO mailboxes VALUES ('recent@gmail.com', 'Kibe', 2, '2026-01-07T00:00:00');
            """
        )
        conn.commit()
        conn.close()
        now = datetime(2026, 1, 10, 12, 0)
        candidates = wd.load_candidates(db, now=now, p0_machine_ids=set(), idle_checker=lambda mid: True)
        assert [c["machine_id"] for c in candidates] == [1, 3, 4]
        assert all(c["machine_id"] != 2 for c in candidates)

    def test_distinct_proxy_per_farm(self):
        candidates = [
            {"machine_id": 1, "farm": "Kibe", "proxy_endpoint": "http://a:1"},
            {"machine_id": 2, "farm": "Kibe", "proxy_endpoint": "a:1"},
            {"machine_id": 3, "farm": "Kibe", "proxy_endpoint": "b:2"},
            {"machine_id": 4, "farm": "Admin", "proxy_endpoint": "a:1"},
            {"machine_id": 5, "farm": "Admin", "proxy_endpoint": "b:2"},
        ]
        selected = wd.select_distinct_proxy_candidates(candidates, per_farm=2)
        assert [c["machine_id"] for c in selected] == [1, 3, 4, 5]

    def test_p0_group_one_and_idle_check(self, tmp_path):
        gpm = tmp_path / "profile_data.db"
        conn = sqlite3.connect(gpm)
        conn.execute("CREATE TABLE Profiles (Name TEXT, GroupId INTEGER)")
        conn.execute("INSERT INTO Profiles VALUES ('M07 - needs-login@gmail.com', 1)")
        conn.execute("INSERT INTO Profiles VALUES ('M08 - normal@gmail.com', 2)")
        conn.commit()
        conn.close()
        assert wd.p0_machine_ids(gpm) == {7}

        lock_dir = tmp_path / "locks"
        codex_dir = tmp_path / "codex-locks"
        lock_dir.mkdir()
        assert wd.is_machine_idle(7, lock_dirs=(lock_dir, codex_dir), next_slot_gap=60)
        (lock_dir / "machine_7.lock.json").write_text("{}", encoding="utf-8")
        assert not wd.is_machine_idle(7, lock_dirs=(lock_dir, codex_dir), next_slot_gap=60)
        assert not wd.is_machine_idle(8, lock_dirs=(lock_dir, codex_dir), next_slot_gap=44)

    def test_daily_report_format(self):
        state = {
            "runs": [
                {"farm": "Kibe", "status": "success", "machine_id": 1,
                 "timestamp": "2026-01-10T07:00:00"},
                {"farm": "Admin", "status": "failed", "machine_id": 201,
                 "timestamp": "2026-01-10T07:30:00"},
            ]
        }
        report = wd.format_daily_report(state, now=datetime(2026, 1, 10, 8, 0))
        assert "GMAIL REG" in report
        assert "Kibe" in report and "Admin" in report
        assert "Thành công: 1" in report
        assert "Thất bại: 1" in report

    def test_main_is_silent_in_blocked_window(self, tmp_path, capsys):
        with patch.object(wd, "STATE_FILE", tmp_path / "state.json"), \
             patch.object(wd, "now_local", return_value=datetime(2026, 1, 1, 5, 30)), \
             patch.object(wd, "is_feed_runner_active", return_value=False):
            assert wd.main([]) == 0
        assert capsys.readouterr().out == ""

    def test_report_only_sends_telegram_without_stdout(self, tmp_path, capsys):
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"runs": []}), encoding="utf-8")
        with patch.object(wd, "STATE_FILE", state_file), \
             patch.object(wd, "_send_telegram_text") as send:
            assert wd.main(["--report-only"]) == 0
        send.assert_called_once()
        assert send.call_args.args[0] == wd.GMAIL_REPORT_CHAT_ID
        assert capsys.readouterr().out == ""
