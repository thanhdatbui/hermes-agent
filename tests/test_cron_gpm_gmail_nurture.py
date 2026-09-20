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

    loaded = nurture.load_state()
    assert loaded == data

    # Test corrupt state file
    with open(state_file, "w", encoding="utf-8") as f:
        f.write("{invalid json")
    assert nurture.load_state() == {}


def test_get_all_gpm_profiles_mock():
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"data": [{"id": "p1", "name": "user@gmail.com"}]}
        profiles = nurture.get_all_gpm_profiles()
        assert len(profiles) == 1
        assert profiles[0]["id"] == "p1"

        mock_get.return_value.json.return_value = {"data": {"list": [{"id": "p2", "name": "user2@gmail.com"}]}}
        profiles2 = nurture.get_all_gpm_profiles()
        assert len(profiles2) == 1
        assert profiles2[0]["id"] == "p2"

        mock_get.side_effect = Exception("network error")
        assert nurture.get_all_gpm_profiles() == []


def test_get_emails_with_session(tmp_path, monkeypatch):
    db_path = tmp_path / "profile_data.db"
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("CREATE TABLE profiles (Name TEXT, ProfilePath TEXT);")
    cur.execute("INSERT INTO profiles VALUES ('Acc1 - live@gmail.com', 'prof1');")
    cur.execute("INSERT INTO profiles VALUES ('Acc2 - no_session@gmail.com', 'prof2');")
    conn.commit()
    conn.close()

    prof1_cookies = tmp_path / "prof1" / "Default" / "Network" / "Cookies"
    prof1_cookies.parent.mkdir(parents=True)
    c1 = sqlite3.connect(str(prof1_cookies))
    c1.execute("CREATE TABLE cookies (host_key TEXT, name TEXT);")
    c1.execute("INSERT INTO cookies VALUES ('.google.com', 'SID');")
    c1.execute("INSERT INTO cookies VALUES ('.google.com', 'SSID');")
    c1.commit()
    c1.close()

    prof2_cookies = tmp_path / "prof2" / "Default" / "Network" / "Cookies"
    prof2_cookies.parent.mkdir(parents=True)
    c2 = sqlite3.connect(str(prof2_cookies))
    c2.execute("CREATE TABLE cookies (host_key TEXT, name TEXT);")
    c2.execute("INSERT INTO cookies VALUES ('.google.com', 'OTHER');")
    c2.commit()
    c2.close()

    monkeypatch.setattr(nurture, "GPM_DB", db_path)
    sessions = nurture.get_emails_with_session()
    assert "live@gmail.com" in sessions
    assert "no_session@gmail.com" not in sessions


def test_main_candidate_filtering_and_no_media(monkeypatch, capsys):
    monkeypatch.setattr(nurture, "get_all_gpm_profiles", lambda: [
        {"id": "1", "name": "logged_in@gmail.com"},
        {"id": "2", "name": "guest@gmail.com"},
    ])
    monkeypatch.setattr(nurture, "get_emails_with_session", lambda: {"logged_in@gmail.com"})
    monkeypatch.setattr(nurture, "load_state", lambda: {})

    with patch.object(sys, "argv", ["cron_gpm_gmail_nurture.py", "--limit", "0"]):
        nurture.main()

    captured = capsys.readouterr().out
    assert "MEDIA:" not in captured


def test_save_state_oserror_handled(tmp_path, monkeypatch):
    state_file = str(tmp_path / "test_state.json")
    monkeypatch.setattr(nurture, "STATE_FILE", state_file)

    with patch("os.replace", side_effect=OSError("Disk full")):
        with patch.object(nurture.logger, "error") as mock_error:
            nurture.save_state({"test@gmail.com": {"status": "ok"}})
            mock_error.assert_called_once()
            assert "[TELEMETRY] Lỗi ghi state atomic: Disk full" in mock_error.call_args[0][0]


def test_get_emails_with_session_corrupt_db(tmp_path, monkeypatch):
    corrupt_db = tmp_path / "corrupt.db"
    with open(corrupt_db, "wb") as f:
        f.write(b"not a valid sqlite database header")

    monkeypatch.setattr(nurture, "GPM_DB", corrupt_db)
    sessions = nurture.get_emails_with_session()
    assert sessions == set()


def test_get_all_gpm_profiles_non_200():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.side_effect = Exception("JSON decode error or 500 HTML")
        mock_get.return_value = mock_resp
        profiles = nurture.get_all_gpm_profiles()
        assert profiles == []

        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Connection timeout")
        assert nurture.get_all_gpm_profiles() == []

