import sqlite3
import sys
from pathlib import Path
import pytest

# Add scripts directory to sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "deploy" / "hermes-home" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import hermes_stale_watchdog as watchdog


def test_check_and_truncate_wal_no_wal(tmp_path, monkeypatch):
    monkeypatch.setattr(watchdog, "HERMES_HOME", tmp_path)
    # WAL doesn't exist, should return None
    res = watchdog.check_and_truncate_wal()
    assert res is None


def test_check_and_truncate_wal_below_threshold(tmp_path, monkeypatch):
    monkeypatch.setattr(watchdog, "HERMES_HOME", tmp_path)
    db_file = tmp_path / "state.db"
    db_file.write_bytes(b"dummy")
    wal_file = tmp_path / "state.db-wal"
    wal_file.write_bytes(b"x" * 1024)
    # Below threshold (50MB), should return None and not trigger truncate
    res = watchdog.check_and_truncate_wal()
    assert res is None
    assert wal_file.exists()


def test_check_and_truncate_wal_above_threshold(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(watchdog, "HERMES_HOME", tmp_path)
    db_file = tmp_path / "state.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE t (id INT)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()

    wal_file = tmp_path / "state.db-wal"
    assert wal_file.exists()

    try:
        # Mock threshold to 10 bytes to trigger truncate
        monkeypatch.setattr(watchdog, "WAL_TRUNCATE_THRESHOLD_BYTES", 10)
        telemetry = watchdog.check_and_truncate_wal()
        assert telemetry is not None
        assert telemetry["status"] == "success"
        assert telemetry["checkpoint_result"][0] == 0
        captured = capsys.readouterr()
        assert "[WAL_WATCHDOG] Truncated WAL" in captured.err
        assert wal_file.exists()
    finally:
        conn.close()


def test_check_and_truncate_wal_handles_exception(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(watchdog, "HERMES_HOME", tmp_path)
    wal_file = tmp_path / "state.db-wal"
    wal_file.write_bytes(b"x" * 100)
    monkeypatch.setattr(watchdog, "WAL_TRUNCATE_THRESHOLD_BYTES", 10)
    # Point to invalid DB file to cause exception
    (tmp_path / "state.db").write_text("not a sqlite db")
    telemetry = watchdog.check_and_truncate_wal()
    assert telemetry is not None
    assert telemetry["status"] == "error"
    assert "error" in telemetry
    captured = capsys.readouterr()
    assert "[WAL_WATCHDOG] Failed to truncate WAL" in captured.err


def test_check_and_truncate_wal_concurrency_lock_busy(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(watchdog, "HERMES_HOME", tmp_path)
    wal_file = tmp_path / "state.db-wal"
    wal_file.write_bytes(b"x" * 100)
    (tmp_path / "state.db").write_bytes(b"dummy")
    monkeypatch.setattr(watchdog, "WAL_TRUNCATE_THRESHOLD_BYTES", 10)

    def mock_connect(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(sqlite3, "connect", mock_connect)
    telemetry = watchdog.check_and_truncate_wal()
    assert telemetry is not None
    assert telemetry["status"] == "error"
    assert "database is locked" in telemetry["error"]
    captured = capsys.readouterr()
    assert "[WAL_WATCHDOG] Failed to truncate WAL: OperationalError: database is locked" in captured.err


def test_main_integrates_wal_truncate_and_preserves_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setattr(watchdog, "HERMES_HOME", tmp_path)
    monkeypatch.setattr(watchdog, "WATCHDOG_STATE_FILE", tmp_path / "watchdog_state.json")
    monkeypatch.setattr(watchdog, "PHASE_FILE", tmp_path / "farm_coordinator_phase.json")
    monkeypatch.setattr(watchdog, "ALERT_CACHE_FILE", tmp_path / "stale_alert_sent.json")
    (tmp_path / "watchdog_state.json").write_text("{\"sessions\": {}}", encoding="utf-8")
    (tmp_path / "farm_coordinator_phase.json").write_text("{\"sessions\": {}}", encoding="utf-8")

    exit_code = watchdog.main()
    assert exit_code == 0



def test_main_records_wal_telemetry_to_jsonl_and_keeps_stdout_silent(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(watchdog, "HERMES_HOME", tmp_path)
    monkeypatch.setattr(watchdog, "WATCHDOG_STATE_FILE", tmp_path / "watchdog_state.json")
    monkeypatch.setattr(watchdog, "PHASE_FILE", tmp_path / "farm_coordinator_phase.json")
    monkeypatch.setattr(watchdog, "ALERT_CACHE_FILE", tmp_path / "stale_alert_sent.json")
    monkeypatch.setattr(watchdog, "WAL_TELEMETRY_LOG", tmp_path / "logs" / "wal_maintenance.jsonl")
    (tmp_path / "watchdog_state.json").write_text("{\"sessions\": {}}", encoding="utf-8")
    (tmp_path / "farm_coordinator_phase.json").write_text("{\"sessions\": {}}", encoding="utf-8")

    db_file = tmp_path / "state.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE t (id INT)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()

    try:
        monkeypatch.setattr(watchdog, "WAL_TRUNCATE_THRESHOLD_BYTES", 10)
        exit_code = watchdog.main()
        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == ""  # Stdout must be completely silent
        log_file = tmp_path / "logs" / "wal_maintenance.jsonl"
        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "wal_truncate" in content
        assert "success" in content
    finally:
        conn.close()
