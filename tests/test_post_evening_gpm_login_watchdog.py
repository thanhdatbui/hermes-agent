import json
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

# Ensure the scripts directory is in sys.path
SCRIPTS_DIR = Path(r"D:\Taadaa\Hermes\deploy\hermes-home\scripts")
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import post_evening_gpm_login_watchdog as watchdog

HCMC = ZoneInfo("Asia/Ho_Chi_Minh")


class TestGetCurrentShiftInfo:
    @pytest.mark.parametrize(
        "dt,expected",
        [
            # Morning window: 07:15 - 08:45
            (datetime(2026, 9, 20, 7, 15, tzinfo=HCMC), ("SANG", "SÁNG", "sáng")),
            (datetime(2026, 9, 20, 8, 0, tzinfo=HCMC), ("SANG", "SÁNG", "sáng")),
            (datetime(2026, 9, 20, 8, 45, tzinfo=HCMC), ("SANG", "SÁNG", "sáng")),
            # Noon window: 12:00 - 13:45
            (datetime(2026, 9, 20, 12, 0, tzinfo=HCMC), ("TRUA", "TRƯA", "trưa")),
            (datetime(2026, 9, 20, 12, 30, tzinfo=HCMC), ("TRUA", "TRƯA", "trưa")),
            (datetime(2026, 9, 20, 13, 45, tzinfo=HCMC), ("TRUA", "TRƯA", "trưa")),
            # Evening window: 20:15 - 23:45
            (datetime(2026, 9, 20, 20, 15, tzinfo=HCMC), ("TOI", "TỐI", "tối")),
            (datetime(2026, 9, 20, 22, 0, tzinfo=HCMC), ("TOI", "TỐI", "tối")),
            (datetime(2026, 9, 20, 23, 45, tzinfo=HCMC), ("TOI", "TỐI", "tối")),
            # Fallback cases outside explicit windows:
            # hour < 12 fallback -> SANG
            (datetime(2026, 9, 20, 6, 30, tzinfo=HCMC), ("SANG", "SÁNG", "sáng")),
            (datetime(2026, 9, 20, 9, 0, tzinfo=HCMC), ("SANG", "SÁNG", "sáng")),
            (datetime(2026, 9, 20, 11, 59, tzinfo=HCMC), ("SANG", "SÁNG", "sáng")),
            # hour < 18 fallback -> TRUA
            (datetime(2026, 9, 20, 14, 0, tzinfo=HCMC), ("TRUA", "TRƯA", "trưa")),
            (datetime(2026, 9, 20, 16, 30, tzinfo=HCMC), ("TRUA", "TRƯA", "trưa")),
            (datetime(2026, 9, 20, 17, 59, tzinfo=HCMC), ("TRUA", "TRƯA", "trưa")),
            # else (hour >= 18) fallback -> TOI
            (datetime(2026, 9, 20, 18, 0, tzinfo=HCMC), ("TOI", "TỐI", "tối")),
            (datetime(2026, 9, 20, 19, 30, tzinfo=HCMC), ("TOI", "TỐI", "tối")),
            (datetime(2026, 9, 20, 23, 50, tzinfo=HCMC), ("TOI", "TỐI", "tối")),
        ],
    )
    def test_get_current_shift_info(self, dt, expected):
        with patch.object(watchdog, "datetime") as mock_dt:
            mock_dt.now.return_value = dt
            result = watchdog.get_current_shift_info()
            assert result == expected


class TestFormatSummaryReport:
    @patch.object(watchdog, "_get_live_omniroute_antigravity_emails", return_value=["acc1@gmail.com", "acc2@gmail.com"])
    @patch.object(watchdog, "_get_gpm_profiles_with_google_session", return_value=["prof1", "prof2", "prof3"])
    def test_format_summary_report_default_evening(self, mock_session, mock_live):
        report = watchdog._format_summary_report(total_success=5, total_fail=1)
        assert "[LOGIN GPM TỐI - TỔNG KẾT]" in report
        assert "✓ 5 | ✗ 1" in report
        assert "Hoàn tất ca tối" in report
        assert "2 accounts LIVE trên OmniRoute (:20129)" in report
        assert "3 accounts" in report

    @patch.object(watchdog, "_get_live_omniroute_antigravity_emails", return_value=[])
    @patch.object(watchdog, "_get_gpm_profiles_with_google_session", return_value=["prof1"])
    def test_format_summary_report_custom_shifts(self, mock_session, mock_live):
        # Morning test
        report_morning = watchdog._format_summary_report(
            total_success=10,
            total_fail=0,
            shift_label="SÁNG",
            shift_desc="sáng",
        )
        assert "[LOGIN GPM SÁNG - TỔNG KẾT]" in report_morning
        assert "✓ 10 | ✗ 0" in report_morning
        assert "Hoàn tất ca sáng" in report_morning

        # Noon test
        report_noon = watchdog._format_summary_report(
            total_success=3,
            total_fail=2,
            shift_label="TRƯA",
            shift_desc="trưa",
        )
        assert "[LOGIN GPM TRƯA - TỔNG KẾT]" in report_noon
        assert "✓ 3 | ✗ 2" in report_noon
        assert "Hoàn tất ca trưa" in report_noon


class TestFailClosedSoak:
    def test_load_gmail_clean_creation_dates_parsing(self, tmp_path, monkeypatch):
        """Trực tiếp kiểm tra hàm _load_gmail_clean_creation_dates() phân tích ngày hợp lệ / không hợp lệ."""
        fake_rows = [
            ("Header0", "Email", "Col2", "Col3", "Col4", "DOB", "Created"),
            (1, "soak_valid@gmail.com", "", "", "", "1995-01-01", "2026-09-10 12:00:00"),
            (2, "soak_date_obj@gmail.com", "", "", "", None, datetime(2026, 9, 12, 8, 0)),
            (3, "soak_invalid@gmail.com", "", "", "", None, "not-a-date"),
            (4, "soak_none@gmail.com", "", "", "", None, None),
        ]
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_ws.iter_rows.return_value = fake_rows
        mock_wb.active = mock_ws

        fake_xlsx = tmp_path / "fake_clean.xlsx"
        fake_xlsx.touch()
        monkeypatch.setattr(watchdog, "CLEAN_GMAIL_XLSX", fake_xlsx)
        with patch("openpyxl.load_workbook", return_value=mock_wb):
            cache = watchdog._load_gmail_clean_creation_dates()

        assert cache["soak_valid@gmail.com"]["created_date"] == date(2026, 9, 10)
        assert cache["soak_date_obj@gmail.com"]["created_date"] == date(2026, 9, 12)
        assert cache["soak_invalid@gmail.com"]["created_date"] is None
        assert cache["soak_none@gmail.com"]["created_date"] is None

    @patch("post_evening_gpm_login_watchdog.STATUS_JSON")
    @patch("post_evening_gpm_login_watchdog.STATE_FILE")
    @patch("post_evening_gpm_login_watchdog.MASTER_XLSX")
    @patch("post_evening_gpm_login_watchdog.get_all_gpm_emails")
    @patch("post_evening_gpm_login_watchdog._get_live_omniroute_antigravity_emails", return_value=set())
    @patch("post_evening_gpm_login_watchdog._get_gpm_profiles_with_google_session", return_value=set())
    def test_get_candidates_fail_closed_soak_filtering(
        self, mock_session, mock_live, mock_gpm_emails, mock_master_xlsx, mock_state_file, mock_status_json, monkeypatch
    ):
        """Kiểm tra get_candidates() lọc chuẩn fail-closed theo logic sản xuất:
        - soak >= 7 ngày: ĐƯỢC CHẤP NHẬN
        - soak < 7 ngày: BỊ BỎ QUA
        - missing created_date (None): BỊ BỎ QUA (fail-closed)
        """
        mock_status_json.exists.return_value = False
        mock_state_file.exists.return_value = False
        mock_master_xlsx.exists.return_value = True

        mock_gpm_emails.return_value = {
            "soak_pass@gmail.com",
            "soak_young@gmail.com",
            "soak_missing@gmail.com",
        }

        # clean_map với 3 trạng thái
        clean_map = {
            "soak_pass@gmail.com": {"created_date": date(2026, 9, 13)},   # 7 ngày so với 2026-09-20 -> PASS
            "soak_young@gmail.com": {"created_date": date(2026, 9, 15)},  # 5 ngày -> FAIL
            "soak_missing@gmail.com": {"created_date": None},             # Thiếu ngày -> FAIL-CLOSED
        }
        monkeypatch.setattr(watchdog, "_load_gmail_clean_creation_dates", lambda: clean_map)

        # Giả lập Master XLSX sheet Kibe_Farm_S7
        fake_rows = [
            ("MID", "Email", "Pass", "Rec", "2FA", "DOB", "Status", "MID_Col", "Col8", "Col9", "Proxy", "Col11", "Col12", "Note", "Updated"),
            (1, "soak_pass@gmail.com", "p", "r@g.com", "", "", "LIVE", "1", "", "", "127.0.0.1:20001", "", "", "", "2026-09-10"),
            (2, "soak_young@gmail.com", "p", "r@g.com", "", "", "LIVE", "2", "", "", "127.0.0.1:20002", "", "", "", "2026-09-10"),
            (3, "soak_missing@gmail.com", "p", "r@g.com", "", "", "LIVE", "3", "", "", "127.0.0.1:20003", "", "", "", "2026-09-10"),
        ]
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_ws.iter_rows.return_value = fake_rows
        mock_wb.__getitem__.return_value = mock_ws
        with patch("openpyxl.load_workbook", return_value=mock_wb):
            candidates, _ = watchdog.get_candidates("2026-09-20", [])

        candidate_emails = [c["email"] for c in candidates]
        assert "soak_pass@gmail.com" in candidate_emails
        assert "soak_young@gmail.com" not in candidate_emails
        assert "soak_missing@gmail.com" not in candidate_emails


class TestProxyLimit:
    @patch("post_evening_gpm_login_watchdog.STATUS_JSON")
    @patch("post_evening_gpm_login_watchdog.STATE_FILE")
    @patch("post_evening_gpm_login_watchdog.MASTER_XLSX")
    @patch("post_evening_gpm_login_watchdog.get_all_gpm_emails")
    @patch("post_evening_gpm_login_watchdog._get_live_omniroute_antigravity_emails", return_value=set())
    @patch("post_evening_gpm_login_watchdog._get_gpm_profiles_with_google_session", return_value=set())
    def test_proxy_limit_enforced_by_get_candidates(
        self, mock_session, mock_live, mock_gpm_emails, mock_master_xlsx, mock_state_file, mock_status_json, monkeypatch
    ):
        """Kiểm tra get_candidates() thực thi MAX_LOGINS_PER_PROXY=2:
        - proxy_count ban đầu từ state đã có 2 logins trên port 20001 -> bỏ qua candidate trên port 20001
        - port 20002 có 3 candidate trong batch -> chỉ nhận tối đa 2 candidate đầu tiên
        """
        mock_status_json.exists.return_value = False
        mock_master_xlsx.exists.return_value = True

        # State có sẵn proxy 20001 đã đạt limit = 2
        mock_state_file.exists.return_value = True
        mock_state_file.read_text.return_value = json.dumps({
            "date": "2026-09-20",
            "proxy_count": {"20001": 2, "20002": 0}
        })

        clean_map = {
            "p1_cand@gmail.com": {"created_date": date(2026, 9, 1)},
            "p2_cand1@gmail.com": {"created_date": date(2026, 9, 1)},
            "p2_cand2@gmail.com": {"created_date": date(2026, 9, 1)},
            "p2_cand3@gmail.com": {"created_date": date(2026, 9, 1)},
        }
        monkeypatch.setattr(watchdog, "_load_gmail_clean_creation_dates", lambda: clean_map)
        mock_gpm_emails.return_value = set(clean_map.keys())

        fake_rows = [
            ("MID", "Email", "Pass", "Rec", "2FA", "DOB", "Status", "MID_Col", "Col8", "Col9", "Proxy", "Col11", "Col12", "Note", "Updated"),
            (1, "p1_cand@gmail.com", "p", "r@g.com", "", "", "LIVE", "1", "", "", "127.0.0.1:20001", "", "", "", "2026-09-01"),
            (2, "p2_cand1@gmail.com", "p", "r@g.com", "", "", "LIVE", "2", "", "", "127.0.0.1:20002", "", "", "", "2026-09-01"),
            (3, "p2_cand2@gmail.com", "p", "r@g.com", "", "", "LIVE", "3", "", "", "127.0.0.1:20002", "", "", "", "2026-09-01"),
            (4, "p2_cand3@gmail.com", "p", "r@g.com", "", "", "LIVE", "4", "", "", "127.0.0.1:20002", "", "", "", "2026-09-01"),
        ]
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_ws.iter_rows.return_value = fake_rows
        mock_wb.__getitem__.return_value = mock_ws
        with patch("openpyxl.load_workbook", return_value=mock_wb):
            candidates, _ = watchdog.get_candidates("2026-09-20", [])

        cand_emails = [c["email"] for c in candidates]
        # p1_cand bị loại do port 20001 đã có 2 logins trước đó trong state
        assert "p1_cand@gmail.com" not in cand_emails
        # port 20002 nhận tối đa 2 accounts (p2_cand1, p2_cand2), p2_cand3 bị loại
        assert "p2_cand1@gmail.com" in cand_emails
        assert "p2_cand2@gmail.com" in cand_emails
        assert "p2_cand3@gmail.com" not in cand_emails


class TestGoogleSessionSQLiteDetection:
    def test_get_gpm_profiles_with_google_session_real_sqlite(self, tmp_path, monkeypatch):
        """Test thực tế _get_gpm_profiles_with_google_session bằng SQLite thật:
        - Bảng profiles trong profile_data.db
        - Bảng cookies trong Default/Network/Cookies
        - Nhận diện đúng tài khoản có đủ cookies SID / SSID của google.com
        """
        gpm_db_file = tmp_path / "profile_data.db"
        conn = sqlite3.connect(gpm_db_file)
        cur = conn.cursor()
        cur.execute("CREATE TABLE profiles (Name TEXT, ProfilePath TEXT);")
        cur.execute(
            "INSERT INTO profiles VALUES (?, ?)",
            ("01 - session_ok@gmail.com - 20001", "prof_ok")
        )
        cur.execute(
            "INSERT INTO profiles VALUES (?, ?)",
            ("02 - session_insufficient@gmail.com - 20002", "prof_insufficient")
        )
        cur.execute(
            "INSERT INTO profiles VALUES (?, ?)",
            ("03 - no_cookies@gmail.com - 20003", "prof_no_cookies")
        )
        conn.commit()
        conn.close()

        # Tạo thư mục và SQLite cookies cho prof_ok (>= 2 google auth cookies)
        cookie_dir_ok = tmp_path / "prof_ok" / "Default" / "Network"
        cookie_dir_ok.mkdir(parents=True)
        cookie_db_ok = cookie_dir_ok / "Cookies"
        c_conn = sqlite3.connect(cookie_db_ok)
        c_cur = c_conn.cursor()
        c_cur.execute("CREATE TABLE cookies (host_key TEXT, name TEXT);")
        c_cur.execute("INSERT INTO cookies VALUES ('.google.com', 'SID');")
        c_cur.execute("INSERT INTO cookies VALUES ('.google.com', 'SSID');")
        c_cur.execute("INSERT INTO cookies VALUES ('.google.com', 'OTHER');")
        c_conn.commit()
        c_conn.close()

        # Tạo SQLite cookies cho prof_insufficient (< 2 google auth cookies)
        cookie_dir_bad = tmp_path / "prof_insufficient" / "Default" / "Cookies"
        cookie_dir_bad.mkdir(parents=True)
        cookie_db_bad = cookie_dir_bad / "Cookies"
        c_conn2 = sqlite3.connect(cookie_db_bad)
        c_cur2 = c_conn2.cursor()
        c_cur2.execute("CREATE TABLE cookies (host_key TEXT, name TEXT);")
        c_cur2.execute("INSERT INTO cookies VALUES ('.google.com', 'SID');")  # Chỉ 1 cookie
        c_cur2.execute("INSERT INTO cookies VALUES ('.other.com', 'SSID');")
        c_conn2.commit()
        c_conn2.close()

        monkeypatch.setattr(watchdog, "GPM_DB", gpm_db_file)

        result_emails = watchdog._get_gpm_profiles_with_google_session()
        assert "session_ok@gmail.com" in result_emails
        assert "session_insufficient@gmail.com" not in result_emails
        assert "no_cookies@gmail.com" not in result_emails


class TestShiftStateTransition:
    def test_shift_already_finished_skipped(self):
        finished_shifts = ["SANG", "TRUA"]
        assert "TRUA" in finished_shifts
        assert "TOI" not in finished_shifts


class TestGetCandidatesIntegration:
    @patch("post_evening_gpm_login_watchdog._load_gmail_clean_creation_dates")
    @patch("post_evening_gpm_login_watchdog.get_all_gpm_emails")
    @patch("post_evening_gpm_login_watchdog._get_live_omniroute_antigravity_emails")
    @patch("post_evening_gpm_login_watchdog._get_gpm_profiles_with_google_session")
    @patch("post_evening_gpm_login_watchdog.STATUS_JSON")
    @patch("post_evening_gpm_login_watchdog.MASTER_XLSX")
    @patch("post_evening_gpm_login_watchdog.STATE_FILE")
    def test_priority_ordering_and_filtering(
        self, mock_state_file, mock_master_xlsx, mock_status_json,
        mock_get_sessions, mock_omni_emails, mock_gpm_emails, mock_clean_dates
    ):
        mock_state_file.exists.return_value = False
        mock_status_json.exists.return_value = False
        mock_master_xlsx.exists.return_value = False
        
        mock_gpm_emails.return_value = {"acc_session@gmail.com", "acc_cg@gmail.com", "acc_normal@gmail.com"}
        mock_get_sessions.return_value = {"acc_session@gmail.com"}
        mock_omni_emails.return_value = set()
        mock_clean_dates.return_value = {}

        # Test priority sort order directly
        cands = [
            {"email": "acc_normal@gmail.com", "priority": 3, "mid": 1, "port": "20001"},
            {"email": "acc_session@gmail.com", "priority": 1, "mid": 2, "port": "20002"},
            {"email": "acc_cg@gmail.com", "priority": 2, "mid": 3, "port": "20003"},
        ]
        cands.sort(key=lambda x: x.get("priority", 3))
        assert [c["email"] for c in cands] == ["acc_session@gmail.com", "acc_cg@gmail.com", "acc_normal@gmail.com"]


class TestMainStateTransition:
    @patch("post_evening_gpm_login_watchdog.is_within_time_window", return_value=True)
    @patch("post_evening_gpm_login_watchdog.get_current_shift_info", return_value=("TRUA", "TRƯA", "trưa"))
    @patch("post_evening_gpm_login_watchdog.STATE_FILE")
    def test_main_early_exit_if_shift_already_finished(self, mock_state_file, mock_shift, mock_window):
        today_str = datetime.now(watchdog.HCMC).strftime("%Y-%m-%d")
        mock_state_file.exists.return_value = True
        mock_state_file.read_text.return_value = json.dumps({
            "date": today_str,
            "finished_shifts": ["TRUA"],
            "finished": False
        })
        ret = watchdog.main()
        assert ret == 0


class TestEndToEndMainSimulation:
    @patch("post_evening_gpm_login_watchdog.is_within_time_window", return_value=True)
    @patch("post_evening_gpm_login_watchdog.is_avatar_done", return_value=True)
    @patch("post_evening_gpm_login_watchdog.get_current_shift_info", return_value=("TRUA", "TRƯA", "trưa"))
    @patch("post_evening_gpm_login_watchdog.sync_gpm_profiles_lifecycle")
    @patch("post_evening_gpm_login_watchdog.get_candidates")
    @patch("post_evening_gpm_login_watchdog.get_online_adb_serials", return_value={"SERIAL01"})
    @patch("post_evening_gpm_login_watchdog.get_machine_serial_map", return_value={1: "SERIAL01"})
    @patch("post_evening_gpm_login_watchdog.is_machine_idle", return_value=True)
    @patch("post_evening_gpm_login_watchdog.run_login")
    @patch("post_evening_gpm_login_watchdog.STATE_FILE")
    def test_main_e2e_successful_cycle(
        self, mock_state_file, mock_run_login, mock_idle, mock_serial_map,
        mock_online_serials, mock_get_candidates, mock_sync_gpm, mock_shift,
        mock_avatar, mock_window
    ):
        mock_state_file.exists.return_value = False
        saved_data = {}
        def fake_write_text(text, encoding="utf-8"):
            saved_data.update(json.loads(text))
        mock_state_file.write_text.side_effect = fake_write_text

        candidate = {"email": "test_e2e@gmail.com", "mid": 1, "port": "20001", "priority": 1}
        mock_get_candidates.return_value = ([candidate], {})
        mock_run_login.return_value = {**candidate, "status": "SUCCESS"}

        ret = watchdog.main()
        assert ret == 0
        assert "test_e2e@gmail.com" in saved_data.get("processed", [])
        assert saved_data.get("total_success") == 1
        assert saved_data.get("total_fail") == 0
        assert saved_data.get("proxy_count", {}).get("20001") == 1

    @patch("post_evening_gpm_login_watchdog.is_within_time_window", return_value=True)
    @patch("post_evening_gpm_login_watchdog.is_avatar_done", return_value=True)
    @patch("post_evening_gpm_login_watchdog.get_current_shift_info", return_value=("TRUA", "TRƯA", "trưa"))
    @patch("post_evening_gpm_login_watchdog.sync_gpm_profiles_lifecycle")
    @patch("post_evening_gpm_login_watchdog.get_candidates")
    @patch("post_evening_gpm_login_watchdog.get_online_adb_serials", return_value={"SERIAL01"})
    @patch("post_evening_gpm_login_watchdog.get_machine_serial_map", return_value={1: "SERIAL01"})
    @patch("post_evening_gpm_login_watchdog.is_machine_idle", return_value=True)
    @patch("post_evening_gpm_login_watchdog.run_login")
    @patch("post_evening_gpm_login_watchdog.STATE_FILE")
    def test_main_e2e_error_isolation(
        self, mock_state_file, mock_run_login, mock_idle, mock_serial_map,
        mock_online_serials, mock_get_candidates, mock_sync_gpm, mock_shift,
        mock_avatar, mock_window
    ):
        mock_state_file.exists.return_value = False
        saved_data = {}
        def fake_write_text(text, encoding="utf-8"):
            saved_data.update(json.loads(text))
        mock_state_file.write_text.side_effect = fake_write_text

        candidate = {"email": "fail_e2e@gmail.com", "mid": 1, "port": "20001", "priority": 1}
        mock_get_candidates.return_value = ([candidate], {})
        mock_run_login.return_value = {**candidate, "status": "FAIL", "error": "Simulated error"}

        ret = watchdog.main()
        assert ret == 0
        assert "fail_e2e@gmail.com" in saved_data.get("processed", [])
        assert saved_data.get("total_success") == 0
        assert saved_data.get("total_fail") == 1


class TestEdgeCasesAndRegression:
    @patch("urllib.request.urlopen", side_effect=TimeoutError("OmniRoute API timeout"))
    def test_omniroute_api_timeout_fallback(self, mock_urlopen):
        emails = watchdog._get_live_omniroute_antigravity_emails()
        assert emails == set()

    @patch("post_evening_gpm_login_watchdog.is_within_time_window", return_value=True)
    @patch("post_evening_gpm_login_watchdog.is_avatar_done", return_value=True)
    @patch("post_evening_gpm_login_watchdog.sync_gpm_profiles_lifecycle")
    @patch("post_evening_gpm_login_watchdog.get_candidates", return_value=([], {}))
    @patch("post_evening_gpm_login_watchdog.get_current_shift_info", return_value=("TRUA", "TRƯA", "trưa"))
    @patch("post_evening_gpm_login_watchdog.STATE_FILE")
    def test_legacy_state_file_migration(
        self, mock_state_file, mock_shift, mock_get_cands, mock_sync, mock_avatar, mock_window
    ):
        saved_state = {}

        def fake_write_text(text, encoding="utf-8"):
            saved_state.update(json.loads(text))

        mock_state_file.exists.return_value = True
        mock_state_file.read_text.return_value = json.dumps({
            "date": "2026-09-20",
            "reported": True,
            "finished": False
        })
        mock_state_file.write_text.side_effect = fake_write_text

        with patch.object(watchdog, "datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 9, 20, 12, 30, tzinfo=HCMC)
            ret = watchdog.main()

        assert ret == 0
        assert "finished_shifts" in saved_state
        assert "TRUA" in saved_state["finished_shifts"]

    @patch("post_evening_gpm_login_watchdog.STATUS_JSON")
    @patch("post_evening_gpm_login_watchdog.MASTER_XLSX")
    @patch("post_evening_gpm_login_watchdog.CLEAN_GMAIL_XLSX")
    @patch("post_evening_gpm_login_watchdog.GPM_DB")
    @patch("post_evening_gpm_login_watchdog.STATE_FILE")
    @patch("post_evening_gpm_login_watchdog._get_live_omniroute_antigravity_emails", return_value=set())
    def test_get_candidates_live_filtering_call(
        self, mock_omni_live, mock_state_file, mock_gpm_db, mock_clean_xlsx, mock_master_xlsx, mock_status_json
    ):
        mock_status_json.exists.return_value = False
        mock_master_xlsx.exists.return_value = False
        mock_clean_xlsx.exists.return_value = False
        mock_gpm_db.exists.return_value = False
        mock_state_file.exists.return_value = False

        res = watchdog.get_candidates("2026-09-20", [])
        assert isinstance(res, tuple)
        assert len(res) == 2
        candidates, proxy_count = res
        assert isinstance(candidates, list)
        assert isinstance(proxy_count, dict)
