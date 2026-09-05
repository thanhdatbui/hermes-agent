"""Tự động chờ phiên nuôi Ca 3 kết thúc và kích hoạt batch upload avatar cho Tik5.

Dữ liệu nguồn: Đọc trực tiếp từ D:\\OneDrive\\TaadaaData\\kibe\\taikhoan_run_safe.xlsx (Slot 5).
Không dùng / không chế bất kỳ file manifest trung gian nào.
"""
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import openpyxl
import psutil

TAIKHOAN_RUN_SAFE = r"D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx"
TIK_NUM = 5
LAUNCHER_PS1 = r"D:\Taadaa\Tiktok-video\run_tiktok_upload_batch.ps1"
HOST_CONFIG = r"D:\Taadaa\machine-config\kibe.yaml"
RUNTIME_ROOT = r"D:\CodexRuntime\tiktok-video"
ADB_EXE = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"


def is_feed_runner_active() -> bool:
    """Kiểm tra có process feed runner hay powershell feed nào đang chạy không."""
    try:
        for p in psutil.process_iter(['name', 'cmdline']):
            try:
                name = (p.info.get('name') or '').lower()
                if not name.startswith(('python', 'powershell', 'pwsh')):
                    continue
                cmd = " ".join(p.info.get('cmdline') or [])
                if "multi_machine_feed_session" in cmd or "run-feed-session.ps1" in cmd or "run_follow" in cmd:
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return False


def get_online_adb_serials() -> set[str]:
    """Lấy danh sách serial ADB đang online."""
    try:
        res = subprocess.run([ADB_EXE, "devices"], capture_output=True, text=True, timeout=10)
        lines = res.stdout.strip().splitlines()
        online = set()
        for l in lines[1:]:
            parts = l.split()
            if len(parts) >= 2 and parts[1] == "device":
                online.add(parts[0])
        return online
    except Exception as ex:
        print(f"Lỗi đọc ADB devices: {ex}")
        return set()


def get_target_machines_from_run_safe() -> list[int]:
    """Đọc trực tiếp từ taikhoan_run_safe.xlsx cho Slot 5 (Ca tối), lọc máy online."""
    wb = openpyxl.load_workbook(TAIKHOAN_RUN_SAFE, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))[1:]
    
    machine_slots = defaultdict(list)
    for r in rows:
        m = str(r[0]).strip() if r[0] else ""
        if m:
            machine_slots[m].append({
                "serial": r[1],
                "account_id": r[2],
            })
            
    online_serials = get_online_adb_serials()
    
    target_machines = []
    missing_account_machines = []
    offline_machines = []
    
    for m_num in range(1, 81):
        m_str = str(m_num)
        slots = machine_slots.get(m_str, [])
        if len(slots) >= 5:
            s5 = slots[4]  # Slot 5 = Tik5 / Ca tối
            aid = str(s5["account_id"]).strip() if s5["account_id"] else ""
            ser = str(s5["serial"]).strip() if s5["serial"] else ""
            
            if not aid or aid.lower() == "none":
                missing_account_machines.append(m_num)
                continue
                
            if ser not in online_serials:
                offline_machines.append(m_num)
                continue
                
            target_machines.append(m_num)
        else:
            missing_account_machines.append(m_num)
            
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Đọc taikhoan_run_safe.xlsx (Slot 5):")
    print(f"  • Máy đủ điều kiện chạy ({len(target_machines)}): {target_machines}")
    print(f"  • Máy thiếu nick ({len(missing_account_machines)}): {missing_account_machines}")
    print(f"  • Máy offline ({len(offline_machines)}): {offline_machines}")
    
    return target_machines


def wait_for_feed_completion():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Đang theo dõi tiến trình nuôi feed Ca 3...")
    streak_idle = 0
    while True:
        active = is_feed_runner_active()
        if not active:
            streak_idle += 1
            if streak_idle >= 3:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Toàn bộ tiến trình feed session đã kết thúc an toàn.")
                break
        else:
            streak_idle = 0
        time.sleep(15)


def run_avatar_batch():
    machines = get_target_machines_from_run_safe()
    if not machines:
        print("Không có máy nào hợp lệ để chạy.")
        return
        
    m_list_str = ",".join(str(m) for m in machines)
    
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", LAUNCHER_PS1,
        "-Tik", str(TIK_NUM),
        "-AvatarOnly",
        "-ForceAvatarMachineList", m_list_str,
        "-MaxParallel", "40",
        "-HostConfigPath", HOST_CONFIG
    ]
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Kích hoạt batch upload avatar cho {len(machines)} máy theo taikhoan_run_safe...")
    start_time = time.time()
    
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    
    output_lines = []
    while True:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        if line:
            output_lines.append(line)
            if any(k in line for k in ["[ENSURE_AVATAR]", "Bắt đầu máy", "hoàn thành", "thất bại", "Summary:"]):
                print(line.strip())
                
    rc = proc.poll()
    duration_min = round((time.time() - start_time) / 60, 1)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Batch hoàn thành trong {duration_min} phút (Exit code: {rc}).")
    
    # Analyze latest batch run
    batch_dirs = sorted([
        d for d in os.listdir(os.path.join(RUNTIME_ROOT, "batch-runs"))
        if d.startswith(f"batch_tik{TIK_NUM}_")
    ])
    
    success_machines = []
    fail_machines = []
    
    if batch_dirs:
        latest_batch = os.path.join(RUNTIME_ROOT, "batch-runs", batch_dirs[-1])
        for m in machines:
            out_log = os.path.join(latest_batch, f"machine-{m}.out.log")
            if os.path.exists(out_log):
                try:
                    with open(out_log, "r", encoding="utf-8", errors="ignore") as f:
                        log_content = f.read()
                    if "AVATAR_CONFIRMED" in log_content or "AVATAR_UPLOAD_COMPLETED" in log_content or "AVATAR_ALREADY_PRESENT" in log_content or "status\": \"success" in log_content.lower():
                        success_machines.append(m)
                    else:
                        m_err = re.findall(r"\[ERROR\]\s*(.+)", log_content)
                        reason = m_err[-1][:50] if m_err else "FAIL"
                        fail_machines.append((m, reason))
                except Exception:
                    fail_machines.append((m, "LOG_READ_ERROR"))
            else:
                fail_machines.append((m, "NO_LOG"))
    
    # Format report
    print("\n================ BÁO CÁO TỔNG KẾT UPLOAD AVATAR CA TỐI (TIK 5) ================")
    print(f"• Tổng máy chạy: {len(machines)}")
    print(f"• Success ({len(success_machines)}): {success_machines}")
    if fail_machines:
        fail_summary = ", ".join(f"M{m} ({r})" for m, r in fail_machines)
        print(f"• Fail ({len(fail_machines)}): {fail_summary}")
    else:
        print(f"• Fail (0): None")
    print(f"• Thời gian thực thi: {duration_min} phút")
    print("================================================================================")


if __name__ == "__main__":
    wait_for_feed_completion()
    run_avatar_batch()
