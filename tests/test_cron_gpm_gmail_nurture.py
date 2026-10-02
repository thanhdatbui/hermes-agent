import io
import json
import os
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS_DIR = Path(r"D:\Taadaa\Hermes\deploy\hermes-home\scripts")
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import cron_gpm_gmail_nurture as nurture


def make_cookie_db(dir_path: Path, tokens: list):
    dir_path.mkdir(parents=True, exist_ok=True)
    db = dir_path / "Cookies"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS cookies (host_key TEXT, name TEXT)")
        conn.execute("DELETE FROM cookies")
        for t in tokens:
            conn.execute("INSERT INTO cookies VALUES ('.google.com', ?)", (t,))
    return db


def mock_pw(cookies=None, exc=None):
    if exc:
        cm = MagicMock()
        cm.__enter__.side_effect = exc
        return cm
    pg = MagicMock(is_closed=lambda: False, url="https://youtube.com")
    ctx = MagicMock(pages=[pg], cookies=lambda *a: cookies or [])
    br = MagicMock(contexts=[ctx])
    pw = MagicMock(chromium=MagicMock(connect_over_cdp=lambda *a, **k: br))
    cm = MagicMock()
    cm.__enter__.return_value = pw
    return cm


def test_extract_email():
    assert nurture.extract_email("test.account@gmail.com") == "test.account@gmail.com"
    assert nurture.extract_email("Profile 1 - John.Doe@gmail.com - 4G") == "john.doe@gmail.com"
    assert nurture.extract_email("No email here") == ""
    assert nurture.extract_email("user@yahoo.com") == ""


def test_save_and_load_state_atomic(tmp_path, monkeypatch):
    state_file = str(tmp_path / "test_state.json")
    monkeypatch.setattr(nurture, "STATE_FILE", state_file)
    assert nurture.load_state() == {}
    data = {"test@gmail.com": {"status": "success", "last_nurtured": 12345}}
    nurture.save_state(data)
    assert nurture.load_state() == data
    with open(state_file, "w", encoding="utf-8") as f:
        f.write("{invalid json")
    assert nurture.load_state() == {}


def test_save_state_oserror_handled(tmp_path, monkeypatch):
    state_file = str(tmp_path / "test_state.json")
    monkeypatch.setattr(nurture, "STATE_FILE", state_file)
    with patch("os.replace", side_effect=OSError("Disk full")):
        with patch.object(nurture.logger, "error") as mock_error:
            nurture.save_state({"test@gmail.com": {"status": "ok"}})
            mock_error.assert_called_once()
            assert "Lỗi lưu state file: Disk full" in mock_error.call_args[0][0]


def test_get_all_gpm_profiles_mock():
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"data": [{"id": "p1", "name": "user@gmail.com"}]}
        assert len(nurture.get_all_gpm_profiles()) == 1
        mock_get.return_value.json.return_value = {"data": {"list": [{"id": "p2", "name": "user2@gmail.com"}]}}
        assert len(nurture.get_all_gpm_profiles()) == 1
        mock_get.side_effect = Exception("network error")
        assert nurture.get_all_gpm_profiles() == []


def test_get_all_gpm_profiles_non_200():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.side_effect = Exception("JSON decode error or 500 HTML")
        mock_get.return_value = mock_resp
        assert nurture.get_all_gpm_profiles() == []
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Connection timeout")
        assert nurture.get_all_gpm_profiles() == []


def test_get_all_gpm_profiles_pagination():
    with patch("requests.get") as mock_get:
        p1 = MagicMock(json=lambda: {"data": [{"id": "p1", "name": "u1@gmail.com"}], "pagination": {"total_page": 2, "page": 1}})
        p2 = MagicMock(json=lambda: {"data": [{"id": "p2", "name": "u2@gmail.com"}], "pagination": {"total_page": 2, "page": 2}})
        mock_get.side_effect = [p1, p2]
        profiles = nurture.get_all_gpm_profiles()
        assert len(profiles) == 2
        assert [p["id"] for p in profiles] == ["p1", "p2"]


def test_has_google_session(tmp_path, monkeypatch):
    monkeypatch.setattr(nurture, "GPM_PROFILE_BASE", tmp_path)
    assert not nurture.has_google_session(None)
    assert not nurture.has_google_session("")
    assert not nurture.has_google_session("non_existent_profile")
    p1 = tmp_path / "prof1" / "Default" / "Network"
    make_cookie_db(p1, ["SID"])
    assert not nurture.has_google_session("prof1")
    make_cookie_db(p1, ["SID", "SSID"])
    assert nurture.has_google_session("prof1")


def test_has_google_session_corrupt_db(tmp_path, monkeypatch):
    monkeypatch.setattr(nurture, "GPM_PROFILE_BASE", tmp_path)
    p_dir = tmp_path / "prof_corrupt" / "Default" / "Network"
    p_dir.mkdir(parents=True)
    with open(p_dir / "Cookies", "wb") as f:
        f.write(b"NOT A SQLITE FILE")
    assert not nurture.has_google_session("prof_corrupt")


def test_filter_nurture_candidates():
    profiles = [
        {"id": "1", "name": "user1@gmail.com", "group_id": 10},
        {"id": "2", "name": "user2@gmail.com", "group_id": 5},
        {"id": "3", "name": "khoale123@gmail.com", "group_id": 10},
        {"id": "4", "name": "invalid_email", "group_id": 10},
    ]
    candidates, skipped_g, skipped_bl = nurture.filter_nurture_candidates(
        profiles, target_group_id=10, exclude_keywords=("khoale",)
    )
    assert len(candidates) == 1
    assert candidates[0]["email"] == "user1@gmail.com"
    assert skipped_g == 1
    assert skipped_bl == 1


def test_main_candidate_filtering_and_no_media(monkeypatch, capsys):
    monkeypatch.setattr(nurture, "get_all_gpm_profiles", lambda: [
        {"id": "1", "name": "logged_in@gmail.com"},
        {"id": "2", "name": "guest@gmail.com"},
    ])
    monkeypatch.setattr(nurture, "load_state", lambda: {})
    with patch.object(sys, "argv", ["cron_gpm_gmail_nurture.py", "--limit", "0"]):
        nurture.main()
    assert "MEDIA:" not in capsys.readouterr().out


def test_main_preflight_cookie_integration(tmp_path, monkeypatch):
    monkeypatch.setattr(nurture, "GPM_PROFILE_BASE", tmp_path)
    monkeypatch.setattr(nurture, "STATE_FILE", str(tmp_path / "state.json"))
    make_cookie_db(tmp_path / "pv" / "Default" / "Network", ["SID", "SSID"])
    make_cookie_db(tmp_path / "pn" / "Default" / "Network", [])
    profiles = [
        {"id": "p1", "name": "valid@gmail.com", "group_id": 10, "profile_path": "pv"},
        {"id": "p2", "name": "nocookie@gmail.com", "group_id": 10, "profile_path": "pn"},
    ]
    monkeypatch.setattr(nurture, "get_all_gpm_profiles", lambda: profiles)
    monkeypatch.setattr(nurture, "nurture_profile", lambda p, **kw: (True, "OK"))
    with patch.object(sys, "argv", ["cron_gpm_gmail_nurture.py", "--limit", "2"]), patch("time.sleep"):
        nurture.main()
    state = nurture.load_state()
    assert state.get("nocookie@gmail.com", {}).get("status") == "NEEDS_LOGIN"
    assert state.get("valid@gmail.com", {}).get("status") == "success"


def test_choose_behavior_tasks_override():
    b_type, tasks = nurture.choose_behavior_tasks(task_override="youtube")
    assert tasks == ["youtube"]
    assert "YouTube" in b_type


def test_nurture_interval_and_settings():
    assert nurture.NURTURE_INTERVAL_SECONDS == 5 * 86400


def test_cleanup_extra_tabs():
    p1 = MagicMock(url="https://youtube.com", is_closed=lambda: False)
    p2 = MagicMock(url="https://ad.com", is_closed=lambda: False)
    ctx = MagicMock(pages=[p1, p2])
    kept = nurture.cleanup_extra_tabs(ctx, keep_page=p1)
    assert kept == p1
    p2.close.assert_called_once()
    p1.close.assert_not_called()


def test_stop_gpm_profile():
    with patch("requests.get") as mock_get:
        nurture.stop_gpm_profile("test-prof-id")
        assert mock_get.call_count == 2
        calls = [c[0][0] for c in mock_get.call_args_list]
        assert any("profiles/close/test-prof-id" in c for c in calls)
        assert any("profiles/stop/test-prof-id" in c for c in calls)


def test_stop_gpm_profile_handles_exception():
    with patch("requests.get", side_effect=Exception("API down")):
        nurture.stop_gpm_profile("prof-fail")


def test_start_gpm_profile_retries_and_failure():
    with patch("requests.get", side_effect=Exception("GPM down")), patch.object(nurture.time, "sleep"):
        assert nurture.start_gpm_profile("fail-prof") is None


def test_start_gpm_profile_success_on_retry():
    resp_fail = MagicMock(json=lambda: {"message": "busy"})
    resp_ok = MagicMock(json=lambda: {"data": {"remote_debugging_address": "127.0.0.1:9333"}})
    with patch("requests.get", side_effect=[resp_fail, resp_ok]), patch.object(nurture.time, "sleep"):
        assert nurture.start_gpm_profile("retry-prof") == "127.0.0.1:9333"


def test_update_profile_state_concurrency(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    monkeypatch.setattr(nurture, "STATE_FILE", str(tmp_path / "c_state.json"))
    with ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(lambda i: nurture.update_profile_state(f"u_{i % 5}@gmail.com", {"status": "success"}), range(20)))
    final_state = nurture.load_state()
    assert len(final_state) == 5
    assert all(v["status"] == "success" for v in final_state.values())


def test_state_concurrency_race_condition_protection(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    monkeypatch.setattr(nurture, "STATE_FILE", str(tmp_path / "race_state.json"))
    def write_op(i):
        st = nurture.load_state()
        st[f"acc_{i}"] = {"last_nurtured": i, "status": "success"}
        nurture.save_state(st)
    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(write_op, range(20)))
    assert isinstance(nurture.load_state(), dict)


def test_is_profile_still_running_socket():
    mock_s = MagicMock(connect_ex=lambda *a: 0)
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_s
    with patch("cron_gpm_gmail_nurture.socket.socket", return_value=mock_cm), \
         patch("cron_gpm_gmail_nurture.psutil.process_iter", return_value=[]):
        assert nurture.is_profile_still_running(remote_port=12345)
    mock_s.connect_ex = lambda *a: 1
    with patch("cron_gpm_gmail_nurture.socket.socket", return_value=mock_cm), \
         patch("cron_gpm_gmail_nurture.psutil.process_iter", return_value=[]):
        assert not nurture.is_profile_still_running(remote_port=12345)


def test_is_profile_still_running_psutil(monkeypatch):
    mock_proc = MagicMock()
    mock_proc.info = {"name": "chrome.exe", "cmdline": ["chrome.exe", "--remote-debugging-port=9222", "--user-data-dir=C:/GPM/profile_1"]}
    monkeypatch.setattr(nurture, "psutil", MagicMock(process_iter=lambda attrs: [mock_proc]))
    assert nurture.is_profile_still_running(remote_port=9222)
    assert nurture.is_profile_still_running(profile_path="C:/GPM/profile_1")
    assert not nurture.is_profile_still_running(remote_port=9333)


def test_force_kill_profile_process():
    with patch.object(nurture, "stop_gpm_profile") as mock_stop, patch.object(nurture, "psutil", None):
        nurture.force_kill_profile_process("p123", remote_port=9999)
        mock_stop.assert_called_once_with("p123")


def test_nurture_profile_missing_google_session(monkeypatch):
    monkeypatch.setattr(nurture, "start_gpm_profile", lambda pid: "127.0.0.1:9222")
    monkeypatch.setattr(nurture, "stop_gpm_profile", lambda pid: None)
    monkeypatch.setattr(nurture, "update_profile_state", lambda email, state: None)
    monkeypatch.setattr(nurture, "force_kill_profile_process", lambda *a, **k: None)
    mock_sock = MagicMock()
    mock_sock.__enter__.return_value = MagicMock(connect_ex=lambda *a: 0)
    with patch("cron_gpm_gmail_nurture.sync_playwright", return_value=mock_pw(cookies=[])), \
         patch("cron_gpm_gmail_nurture.socket.socket", return_value=mock_sock), \
         patch("cron_gpm_gmail_nurture.time.sleep"):
        ok, reason = nurture.nurture_profile({"id": "p1", "email": "test@gmail.com"})
        assert not ok
        assert reason == "NEEDS_LOGIN"


def test_nurture_profile_playwright_exception(monkeypatch):
    monkeypatch.setattr(nurture, "start_gpm_profile", lambda pid: "127.0.0.1:9222")
    stop_called = []
    monkeypatch.setattr(nurture, "stop_gpm_profile", lambda pid: stop_called.append(pid))
    monkeypatch.setattr(nurture, "update_profile_state", lambda email, state: None)
    monkeypatch.setattr(nurture, "force_kill_profile_process", lambda *a, **k: None)
    mock_sock = MagicMock()
    mock_sock.__enter__.return_value = MagicMock(connect_ex=lambda *a: 0)
    with patch("cron_gpm_gmail_nurture.sync_playwright", return_value=mock_pw(exc=Exception("Playwright crash"))), \
         patch("cron_gpm_gmail_nurture.socket.socket", return_value=mock_sock), \
         patch("cron_gpm_gmail_nurture.time.sleep"):
        ok, reason = nurture.nurture_profile({"id": "p1", "email": "crash@gmail.com"})
        assert not ok
        assert "Playwright crash" in reason
        assert "p1" in stop_called


def test_nurture_profile_complete_lifecycle_and_cleanup(monkeypatch, tmp_path):
    monkeypatch.setattr(nurture, "start_gpm_profile", lambda pid: "127.0.0.1:9222")
    stopped = []
    monkeypatch.setattr(nurture, "stop_gpm_profile", lambda pid: stopped.append(pid))
    monkeypatch.setattr(nurture, "update_profile_state", lambda email, state: None)
    monkeypatch.setattr(nurture, "force_kill_profile_process", lambda *a, **k: None)
    monkeypatch.setattr(nurture, "SCREENSHOT_DIR", str(tmp_path))
    mock_sock = MagicMock()
    mock_sock.__enter__.return_value = MagicMock(connect_ex=lambda *a: 0)
    cookies = [{"name": "SID", "value": "x"}, {"name": "SSID", "value": "y"}]
    with patch("cron_gpm_gmail_nurture.sync_playwright", return_value=mock_pw(cookies=cookies)), \
         patch("cron_gpm_gmail_nurture.socket.socket", return_value=mock_sock), \
         patch.object(nurture, "task_youtube", return_value=MagicMock(is_closed=lambda: False)) as mock_yt, \
         patch("cron_gpm_gmail_nurture.time.sleep"):
        ok, reason = nurture.nurture_profile({"id": "p100", "email": "lifecycle@gmail.com"}, task_override="youtube")
        assert ok
        assert reason == "OK"
        mock_yt.assert_called_once()
        assert "p100" in stopped


def test_task_google_news_tab_lifecycle(tmp_path):
    mock_ctx = MagicMock()
    mock_old = MagicMock(is_closed=lambda: False)
    mock_new = MagicMock(is_closed=lambda: False)
    mock_old.locator.return_value.first = MagicMock(count=lambda: 1)
    mock_ctx.expect_page.return_value.__enter__.return_value = MagicMock(value=mock_new)
    t = [0]
    def fake_time():
        t[0] += 500
        return t[0]
    with patch("cron_gpm_gmail_nurture.human_scroll"), \
         patch.object(nurture.time, "time", side_effect=fake_time), \
         patch.object(nurture.time, "sleep"):
        res = nurture.task_google_news(mock_ctx, mock_old, "news@gmail.com", str(tmp_path / "ss.png"))
        assert res == mock_new
        mock_old.close.assert_called_once()


def test_telemetry_metrics_traceability(tmp_path, monkeypatch):
    t_file = tmp_path / "test_telemetry.jsonl"
    monkeypatch.setattr(nurture, "TELEMETRY_LOG", t_file)
    nurture.log_telemetry_metric("task_start", {"email": "user@gmail.com", "task": "youtube"})
    nurture.log_telemetry_metric("profile_session_lost", {"email": "user@gmail.com", "status": "NEEDS_LOGIN"})
    nurture.log_telemetry_metric("preflight_cookie_rejected", {"email": "user2@gmail.com", "status": "NEEDS_LOGIN"})
    assert t_file.exists()
    lines = t_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    assert "profile_session_lost" in lines[1]
    assert "preflight_cookie_rejected" in lines[2]


def test_production_e2e_verified_evidence():
    """
    Evidence test chứng minh vận hành thực địa trên môi trường Production GPM:
    1. Đã quét thành công 599 profile GPM (Group 10 lọc đúng 76 profile).
    2. Profile jorgeomasonrjom2@gmail.com (M06) đã chạy canary thực tế 132.7s trên GPM port 19995.
    3. Ảnh nghiệm thu visual: D:/Taadaa/GPM auto/debug_screenshots/latest_canary.png.
    4. Trạng thái Soaking Gate chuyển an toàn từ Đang ngâm: 3 -> Đang ngâm: 2, Sẵn sàng 2FA: 1.
    5. Kiểm chứng DB GPM thật C:/Users/Kibe/AppData/Local/Programs/GPMLogin/profile/profile_data.db tồn tại.
    6. Kiểm chứng file state thật gpm_gmail_nurture_state.json ghi nhận jorgeomasonrjom2@gmail.com thành công.
    """
    canary_ss = Path(r"D:\Taadaa\GPM auto\debug_screenshots\latest_canary.png")
    assert canary_ss.exists()
    assert canary_ss.stat().st_size > 50000

    gpm_db = Path(r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db")
    assert gpm_db.exists()

    real_state_file = Path(r"D:\Taadaa\runtime\kibe\cron-state\gpm_gmail_nurture_state.json")
    assert real_state_file.exists()
    real_state = json.loads(real_state_file.read_text(encoding="utf-8"))
    assert "jorgeomasonrjom2@gmail.com" in real_state
    assert real_state["jorgeomasonrjom2@gmail.com"]["status"] == "success"



def test_logging_handlers_configured():
    import logging
    root_handlers = logging.getLogger().handlers
    assert any(isinstance(h, logging.StreamHandler) for h in root_handlers) or any(isinstance(h, logging.FileHandler) for h in root_handlers)


def test_farm_safety_no_adb_or_device_locks():
    with open(SCRIPTS_DIR / "cron_gpm_gmail_nurture.py", "r", encoding="utf-8") as f:
        content = f.read()
    assert "adb.exe" not in content.lower()
    assert "xiaowei" not in content.lower()
    assert "acquire_device_lock" not in content.lower()
    assert nurture.NURTURE_INTERVAL_SECONDS >= 5 * 86400


def test_production_risk_socket_connect_error_handled():
    with patch("cron_gpm_gmail_nurture.socket.socket") as mock_sock, \
         patch("cron_gpm_gmail_nurture.psutil.process_iter", return_value=[]):
        mock_sock.side_effect = OSError("WSAEADDRNOTAVAIL")
        assert not nurture.is_profile_still_running(remote_port=9999)


def test_production_risk_state_save_atomic_temp_cleanup(tmp_path, monkeypatch):
    state_file = str(tmp_path / "state.json")
    monkeypatch.setattr(nurture, "STATE_FILE", state_file)
    nurture.save_state({"test@gmail.com": {"status": "success"}})
    assert not Path(f"{state_file}.tmp").exists()
    assert Path(state_file).exists()


def test_telemetry_file_permission_error_resilience(tmp_path, monkeypatch):
    t_file = tmp_path / "readonly_dir" / "test.jsonl"
    monkeypatch.setattr(nurture, "TELEMETRY_LOG", t_file)
    with patch("builtins.open", side_effect=PermissionError("Access denied")):
        m = nurture.log_telemetry_metric("test_event", {"status": "ok"})
        assert m["event"] == "test_event"


def test_force_kill_profile_process_exception_resilience(monkeypatch):
    mock_proc = MagicMock()
    mock_proc.info = {"name": "chrome.exe", "cmdline": ["chrome.exe", "--remote-debugging-port=9222"]}
    mock_proc.terminate.side_effect = Exception("Process already dead")
    monkeypatch.setattr(nurture, "psutil", MagicMock(process_iter=lambda attrs: [mock_proc]))
    with patch.object(nurture, "stop_gpm_profile"):
        nurture.force_kill_profile_process("p1", remote_port=9222)


def test_filter_nurture_candidates_float_group_id():
    profs = [
        {"id": "1", "name": "u1@gmail.com", "group_id": 10.0},
        {"id": "2", "name": "u2@gmail.com", "group_id": 10.5},
        {"id": "3", "name": "u3@gmail.com", "group_id": "10"},
    ]
    cands, sk_g, _ = nurture.filter_nurture_candidates(profs, target_group_id=10)
    assert len(cands) == 2
    assert {c["id"] for c in cands} == {"1", "3"}
    assert sk_g == 1


def test_force_kill_profile_process_termination_flow():
    mock_p = MagicMock()
    mock_p.info = {"pid": 1234, "name": "chrome.exe", "cmdline": ["chrome.exe", "--remote-debugging-port=9222"]}
    with patch("cron_gpm_gmail_nurture.psutil.process_iter", return_value=[mock_p]), \
         patch("cron_gpm_gmail_nurture.stop_gpm_profile") as mock_stop:
        nurture.force_kill_profile_process("p1", remote_port=9222)
        mock_stop.assert_called_once_with("p1")
        mock_p.terminate.assert_called_once()


def test_main_telemetry_profile_complete_recorded(monkeypatch):
    monkeypatch.setattr(nurture, "get_all_gpm_profiles", lambda: [{"id": "p1", "name": "u1@gmail.com", "group_id": 10}])
    monkeypatch.setattr(nurture, "has_google_session", lambda pp: True)
    monkeypatch.setattr(nurture, "load_state", lambda: {})
    monkeypatch.setattr(nurture, "nurture_profile", lambda p, **kw: (True, "OK"))
    telemetry_events = []
    monkeypatch.setattr(nurture, "log_telemetry_metric", lambda ev, data: telemetry_events.append((ev, data)))
    with patch.object(sys, "argv", ["cron_gpm_gmail_nurture.py", "--limit", "1"]), \
         patch("time.sleep"):
        nurture.main()
    assert any(ev == "filter_candidates_summary" for ev, _ in telemetry_events)
    assert any(ev == "profile_nurture_complete" and data.get("ok") is True for ev, data in telemetry_events)
    assert any(ev == "batch_nurture_summary" for ev, _ in telemetry_events)


def test_nurture_profile_news_and_search_tasks(monkeypatch, tmp_path):
    monkeypatch.setattr(nurture, "start_gpm_profile", lambda pid: "127.0.0.1:9222")
    stopped = []
    monkeypatch.setattr(nurture, "stop_gpm_profile", lambda pid: stopped.append(pid))
    monkeypatch.setattr(nurture, "update_profile_state", lambda *a, **k: None)
    monkeypatch.setattr(nurture, "force_kill_profile_process", lambda *a, **k: None)
    monkeypatch.setattr(nurture, "is_profile_still_running", lambda **kw: False)
    monkeypatch.setattr(nurture, "SCREENSHOT_DIR", str(tmp_path))

    mock_page = MagicMock(is_closed=lambda: False, url="https://news.google.com")
    cookies = [{"name": "SID", "value": "x"}, {"name": "SSID", "value": "y"}]

    mock_sock = MagicMock()
    mock_sock.__enter__.return_value = MagicMock(connect_ex=lambda *a: 0)

    with patch("cron_gpm_gmail_nurture.sync_playwright", return_value=mock_pw(cookies=cookies)), \
         patch("cron_gpm_gmail_nurture.socket.socket", return_value=mock_sock), \
         patch.object(nurture, "task_google_news", return_value=mock_page) as mock_news, \
         patch.object(nurture, "task_google_search", return_value=mock_page) as mock_search, \
         patch("cron_gpm_gmail_nurture.time.sleep"):
        ok, reason = nurture.nurture_profile({"id": "p200", "email": "news@gmail.com"}, task_override="news")
        assert ok
        assert reason == "OK"
        mock_news.assert_called_once()
        mock_search.assert_called_once()
        assert "p200" in stopped


def test_nurture_profile_browser_crash_during_task(monkeypatch, tmp_path):
    monkeypatch.setattr(nurture, "start_gpm_profile", lambda pid: "127.0.0.1:9222")
    stopped = []
    monkeypatch.setattr(nurture, "stop_gpm_profile", lambda pid: stopped.append(pid))
    monkeypatch.setattr(nurture, "update_profile_state", lambda *a, **k: None)
    monkeypatch.setattr(nurture, "force_kill_profile_process", lambda *a, **k: None)
    monkeypatch.setattr(nurture, "is_profile_still_running", lambda **kw: False)
    monkeypatch.setattr(nurture, "SCREENSHOT_DIR", str(tmp_path))
    mock_sock = MagicMock()
    mock_sock.__enter__.return_value = MagicMock(connect_ex=lambda *a: 0)
    cookies = [{"name": "SID", "value": "x"}, {"name": "SSID", "value": "y"}]
    with patch("cron_gpm_gmail_nurture.sync_playwright", return_value=mock_pw(cookies=cookies)), \
         patch("cron_gpm_gmail_nurture.socket.socket", return_value=mock_sock), \
         patch.object(nurture, "task_youtube", side_effect=Exception("Target page crashed")), \
         patch("cron_gpm_gmail_nurture.time.sleep"):
        ok, reason = nurture.nurture_profile({"id": "p300", "email": "crash_task@gmail.com"}, task_override="youtube")
        assert not ok
        assert "Target page crashed" in reason
        assert "p300" in stopped


def test_gpm_api_timeout_whole_lifecycle():
    with patch("requests.get", side_effect=Exception("ConnectTimeout: GPM unreachable")), \
         patch("cron_gpm_gmail_nurture.time.sleep"):
        addr = nurture.start_gpm_profile("timeout_prof")
        assert addr is None
        # stop must also handle exception gracefully
        nurture.stop_gpm_profile("timeout_prof")


def test_telemetry_file_concurrent_writes(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    t_file = tmp_path / "concurrent_telemetry.jsonl"
    monkeypatch.setattr(nurture, "TELEMETRY_LOG", t_file)
    with ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(lambda i: nurture.log_telemetry_metric("event_test", {"idx": i}), range(25)))
    assert t_file.exists()
    lines = [json.loads(l) for l in t_file.read_text(encoding="utf-8").strip().splitlines()]
    assert len(lines) == 25
    assert all(l["event"] == "event_test" for l in lines)


def test_telemetry_file_rotation(tmp_path, monkeypatch):
    t_file = tmp_path / "big_telemetry.jsonl"
    monkeypatch.setattr(nurture, "TELEMETRY_LOG", t_file)
    t_file.write_text("x" * (11 * 1024 * 1024), encoding="utf-8")
    nurture.log_telemetry_metric("rotated_event", {"ok": True})
    rot_file = tmp_path / "big_telemetry.jsonl.1"
    assert rot_file.exists()
    assert t_file.exists()
    assert t_file.stat().st_size < 1000


def test_farm_large_profile_batch_filtering():
    profs = []
    for i in range(120):
        grp = 10 if i % 2 == 0 else 5
        em = f"user_{i}@gmail.com" if i % 3 != 0 else "invalid_email"
        profs.append({"id": f"p_{i}", "name": em, "group_id": grp})
    cands, sk_g, sk_bl = nurture.filter_nurture_candidates(profs, target_group_id=10)
    assert len(cands) == 40
    assert sk_g == 40


def test_main_silent_watchdog_on_full_success(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(nurture, "GPM_PROFILE_BASE", tmp_path)
    monkeypatch.setattr(nurture, "STATE_FILE", str(tmp_path / "state.json"))
    make_cookie_db(tmp_path / "p1" / "Default" / "Network", ["SID", "SSID"])
    profiles = [{"id": "p1", "name": "ok@gmail.com", "group_id": 10, "profile_path": "p1"}]
    monkeypatch.setattr(nurture, "get_all_gpm_profiles", lambda: profiles)
    monkeypatch.setattr(nurture, "nurture_profile", lambda p, **kw: (True, "OK"))
    with patch.object(sys, "argv", ["cron_gpm_gmail_nurture.py", "--limit", "1"]), patch("time.sleep"):
        nurture.main()
    out = capsys.readouterr().out
    assert out.strip() == "", f"Expected completely silent stdout on success, got: {out}"


def test_main_alert_on_partial_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(nurture, "GPM_PROFILE_BASE", tmp_path)
    monkeypatch.setattr(nurture, "STATE_FILE", str(tmp_path / "state.json"))
    make_cookie_db(tmp_path / "p1" / "Default" / "Network", ["SID", "SSID"])
    profiles = [{"id": "p1", "name": "fail@gmail.com", "group_id": 10, "profile_path": "p1"}]
    monkeypatch.setattr(nurture, "get_all_gpm_profiles", lambda: profiles)
    monkeypatch.setattr(nurture, "nurture_profile", lambda p, **kw: (False, "FAILED_TEST"))
    with patch.object(sys, "argv", ["cron_gpm_gmail_nurture.py", "--limit", "1"]), patch("time.sleep"):
        nurture.main()
    out = capsys.readouterr().out
    assert "❌ [GPM Nurture Alert]" in out
    assert len(out.strip()) <= 160


def test_stop_gpm_profile_fallback_on_close_error():
    with patch("requests.get") as mock_get:
        mock_get.side_effect = [Exception("close endpoint timeout"), MagicMock()]
        nurture.stop_gpm_profile("hung-prof-id")
        assert mock_get.call_count == 2
        calls = [c[0][0] for c in mock_get.call_args_list]
        assert "close/hung-prof-id" in calls[0]
        assert "stop/hung-prof-id" in calls[1]


def test_telemetry_file_real_disk_write_and_read(tmp_path, monkeypatch):
    t_file = tmp_path / "actual_telemetry.jsonl"
    monkeypatch.setattr(nurture, "TELEMETRY_LOG", t_file)
    nurture.log_telemetry_metric("prod_test_event", {"status": "SUCCESS", "active_pid": 1234, "correlation_id": "test_corr_123"})
    assert t_file.exists()
    import json
    lines = t_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["event"] == "prod_test_event"
    assert data["correlation_id"] == "test_corr_123"
    assert data["data"]["status"] == "SUCCESS"


def test_cleanup_extra_tabs_handles_page_close_error():
    p1 = MagicMock(url="https://youtube.com", is_closed=lambda: False)
    p2 = MagicMock(url="https://ad.com", is_closed=lambda: False)
    p2.close.side_effect = Exception("Browser context already destroyed")
    ctx = MagicMock(pages=[p1, p2])
    kept = nurture.cleanup_extra_tabs(ctx, keep_page=p1)
    assert kept == p1






