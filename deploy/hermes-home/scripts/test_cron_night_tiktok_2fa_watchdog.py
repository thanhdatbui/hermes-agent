from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from cron_night_tiktok_2fa_watchdog import (
    is_safe_rolling_window,
    parse_summary_counts,
    run_night_batch,
    EXIT_SUCCESS,
)

HCMC = ZoneInfo("Asia/Ho_Chi_Minh")


def test_is_safe_rolling_window():
    # Né ca 1 (05:45 - 09:30)
    assert not is_safe_rolling_window(datetime(2026, 10, 15, 6, 0, tzinfo=HCMC))
    assert not is_safe_rolling_window(datetime(2026, 10, 15, 8, 30, tzinfo=HCMC))
    assert not is_safe_rolling_window(datetime(2026, 10, 15, 9, 15, tzinfo=HCMC))

    # Khung rảnh sáng (09:30 - 11:45)
    assert is_safe_rolling_window(datetime(2026, 10, 15, 10, 0, tzinfo=HCMC))

    # Né ca 2 (11:45 - 15:30)
    assert not is_safe_rolling_window(datetime(2026, 10, 15, 12, 0, tzinfo=HCMC))
    assert not is_safe_rolling_window(datetime(2026, 10, 15, 14, 0, tzinfo=HCMC))

    # Khung rảnh chiều (15:30 - 17:45)
    assert is_safe_rolling_window(datetime(2026, 10, 15, 16, 0, tzinfo=HCMC))

    # Né ca 3 (17:45 - 21:30)
    assert not is_safe_rolling_window(datetime(2026, 10, 15, 18, 0, tzinfo=HCMC))
    assert not is_safe_rolling_window(datetime(2026, 10, 15, 20, 0, tzinfo=HCMC))

    # Khung rảnh đêm (21:30 - 04:00)
    assert is_safe_rolling_window(datetime(2026, 10, 15, 22, 0, tzinfo=HCMC))
    assert is_safe_rolling_window(datetime(2026, 10, 15, 1, 0, tzinfo=HCMC))

    # Né dọn cache (04:00 - 04:30)
    assert not is_safe_rolling_window(datetime(2026, 10, 15, 4, 15, tzinfo=HCMC))
    assert is_safe_rolling_window(datetime(2026, 10, 15, 4, 45, tzinfo=HCMC))

    # Khung giờ 5h sáng (chạy đến 05:15)
    assert is_safe_rolling_window(datetime(2026, 10, 15, 5, 5, tzinfo=HCMC))
    assert not is_safe_rolling_window(datetime(2026, 10, 15, 5, 20, tzinfo=HCMC))


def test_parse_summary_counts():
    output = "=== CLUSTER KIBE (MÁY 1-80) ===\nTOTAL=40 SUCCESS=38 FAILED=2\n"
    res = parse_summary_counts(output)
    assert res["total"] == 40
    assert res["success"] == 38
    assert res["failed"] == 2


def test_run_night_batch_dry_run():
    code, out = run_night_batch(dry_run=True)
    assert code == EXIT_SUCCESS
    assert "TOTAL=40 SUCCESS=40 FAILED=0" in out


def test_workbook_hydration_and_admin_script():
    import inspect
    from cron_night_tiktok_2fa_watchdog import WORKBOOK_PATH

    assert isinstance(WORKBOOK_PATH, Path)
    src = inspect.getsource(run_night_batch)
    assert "ps_admin_script" in src and "attrib -u +p" in src


def test_run_night_batch_missing_runner(monkeypatch):
    import cron_night_tiktok_2fa_watchdog as wd
    monkeypatch.setattr(wd, 'TIKTOK_2FA_REPO_DIR', Path('D:/nonexistent_dir_xyz'))
    code, out = wd.run_night_batch(dry_run=False)
    assert code == 1
    assert 'Không tìm thấy runner script' in out


def test_parse_summary_counts_empty_fallback():
    from cron_night_tiktok_2fa_watchdog import parse_summary_counts
    res = parse_summary_counts('')
    assert res['total'] == 0 and res['success'] == 0 and res['failed'] == 0


def test_save_state_telemetry(tmp_path, monkeypatch):
    import json
    import cron_night_tiktok_2fa_watchdog as wd
    test_state_file = tmp_path / 'state.json'
    monkeypatch.setattr(wd, 'STATE_FILE', test_state_file)
    monkeypatch.setattr(wd, 'STATE_DIR', tmp_path)
    wd.save_state('2026-10-18', {'status': 'success', 'code': 0, 'correlation_id': 'cid-123', 'failure_reason': None})
    assert test_state_file.exists()
    data = json.loads(test_state_file.read_text(encoding='utf-8'))
    assert data['correlation_id'] == 'cid-123' and data['details']['code'] == 0


def test_hydrate_workbook(tmp_path, monkeypatch):
    import subprocess
    import cron_night_tiktok_2fa_watchdog as wd

    dummy = tmp_path / 'dummy.xlsx'
    dummy.write_bytes(b'PK\x03\x04testdata123')
    monkeypatch.setattr(wd.sys, 'platform', 'win32')
    monkeypatch.setattr(wd.subprocess, 'run', lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, b'', b''))
    assert wd.hydrate_workbook(dummy) is True
    assert wd.hydrate_workbook(tmp_path / 'nonexistent.xlsx') is False

    monkeypatch.setattr(wd.subprocess, 'run', lambda *a, **kw: subprocess.CompletedProcess(a[0], 1, b'', b'attrib failed'))
    assert wd.hydrate_workbook(dummy) is False

    monkeypatch.setattr(wd.subprocess, 'run', lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, b'', b''))
    import builtins

    def mock_open_fail(*a, **kw):
        raise OSError('open failed')

    monkeypatch.setattr(builtins, 'open', mock_open_fail)
    assert wd.hydrate_workbook(dummy) is False

