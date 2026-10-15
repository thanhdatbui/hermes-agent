#!/usr/bin/env python3
"""
xiaowei_idle_auto_close_watchdog.py
Watchdog tự động đóng Tiểu Vi (xiaowei.exe / 攸卫投屏) khi người dùng không thao tác chuột/phím:
- Ngưỡng idle mặc định: 20 phút (1200 giây) - cân bằng hoàn hảo giữa xem lâu và bảo vệ bus USB.
- Chỉ hành động khi:
  1. Tiến trình xiaowei.exe đang thực sự chạy trên máy tính.
  2. Thời gian người dùng KHÔNG chạm chuột hoặc bàn phím vượt quá IDLE_THRESHOLD_SECONDS.
- Cơ chế đóng an toàn:
  1. Gửi lệnh taskkill /IM xiaowei.exe giải phóng ngay 80 I/O pipe truyền màn hình.
  2. Không đụng chạm hay can thiệp vào các tiến trình nuôi nick/post video khác.
- Silent Watchdog Pattern:
  - Khi không có gì cần đóng hoặc chưa đủ thời gian idle -> Im lặng hoàn toàn (exit 0).
  - Khi thực hiện đóng -> In thông báo kèm thời gian idle và telemetry.
"""

from __future__ import annotations

import os
import sys
import json
import time
import ctypes
import subprocess
import threading
from datetime import datetime

# Đảm bảo stdout luôn dùng utf-8 tránh lỗi charmap cp1252 trên Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

IDLE_THRESHOLD_SECONDS = 1200  # 20 phút (1200 giây)
DRY_RUN_MODE = os.environ.get('WATCHDOG_DRY_RUN', '0').lower() in ('1', 'true', 'yes')
RUN_ID = os.environ.get("WATCHDOG_RUN_ID", hex(int(time.time() * 1000))[2:])
XIAOWEI_DIR = r"C:\Program Files (x86)\xiaowei"
XIAOWEI_ADB_BIN = os.path.join(XIAOWEI_DIR, "tools", "adb.exe")
XIAOWEI_ADB_PORT = 5038
XIAOWEI_ADB_TARGET_PS = (
    f"$ports = Get-NetTCPConnection -LocalPort {XIAOWEI_ADB_PORT} -State Listen -ErrorAction SilentlyContinue "
    "| Select-Object -ExpandProperty OwningProcess; "
    "Get-CimInstance Win32_Process -Filter \"Name = 'adb.exe'\" "
    "| Where-Object { $_.ProcessId -in $ports -and $_.ExecutablePath -like '*\\xiaowei\\*' }"
)
WATCHDOG_METRICS = {
    "adb_cleanup_attempts": 0,
    "adb_cleanup_successes": 0,
    "adb_cleanup_aborted_race": 0,
    "xiaowei_close_attempts": 0,
    "xiaowei_close_successes": 0,
}
_METRICS_LOCK = threading.Lock()


def _bump_metric(key: str) -> None:
    with _METRICS_LOCK:
        WATCHDOG_METRICS[key] += 1


def get_metrics() -> dict:
    with _METRICS_LOCK:
        return dict(WATCHDOG_METRICS)


def reset_metrics() -> None:
    with _METRICS_LOCK:
        for key in WATCHDOG_METRICS:
            WATCHDOG_METRICS[key] = 0


def log_event(event: str, level: str = "INFO", **fields) -> None:
    """Emit a structured JSON telemetry event to stdout for log harvesters."""
    record = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "level": level,
        "event": event,
        "correlation_id": RUN_ID,
        **fields,
    }
    print(json.dumps(record, ensure_ascii=False))


try:
    _raw_t = int(os.environ.get('XIAOWEI_CIM_TIMEOUT', '10'))
    CIM_TIMEOUT_SECONDS = max(5, min(60, _raw_t))
except Exception:
    CIM_TIMEOUT_SECONDS = 10


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_idle_seconds() -> float:
    """Return user idle seconds via passive Win32 GetLastInputInfo, without hooks or input inspection."""
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        tick_count = ctypes.windll.kernel32.GetTickCount()
        millis = (tick_count - lii.dwTime) & 0xFFFFFFFF
        return millis / 1000.0
    return 0.0


_XIAOWEI_RUNNING_CACHE: bool | None = None
_CACHE_TS = 0.0
CACHE_TTL_SECONDS = float(os.environ.get("XIAOWEI_CACHE_TTL", "2.0"))
_CACHE_LOCK = threading.Lock()


def _query_xiaowei_running() -> bool | None:
    try:
        r = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq xiaowei.exe", "/NH"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode != 0:
            log_event("XIAOWEI_CHECK_ERROR", level="ERROR", target="xiaowei.exe", returncode=r.returncode, error=(r.stderr or "").strip())
            return None
        return "xiaowei.exe" in (r.stdout or "").lower()
    except Exception as e:
        log_event("XIAOWEI_CHECK_ERROR", level="ERROR", target="xiaowei.exe", error=str(e))
        return None


def _invalidate_cache() -> None:
    global _XIAOWEI_RUNNING_CACHE, _CACHE_TS
    with _CACHE_LOCK:
        _XIAOWEI_RUNNING_CACHE, _CACHE_TS = None, 0.0


def is_xiaowei_running(use_cache: bool = False) -> bool:
    """Check whether xiaowei.exe is running, retrying once on error and failing closed to True."""
    global _XIAOWEI_RUNNING_CACHE, _CACHE_TS
    if use_cache:
        with _CACHE_LOCK:
            if _XIAOWEI_RUNNING_CACHE is not None and (time.time() - _CACHE_TS < CACHE_TTL_SECONDS):
                return _XIAOWEI_RUNNING_CACHE
    result = _query_xiaowei_running()
    if result is None:
        time.sleep(0.1)
        result = _query_xiaowei_running()
    if result is None:
        result = True
    with _CACHE_LOCK:
        _XIAOWEI_RUNNING_CACHE = result
        _CACHE_TS = time.time()
    return result


def is_xiaowei_adb_running() -> bool | None:
    """Check whether an adb.exe on port 5038 belongs to xiaowei (path-verified, isolated from farm ADB)."""
    try:
        ps_cmd = f"{XIAOWEI_ADB_TARGET_PS} | Measure-Object | Select-Object -ExpandProperty Count"
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=CIM_TIMEOUT_SECONDS)
        if r.returncode != 0:
            log_event("ADB_CHECK_ERROR", level="ERROR", method="powershell", returncode=r.returncode, error=(r.stderr or "").strip())
            return None
        output = (r.stdout or "").strip()
        return int(output) > 0 if output.isdigit() else False
    except Exception as e:
        log_event("ADB_CHECK_ERROR", level="ERROR", method="powershell", error=str(e))
        return None


def _xiaowei_started_before(stage: str) -> bool:
    """Return True if xiaowei is running, so ADB cleanup aborts instead of killing in-use sessions."""
    if is_xiaowei_running(use_cache=False):
        log_event("ADB_CLEANUP_ABORTED", level="WARNING", stage=stage, reason="xiaowei_started")
        return True
    return False


def _try_kill_server() -> bool:
    """Stop the orphan xiaowei adb server on port 5038 via kill-server; return True on success."""
    if not os.path.exists(XIAOWEI_ADB_BIN):
        return False
    try:
        if _xiaowei_started_before("kill-server"):
            _bump_metric("adb_cleanup_aborted_race")
            return False
        r = subprocess.run([XIAOWEI_ADB_BIN, "-P", str(XIAOWEI_ADB_PORT), "kill-server"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and is_xiaowei_adb_running() is False:
            log_event("ADB_CLEANUP_OK", method="kill-server", port=XIAOWEI_ADB_PORT)
            _bump_metric("adb_cleanup_successes")
            return True
    except Exception as e:
        log_event("ADB_CLEANUP_ERROR", level="ERROR", method="kill-server", error=str(e))
    return False


def _try_cim_terminate() -> bool:
    """Terminate the orphan adb process on port 5038 via CIM when xiaowei is stopped; return True on success."""
    try:
        if _xiaowei_started_before("cim-terminate"):
            _bump_metric("adb_cleanup_aborted_race")
            return False
        ps_cmd = f"if (-not (Get-Process -Name xiaowei -ErrorAction SilentlyContinue)) {{ {XIAOWEI_ADB_TARGET_PS} | Invoke-CimMethod -MethodName Terminate }}"
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=CIM_TIMEOUT_SECONDS)
        if r.returncode != 0:
            log_event("ADB_CLEANUP_ERROR", level="ERROR", method="cim-terminate", returncode=r.returncode, error=(r.stderr or "").strip())
        elif is_xiaowei_adb_running() is False:
            log_event("ADB_CLEANUP_OK", method="cim-terminate", port=XIAOWEI_ADB_PORT)
            _bump_metric("adb_cleanup_successes")
            return True
    except Exception as e:
        log_event("ADB_CLEANUP_ERROR", level="ERROR", method="cim-terminate", error=str(e))
    return False


def cleanup_orphan_xiaowei_adb() -> bool:
    """Clean orphan xiaowei adb on port 5038 when xiaowei is stopped; kill-server first, CIM fallback."""
    if DRY_RUN_MODE or is_xiaowei_running(use_cache=True) is True or is_xiaowei_adb_running() is not True:
        return False
    _bump_metric("adb_cleanup_attempts")
    if _try_kill_server() or _try_cim_terminate():
        return True
    log_event("ADB_CLEANUP_FAILED", level="ERROR", port=XIAOWEI_ADB_PORT)
    return False


def close_xiaowei() -> bool:
    """Terminate xiaowei via taskkill, falling back to CIM/WMI on failure, then clean orphan ADB."""
    if DRY_RUN_MODE:
        log_event("DRY_RUN_SKIP", action="close_xiaowei")
        return False
    _bump_metric("xiaowei_close_attempts")
    try:
        t0 = time.time()
        r = subprocess.run(
            ["taskkill", "/F", "/IM", "xiaowei.exe"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        dur_ms = round((time.time() - t0) * 1000, 1)
        is_running = is_xiaowei_running()
        if (r.returncode == 0 or "success" in (r.stdout or "").lower()) and not is_running:
            _invalidate_cache()
            adb_cleaned = cleanup_orphan_xiaowei_adb()
            log_event("XIAOWEI_CLOSE_OK", method="taskkill", adb_cleaned=adb_cleaned, duration_ms=dur_ms)
            _bump_metric("xiaowei_close_successes")
            return True
        if r.returncode == 0 and is_running:
            log_event("XIAOWEI_ZOMBIE_DETECTED", level="WARNING")
        # Fallback qua WMI/CIM nếu taskkill bị Access Denied do xiaowei chạy quyền Admin
        ps_cmd = 'Get-CimInstance Win32_Process -Filter "Name = \'xiaowei.exe\'" | Invoke-CimMethod -MethodName Terminate'
        r_cim = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=CIM_TIMEOUT_SECONDS)
        adb_cleaned = False
        if r_cim.returncode == 0 and not is_xiaowei_running():
            _invalidate_cache()
            adb_cleaned = cleanup_orphan_xiaowei_adb()
            log_event("XIAOWEI_CLOSE_OK", method="cim-terminate", adb_cleaned=adb_cleaned)
            _bump_metric("xiaowei_close_successes")
            return True
        log_event("XIAOWEI_CLOSE_FAILED", level="ERROR", taskkill_rc=r.returncode, cim_rc=r_cim.returncode, adb_cleaned=adb_cleaned)
        return False
    except Exception as e:
        log_event("XIAOWEI_CLOSE_ERROR", level="ERROR", error=str(e))
        return False


def main():
    """Close xiaowei only when idle exceeds IDLE_THRESHOLD_SECONDS; otherwise exit silently."""
    if DRY_RUN_MODE:
        log_event("DRY_RUN_ENABLED", level="WARNING")
        return
    _invalidate_cache()
    if not is_xiaowei_running():
        # Tiểu Vi không mở -> Dọn dẹp ADB 5038 mồ côi (nếu có) rồi thoát
        cleaned = cleanup_orphan_xiaowei_adb()
        if cleaned:
            log_event("WATCHDOG_SUMMARY", action="orphan_cleanup", metrics=get_metrics())
        return

    idle_sec = get_idle_seconds()
    if idle_sec >= IDLE_THRESHOLD_SECONDS:
        mins = idle_sec / 60.0
        if close_xiaowei():
            log_event(
                "XIAOWEI_CLOSE_TRIGGERED",
                idle_seconds=idle_sec,
                idle_minutes=round(mins, 1),
                metrics=get_metrics(),
            )
        else:
            log_event("XIAOWEI_CLOSE_FAILED_SUMMARY", level="ERROR", idle_seconds=idle_sec, idle_minutes=round(mins, 1), metrics=get_metrics())


if __name__ == "__main__":
    main()
