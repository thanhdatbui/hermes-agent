#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""safe_usb_guard.py (v2 - with Backoff & Logging)

Kiem tra an toan truoc khi reset USB Bus:
1. Kiem tra xem co may nao dang giu active lock (device_lock) khong.
2. Kiem tra xem ADB co thuc su bi ket/chet khong (adb devices co loi hoac khong phan hoi).
3. Backoff Logic (Theo dac ta Advisor Sol):
   - Toi da 2 lan reset lien tiep. Neu sau 2 lan van loi -> Dung reset trong 30 phut de bao ve controller.
   - Khi ADB khoe manh -> Tu dong reset bo dem ve 0.
4. Ghi log lich su vao C:\Taadaa_Service\safe_usb_guard.log.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

LOCK_ROOT = Path.home() / ".codex" / "device-locks"
RESET_BAT = Path(r"C:\Taadaa_Service\reset_usb_bus.bat")
ADB_EXE = Path(r"C:\Program Files (x86)\xiaowei\tools\adb.exe")
STATE_FILE = Path(r"C:\Taadaa_Service\usb_guard_state.json")
LOG_FILE = Path(r"C:\Taadaa_Service\safe_usb_guard.log")

MAX_CONSECUTIVE_RESETS = 2
COOLDOWN_SECONDS = 1800  # 30 phut


def log_message(msg: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"consecutive_resets": 0, "last_reset_time": 0}


def save_state(state: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        pass


def has_active_device_locks(lock_root: Path = LOCK_ROOT) -> tuple[bool, list[str]]:
    """Kiem tra xem co may nao dang ban lock va process van con song khong."""
    if not lock_root.exists():
        return False, []

    busy_devices: list[str] = []
    
    owner_alive_fn = None
    try:
        sys.path.insert(0, r"D:\Taadaa\automation-core\src")
        from automation_core.device_lock import owner_process_alive
        owner_alive_fn = owner_process_alive
    except Exception:
        pass

    for p in lock_root.glob("*.lock.json"):
        try:
            raw = p.read_text(encoding="utf-8")
            data = json.loads(raw)
            status = str(data.get("status", "")).lower()
            pid = data.get("pid")
            
            if status in ("active", "running", "locked", "acquired", "busy"):
                is_alive = True
                if owner_alive_fn and pid:
                    try:
                        is_alive = owner_alive_fn(data)
                    except Exception:
                        is_alive = True
                elif pid:
                    try:
                        res = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True, timeout=5)
                        is_alive = str(pid) in res.stdout
                    except Exception:
                        is_alive = True

                if is_alive:
                    dev_id = str(data.get("machine") or data.get("serial") or p.stem)
                    busy_devices.append(f"{dev_id} (PID {pid}, status={status})")
        except Exception:
            pass

    return len(busy_devices) > 0, busy_devices


def is_adb_healthy(min_expected_devices: int = 50) -> tuple[bool, str]:
    """Kiem tra xem ADB co phan hoi va nhan du thiet bi khong."""
    if not ADB_EXE.exists():
        return False, "ADB executable not found"

    try:
        t0 = time.time()
        res = subprocess.run(
            [str(ADB_EXE), "devices"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        elapsed = time.time() - t0
        if res.returncode != 0:
            return False, f"adb devices exit code {res.returncode}"

        lines = [l.strip() for l in res.stdout.strip().splitlines() if l.strip() and not l.startswith("List of")]
        online_count = sum(1 for l in lines if l.endswith("\tdevice"))
        
        if online_count < min_expected_devices:
            return False, f"Chi con {online_count} may online (ky vong >= {min_expected_devices})"

        return True, f"ADB OK: {online_count} may online (lat: {elapsed:.2f}s)"
    except subprocess.TimeoutExpired:
        return False, "adb devices TIMEOUT (>8s) - ADB daemon bi treo"
    except Exception as e:
        return False, f"adb devices exception: {e}"


def check_and_reset(force: bool = False, min_devices: int = 50) -> int:
    log_message("Kiem tra trang thai USB & Device Locks...")

    # 1. Kiem tra Device Locks
    is_busy, busy_list = has_active_device_locks()
    if is_busy:
        log_message(f"[GUARD BLOCK] KHONG THE RESET USB: Co {len(busy_list)} may dang ban khoa: {', '.join(busy_list[:3])}")
        return 1

    log_message("[GUARD PASS] Khong co may nao dang ban giu lock (Fleet ranh).")

    # 2. Kiem tra ADB Health
    adb_ok, adb_msg = is_adb_healthy(min_expected_devices=min_devices)
    log_message(f"[ADB STATUS] {adb_msg}")

    state = load_state()

    if adb_ok and not force:
        log_message("[SKIP] ADB va bus USB van dang khoe manh, khong can reset.")
        if state.get("consecutive_resets", 0) > 0:
            state["consecutive_resets"] = 0
            save_state(state)
            log_message("[STATE] Da reset consecutive_resets ve 0.")
        return 0

    # 3. Kiem tra Backoff Logic
    consecutive = state.get("consecutive_resets", 0)
    last_reset = state.get("last_reset_time", 0)
    now = time.time()

    if consecutive >= MAX_CONSECUTIVE_RESETS and (now - last_reset) < COOLDOWN_SECONDS and not force:
        remaining = int((COOLDOWN_SECONDS - (now - last_reset)) / 60)
        log_message(f"[BACKOFF BLOCK] Da reset {consecutive} lan lien tiep that bai. Cooldown con {remaining} phut de bao ve phan cung. Dung reset!")
        return 5

    # 4. Kich hoat Reset
    log_message(f"[TRIGGER RESET] Kich hoat reset USB Bus (Lan {consecutive + 1}/{MAX_CONSECUTIVE_RESETS}) do: {adb_msg}...")
    if not RESET_BAT.exists():
        log_message(f"[ERROR] Khong tim thay file {RESET_BAT}")
        return 2

    try:
        state["consecutive_resets"] = consecutive + 1
        state["last_reset_time"] = now
        save_state(state)

        res = subprocess.run([str(RESET_BAT)], capture_output=True, text=True, timeout=30)
        log_message(f"[RESET OUTPUT] {res.stdout.strip()}")
        if res.stderr:
            log_message(f"[RESET STDERR] {res.stderr.strip()}")
        
        # Cho 5 giay de thiet bi nhan lai va check lai
        time.sleep(5)
        after_ok, after_msg = is_adb_healthy(min_expected_devices=min_devices)
        log_message(f"[AFTER RESET] {after_msg}")
        
        if after_ok:
            state["consecutive_resets"] = 0
            save_state(state)
            log_message("[STATE] Reset thanh cong, da reset consecutive_resets ve 0.")
            return 0
        else:
            log_message("[WARNING] Reset xong van chua du thiet bi online!")
            return 3
    except Exception as e:
        log_message(f"[RESET FAILED] Exception: {e}")
        return 4


if __name__ == "__main__":
    force_run = "--force" in sys.argv
    min_devs = 50
    for arg in sys.argv:
        if arg.startswith("--min-devices="):
            min_devs = int(arg.split("=")[1])
    sys.exit(check_and_reset(force=force_run, min_devices=min_devs))
