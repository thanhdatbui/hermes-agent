import importlib.util
import json, os, subprocess, sys, threading
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "deploy", "hermes-home", "scripts"))
import xiaowei_idle_auto_close_watchdog as xw


@pytest.fixture(autouse=True)
def _clean_state(tmp_path, monkeypatch):
    monkeypatch.setattr(xw, "STATE_FILE", str(tmp_path / "xiaowei_idle_activity.ts"))
    xw.reset_metrics()
    xw._invalidate_cache()
    yield


def test_is_running_helpers(capsys):
    for out, exp in [("xiaowei.exe 51032", True), ("INFO: No tasks", False)]:
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=out)):
            assert xw.is_xiaowei_running() is exp
    with patch("subprocess.run", return_value=MagicMock(returncode=1, stdout="", stderr="denied")):
        assert xw.is_xiaowei_running() is True
    assert '"event": "XIAOWEI_CHECK_ERROR"' in capsys.readouterr().out
    with patch.object(xw, "_query_xiaowei_running", side_effect=[None, None]) as query:
        assert xw.is_xiaowei_running() is True
    assert query.call_count == 2
    for rc, out, exp in [(0, "2", True), (0, "0", False), (0, "bad", False), (1, "", None)]:
        with patch("subprocess.run", return_value=MagicMock(returncode=rc, stdout=out, stderr="e")):
            assert xw.is_xiaowei_adb_running() is exp
    with patch("subprocess.run", side_effect=Exception("timeout")):
        assert xw.is_xiaowei_adb_running() is None
    with patch.object(xw, "_XIAOWEI_RUNNING_CACHE", True), patch.object(xw, "_CACHE_TS", xw.time.time() - 5.0), \
         patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="")) as run:
        assert xw.is_xiaowei_running(use_cache=True) is False and run.call_count == 1
    with patch.object(xw.ctypes.windll.user32, 'GetLastInputInfo', return_value=0), \
         patch.object(xw, "is_xiaowei_foreground", return_value=False):
        assert xw.get_idle_seconds() == 0.0
    assert xw.IDLE_THRESHOLD_SECONDS == 600


def test_get_idle_seconds_counts_unfocused_time(monkeypatch):
    clock = MagicMock()
    clock.time.return_value = 1000.0
    monkeypatch.setattr(xw, "time", clock)
    monkeypatch.setattr(xw, "_system_idle_seconds", lambda: 5.0)
    monkeypatch.setattr(xw, "is_xiaowei_foreground", lambda: True)
    assert xw.get_idle_seconds() == 0.0
    monkeypatch.setattr(xw, "is_xiaowei_foreground", lambda: False)
    clock.time.return_value = 1000.0 + xw.IDLE_THRESHOLD_SECONDS
    assert xw.get_idle_seconds() == xw.IDLE_THRESHOLD_SECONDS


def test_close_xiaowei_clears_idle_state(monkeypatch):
    xw._write_last_active(1000.0)
    monkeypatch.setattr(xw, "cleanup_orphan_xiaowei_adb", lambda: False)
    monkeypatch.setattr(xw, "is_xiaowei_running", lambda: False)
    with patch("subprocess.run", return_value=_proc(0, "SUCCESS")):
        assert xw.close_xiaowei() is True
    assert not os.path.exists(xw.STATE_FILE)


def test_cleanup_orphan_preconditions_and_kill():
    xw.reset_metrics()
    with patch.object(xw, "is_xiaowei_running") as running, patch.object(xw, "is_xiaowei_adb_running") as adb, \
         patch("os.path.exists", return_value=True), patch("subprocess.run", return_value=MagicMock(returncode=0)):
        running.return_value = True
        assert not xw.cleanup_orphan_xiaowei_adb()
        running.return_value, adb.return_value = False, False
        assert not xw.cleanup_orphan_xiaowei_adb()
        running.side_effect, adb.return_value = [False, True], True
        assert not xw.cleanup_orphan_xiaowei_adb()
        assert xw.get_metrics()["adb_cleanup_aborted_race"] == 1
        running.side_effect, running.return_value = None, False
        adb.side_effect = [True, False]
        assert xw.cleanup_orphan_xiaowei_adb()


def test_cleanup_orphan_cim():
    with (patch.object(xw, "is_xiaowei_running") as running, patch.object(xw, "is_xiaowei_adb_running") as adb,
          patch("os.path.exists") as exists, patch("subprocess.run") as run):
        running.side_effect, adb.return_value, exists.return_value = [False, False, True], True, True
        run.side_effect = Exception("bin fail")
        assert not xw.cleanup_orphan_xiaowei_adb()
        running.side_effect, running.return_value, adb.side_effect, exists.return_value = None, False, [True, False], False
        run.side_effect, run.return_value = None, MagicMock(returncode=0)
        assert xw.cleanup_orphan_xiaowei_adb()
        assert "Invoke-CimMethod" in run.call_args.args[0][-1]


def _proc(rc=0, out="", err=""):
    return MagicMock(returncode=rc, stdout=out, stderr=err)


def test_close_xiaowei(monkeypatch, capsys):
    cleanup_mock = MagicMock(return_value=False)
    monkeypatch.setattr(xw, "cleanup_orphan_xiaowei_adb", cleanup_mock)
    monkeypatch.setattr(xw, "is_xiaowei_running", lambda: False)
    with patch("subprocess.run", return_value=_proc(0, "SUCCESS")) as run:
        assert xw.close_xiaowei() is True and run.call_count == 1
    cleanup_mock.assert_called()
    with patch("subprocess.run", side_effect=[_proc(1, "", "Access is denied"), _proc(0)]) as run:
        assert xw.close_xiaowei() is True and run.call_count == 2 and run.call_args_list[1].args[0][0] == "powershell"
    monkeypatch.setattr(xw, "is_xiaowei_running", lambda: True)
    with patch("subprocess.run", side_effect=[_proc(1, "failed"), _proc(1, "", "cim err")]) as run:
        assert xw.close_xiaowei() is False and run.call_count == 2
    out = capsys.readouterr().out
    assert '"method": "taskkill"' in out and '"method": "cim-terminate"' in out and '"taskkill_rc": 1' in out
    with patch("subprocess.run", side_effect=OSError("boom")):
        assert xw.close_xiaowei() is False
    assert '"event": "XIAOWEI_CLOSE_ERROR"' in capsys.readouterr().out
    r_iter = iter([True, False])
    monkeypatch.setattr(xw, "is_xiaowei_running", lambda: next(r_iter))
    with patch("subprocess.run", side_effect=[_proc(0, "SUCCESS"), _proc(0)]) as run:
        assert xw.close_xiaowei() is True and run.call_count == 2 and run.call_args_list[1].args[0][0] == "powershell"
    assert 'XIAOWEI_ZOMBIE_DETECTED' in capsys.readouterr().out
    monkeypatch.setattr(xw, "DRY_RUN_MODE", True)
    assert xw.close_xiaowei() is False and '"event": "DRY_RUN_SKIP"' in capsys.readouterr().out
    monkeypatch.setattr(xw, "DRY_RUN_MODE", False)


def test_main(monkeypatch, capsys):
    cleanup, close, idle = MagicMock(), MagicMock(return_value=False), MagicMock(return_value=0.0)
    monkeypatch.setattr(xw, "cleanup_orphan_xiaowei_adb", cleanup)
    monkeypatch.setattr(xw, "close_xiaowei", close)
    monkeypatch.setattr(xw, "get_idle_seconds", idle)
    monkeypatch.setattr(xw, "is_xiaowei_running", lambda: False)
    xw.main()
    cleanup.assert_called_once()
    monkeypatch.setattr(xw, "is_xiaowei_running", lambda: True)
    idle.return_value = 300.0
    xw.main()
    close.assert_not_called()
    idle.return_value = 1350.5
    close.return_value = True
    xw.main()
    assert "XIAOWEI_CLOSE_TRIGGERED" in capsys.readouterr().out
    assert xw._XIAOWEI_RUNNING_CACHE is None

    monkeypatch.setattr(xw, "DRY_RUN_MODE", True)
    xw.main()
    assert '"event": "DRY_RUN_ENABLED"' in capsys.readouterr().out
    monkeypatch.setattr(xw, 'DRY_RUN_MODE', False)
    monkeypatch.setattr(xw, 'get_idle_seconds', lambda: 1200.0)
    with patch.object(xw, 'close_xiaowei', return_value=True):
        xw.main()
    assert 'XIAOWEI_CLOSE_TRIGGERED' in capsys.readouterr().out


def test_cim_timeout_env_parsing(monkeypatch):
    for value, expected in [(None, 10), ("-1", 5), ("120", 60), ("abc", 10)]:
        monkeypatch.delenv("XIAOWEI_CIM_TIMEOUT", raising=False)
        if value is not None:
            monkeypatch.setenv("XIAOWEI_CIM_TIMEOUT", value)
        spec = importlib.util.spec_from_file_location("p", xw.__file__)
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)
        assert probe.CIM_TIMEOUT_SECONDS == expected


def test_metrics_thread_safety():
    threads = [threading.Thread(target=lambda: [xw._bump_metric("adb_cleanup_attempts") for _ in range(1000)]) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert xw.get_metrics()["adb_cleanup_attempts"] == 5000


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_windows_real_integration():
    assert xw.get_idle_seconds() >= 0
    assert xw.XIAOWEI_ADB_PORT == 5038 and "5037" not in xw.XIAOWEI_ADB_TARGET_PS
    assert xw.is_xiaowei_running() in (True, False) and xw.is_xiaowei_adb_running() in (True, False)
    assert xw.cleanup_orphan_xiaowei_adb() in (True, False)
    r_ps = subprocess.run(["powershell", "-NoProfile", "-Command", xw.XIAOWEI_ADB_TARGET_PS], capture_output=True, timeout=15)
    assert r_ps.returncode == 0


def test_telemetry_json_schema(monkeypatch, capsys):
    monkeypatch.setattr(xw, "is_xiaowei_running", lambda: True)
    with patch("subprocess.run", return_value=MagicMock(returncode=1, stdout="", stderr="denied")): xw.close_xiaowei()
    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert all(r.get("level") in {"INFO", "WARNING", "ERROR"} for r in records)
    assert any(r.get("event") == "XIAOWEI_CLOSE_FAILED" for r in records)
    monkeypatch.setattr(xw, "is_xiaowei_running", lambda: False)
    monkeypatch.setattr(xw, "cleanup_orphan_xiaowei_adb", lambda: True)
    xw.main()
    assert any(r.get("event") == "WATCHDOG_SUMMARY" for r in map(json.loads, capsys.readouterr().out.splitlines()))


def test_netstat_powershell_contract():
    assert "netstat -ano -p tcp" in xw.XIAOWEI_ADB_TARGET_PS
    assert f":{xw.XIAOWEI_ADB_PORT}\\s+\\S+\\s+LISTENING" in xw.XIAOWEI_ADB_TARGET_PS
    assert "Get-CimInstance Win32_Process" in xw.XIAOWEI_ADB_TARGET_PS
    for count_str, expected in [("1", True), ("0", False), ("3", True), ("", False)]:
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=count_str)):
            assert xw.is_xiaowei_adb_running() is expected


def test_powershell_target_string_contract():
    ps = xw.XIAOWEI_ADB_TARGET_PS
    assert "Get-NetTCPConnection" in ps
    assert "netstat -ano -p tcp" in ps
    assert "if (-not $ports)" in ps
    assert "$_.ProcessId -in $ports" in ps
    assert "*-P 5038*" in ps


def test_is_xiaowei_adb_running_branches(capsys):
    with patch("subprocess.run", return_value=_proc(0, "3\n")) as run:
        assert xw.is_xiaowei_adb_running() is True
    cmd = run.call_args.args[0][-1]
    assert cmd.startswith(xw.XIAOWEI_ADB_TARGET_PS) and "Get-NetTCPConnection" in cmd

    with patch("subprocess.run", return_value=_proc(0, "  1 \r\n")) as run:
        assert xw.is_xiaowei_adb_running() is True
    assert "netstat -ano -p tcp" in run.call_args.args[0][-1]

    with patch("subprocess.run", return_value=_proc(0, "0\n")):
        assert xw.is_xiaowei_adb_running() is False
    with patch("subprocess.run", return_value=_proc(0, "   \n")):
        assert xw.is_xiaowei_adb_running() is False
    assert '"event": "ADB_CHECK_ERROR"' not in capsys.readouterr().out

    with patch("subprocess.run", return_value=_proc(1, "", "powershell failed")):
        assert xw.is_xiaowei_adb_running() is None
    assert '"event": "ADB_CHECK_ERROR"' in capsys.readouterr().out

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="powershell", timeout=10)):
        assert xw.is_xiaowei_adb_running() is None
    assert '"event": "ADB_CHECK_ERROR"' in capsys.readouterr().out


def test_is_xiaowei_adb_negative_and_adversarial(monkeypatch, capsys):
    for out in ["0", "0\n", "  0 \r\n"]:
        with patch("subprocess.run", return_value=_proc(0, out)):
            assert xw.is_xiaowei_adb_running() is False
    assert '"event": "ADB_CHECK_ERROR"' not in capsys.readouterr().out

    monkeypatch.setattr(xw, "DRY_RUN_MODE", False)
    monkeypatch.setattr(xw, "is_xiaowei_running", lambda use_cache=False: False)
    with patch("subprocess.run", return_value=_proc(0, "0\n")) as run:
        assert xw.cleanup_orphan_xiaowei_adb() is False
    assert run.call_count == 1 and xw.get_metrics()["adb_cleanup_attempts"] == 0
    assert capsys.readouterr().out == ""

    with patch("subprocess.run", return_value=_proc(1, "", "powershell failed")):
        assert xw.is_xiaowei_adb_running() is None
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="powershell", timeout=10)):
        assert xw.is_xiaowei_adb_running() is None
    errors = [r for r in map(json.loads, capsys.readouterr().out.splitlines()) if r.get("event") == "ADB_CHECK_ERROR"]
    assert [r["level"] for r in errors] == ["ERROR", "ERROR"]
    assert all(r["method"] == "powershell" for r in errors)
    assert errors[0]["returncode"] == 1 and errors[0]["error"] == "powershell failed"
    assert "timed out" in errors[1]["error"]

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="powershell", timeout=10)) as run:
        assert xw.cleanup_orphan_xiaowei_adb() is False
    assert run.call_count == 1 and xw.get_metrics()["adb_cleanup_attempts"] == 0

