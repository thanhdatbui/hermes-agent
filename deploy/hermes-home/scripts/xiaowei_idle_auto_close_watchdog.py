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

import os
import sys
import time
import ctypes
import subprocess
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


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_idle_seconds() -> float:
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        tick_count = ctypes.windll.kernel32.GetTickCount()
        millis = (tick_count - lii.dwTime) & 0xFFFFFFFF
        return millis / 1000.0
    return 0.0


def is_xiaowei_running() -> bool:
    try:
        r = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq xiaowei.exe", "/NH"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return "xiaowei.exe" in r.stdout.lower()
    except Exception:
        return False


def close_xiaowei() -> bool:
    try:
        r = subprocess.run(
            ["taskkill", "/F", "/IM", "xiaowei.exe"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if (r.returncode == 0 or "success" in r.stdout.lower()) and not is_xiaowei_running():
            return True
        # Fallback qua WMI/CIM nếu taskkill bị Access Denied do xiaowei chạy quyền Admin
        ps_cmd = 'Get-CimInstance Win32_Process -Filter "Name = \'xiaowei.exe\'" | Invoke-CimMethod -MethodName Terminate'
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=8)
        return not is_xiaowei_running()
    except Exception as e:
        sys.stderr.write(f"Error closing xiaowei: {e}\n")
        return False


def main():
    if not is_xiaowei_running():
        # Tiểu Vi không mở -> Silent không làm gì
        return

    idle_sec = get_idle_seconds()
    if idle_sec >= IDLE_THRESHOLD_SECONDS:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mins = idle_sec / 60.0
        success = close_xiaowei()
        if not success:
            print(
                f"[{now_str}] [XIAOWEI_CLOSE_FAILED] Da phat hien idle {mins:.1f} phut nhung khong the taskkill xiaowei.exe"
            )


if __name__ == "__main__":
    main()
