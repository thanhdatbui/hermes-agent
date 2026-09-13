"""
Watchdog cuốn chiếu: Tự động chạy upload Avatar cho các acc CHƯA BAO GIỜ ĐƯỢC UP
ngay sau ca tối (khung giờ 21:00 -> 23:45) và CHỈ BÁO CÁO KHI CHẠY XONG vào Farm Alert.

Kênh Farm Alert: Telegram chat_id = -5373649734

Nguyên tắc:
- Quét các workbook Tik5, Tik6, Tik3, Tik4.
- Lọc chính xác các máy mà cột Avatar != 'OK' (chưa bao giờ được up).
- Sau khi kích hoạt batch -> Chạy ngầm im lặng, không spam lúc bắt đầu.
- CHỈ KHI BATCH HOÀN TẤT:
  + Đọc kết quả summary.csv & đối soát workbook thực tế.
  + Gửi DUY NHẤT 1 tin nhắn báo cáo kết quả hoàn thành vào Farm Alert (-5373649734).
  + Xóa trạng thái để nhịp sau quét Tik tiếp theo.
"""
from __future__ import annotations

import csv
import glob
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HCMC = ZoneInfo("Asia/Ho_Chi_Minh")

FARM_ALERT_CHAT_ID = "-5373649734"
STATE_FILE = Path(r"D:\Taadaa\runtime\kibe\cron-state\post_evening_avatar_state.json")
LAUNCHER = Path(r"D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1")
HOST_CONFIG = Path(r"D:\Taadaa\machine-config\kibe.yaml")
TIKTOK_VIDEO_DIR = Path(r"D:\Taadaa\Tiktok-video")
BATCH_RUNS_DIR = Path(r"D:\CodexRuntime\tiktok-video\batch-runs")
LOCK_DIR = Path(os.path.expanduser("~/.codex/device-locks"))
WORKBOOK_DIR = Path(r"D:\OneDrive\TaadaaData\kibe")

TARGET_TIKS = [5, 6, 7, 8, 3, 4]


def now_hcmc() -> datetime:
    return datetime.now(HCMC)


def get_telegram_bot_token() -> str | None:
    """Lấy Telegram Bot Token từ env hoặc file .env của Hermes."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if token:
        return token
    env_file = Path.home() / "AppData/Local/hermes/.env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return None


def send_farm_alert(text: str) -> bool:
    """Gửi tin nhắn thông báo vào nhóm Farm Alert."""
    token = get_telegram_bot_token()
    if not token:
        print("[ALERT] Không tìm thấy TELEGRAM_BOT_TOKEN, in console:")
        print(text)
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": FARM_ALERT_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception as e:
        sys.stderr.write(f"send_farm_alert error: {e}\n")
        return False


def is_post_evening_window(now_dt: datetime) -> bool:
    """Khung giờ ngay sau ca tối: 21:00 đến 23:30."""
    h, m = now_dt.hour, now_dt.minute
    if h in (21, 22):
        return True
    if h == 23 and m <= 30:
        return True
    return False


def count_active_locks() -> int:
    """Đếm số device locks còn fresh (< 45 phút)."""
    if not LOCK_DIR.exists():
        return 0
    cur_time = time.time()
    count = 0
    for f in LOCK_DIR.iterdir():
        if f.is_file() and f.suffix == ".json" and (
            f.name.startswith("machine_") or f.name.startswith("serial_")
        ):
            try:
                if (cur_time - f.stat().st_mtime) < 2700:
                    count += 1
            except Exception:
                pass
    return count


def is_feed_active() -> bool:
    """Kiểm tra có feed runner nào đang chạy không."""
    try:
        ps_cmd = (
            'Get-CimInstance Win32_Process '
            '-Filter "Name like \'python%\' or Name like \'powershell%\'" '
            '| Select-Object -ExpandProperty CommandLine'
        )
        p = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15,
        )
        cmdlines = p.stdout.lower()
        signatures = [
            "run-feed-session.ps1",
            "multi_machine_feed_session",
            "run_tiktok.py",
            "night_chain_reg_pipeline"
        ]
        for sig in signatures:
            if sig in cmdlines:
                return True
    except Exception:
        pass
    return False


def get_unuploaded_machines(tik: int) -> list[int]:
    """Đọc workbook TikN.xlsx và lọc ra các máy CHƯA BAO GIỜ được up avatar (Avatar != 'OK')."""
    fn = f"Tik{tik}.xlsx" if tik != 3 else "tik3.xlsx"
    wb_path = WORKBOOK_DIR / fn
    if not wb_path.exists():
        return []

    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(wb_path), data_only=True, read_only=True)
        ws = wb["TaiKhoan"] if "TaiKhoan" in wb.sheetnames else wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []

        header = [str(c or "").strip().lower() for c in rows[0]]
        id_col = -1
        ava_col = -1
        for idx, h in enumerate(header):
            if h in ("id", "id tiktok", "tiktok id"):
                id_col = idx
            if "avatar" in h:
                ava_col = idx

        if id_col == -1:
            id_col = 2

        unuploaded = []
        for r in rows[1:]:
            m_val = r[0]
            if m_val is None:
                continue
            try:
                m_int = int(m_val)
            except (ValueError, TypeError):
                continue

            nick = r[id_col] if id_col < len(r) else None
            if not nick or str(nick).strip().lower() in ("none", "null", "", "0", "missing_id"):
                continue

            ava = r[ava_col] if (ava_col != -1 and ava_col < len(r)) else None
            if not ava or str(ava).strip().lower() not in ("ok", "present", "true", "done", "yes"):
                unuploaded.append(m_int)

        wb.close()
        return sorted(list(set(unuploaded)))
    except Exception as e:
        sys.stderr.write(f"Error reading {fn}: {e}\n")
        return []


def is_powershell_batch_alive() -> bool:
    """Kiểm tra có process batch upload avatar đang thực thi không."""
    try:
        ps_cmd = (
            'Get-CimInstance Win32_Process '
            '-Filter "Name like \'powershell%\'" '
            '| Select-Object -ExpandProperty CommandLine'
        )
        p = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15,
        )
        cmdlines = p.stdout.lower()
        return "run_tiktok_upload_avatar.ps1" in cmdlines or "run_tiktok_upload_batch.ps1" in cmdlines
    except Exception:
        return False


def get_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"running_batch": None}


def save_state(st: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


def check_and_report_completed_batch(state: dict) -> bool:
    """Nếu có batch đang chạy, kiểm tra xem đã kết thúc chưa để tổng kết và gửi Farm Alert."""
    running = state.get("running_batch")
    if not running:
        return False

    tik = running.get("tik")
    machines = running.get("machines", [])
    start_time = running.get("start_time", 0)

    # Nếu process vẫn còn sống và chưa quá 45 phút -> Vẫn đang chạy
    if is_powershell_batch_alive() and (time.time() - start_time) < 2700:
        return True

    # Process đã xong -> Tìm folder batch mới nhất của Tik này
    pattern = str(BATCH_RUNS_DIR / f"batch_tik{tik}_*")
    dirs = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)

    # Xác định lại bằng cách đọc workbook thực tế
    remaining = get_unuploaded_machines(tik)
    completed = [m for m in machines if m not in remaining]
    failed = [m for m in machines if m in remaining]

    # Báo cáo kết quả duy nhất khi đã chạy xong
    duration_min = max(1, int((time.time() - start_time) / 60))
    lines = [
        f"🔔 <b>[FARM ALERT] BÁO CÁO TIẾN ĐỘ UP AVATAR ROW {tik}</b>",
        f"• <b>Thời gian hoàn thành:</b> {now_hcmc().strftime('%H:%M:%S %d/%m/%Y')} (thời lượng {duration_min}p)",
        f"• <b>Tổng số acc cần up:</b> {len(machines)} máy",
        f"• <b>Thành công:</b> {len(completed)} máy",
    ]
    if completed:
        lines.append(f"  └ <i>Máy:</i> {','.join(map(str, sorted(completed)))}")
    lines.append(f"• <b>Chưa hoàn tất:</b> {len(failed)} máy")
    if failed:
        lines.append(f"  └ <i>Máy:</i> {','.join(map(str, sorted(failed)))}")

    report_msg = "\n".join(lines)
    send_farm_alert(report_msg)
    print(report_msg)

    # Xóa state running_batch để nhịp sau quét Tik tiếp theo
    state["running_batch"] = None
    save_state(state)
    return False


def trigger_avatar_batch(tik: int, machines: list[int], state: dict) -> bool:
    """Khởi chạy batch upload avatar qua PowerShell background (hoàn toàn im lặng)."""
    machine_list_str = ",".join(str(m) for m in machines)
    cmd = [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(LAUNCHER),
        "-Tik", str(tik),
        "-ForceAvatarMachineList", machine_list_str,
        "-MaxParallel", "20",
        "-HostConfigPath", str(HOST_CONFIG),
    ]

    try:
        kwargs = {
            "cwd": str(TIKTOK_VIDEO_DIR),
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "close_fds": True,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000200  # CREATE_NO_WINDOW
        proc = subprocess.Popen(cmd, **kwargs)

        # Lưu state đang chạy, KHÔNG gửi tin nhắn bắt đầu
        state["running_batch"] = {
            "tik": tik,
            "machines": machines,
            "start_time": time.time(),
            "pid": proc.pid,
        }
        save_state(state)
        return True
    except Exception as e:
        sys.stderr.write(f"post_evening_avatar: Failed to spawn Tik{tik}: {e}\n")
        return False


def main() -> int:
    now = now_hcmc()
    state = get_state()

    # 1. Kiểm tra nếu có batch trước đó vừa hoàn tất -> Báo cáo vào Farm Alert
    if check_and_report_completed_batch(state):
        return 0

    # 2. Gate khung giờ: Chỉ chạy ngay sau ca tối (21:00 -> 23:30)
    if not is_post_evening_window(now):
        return 0

    # 3. Gate tiến trình feed
    if is_feed_active():
        return 0

    # 4. Gate device-locks
    if count_active_locks() > 5:
        return 0

    # 5. Gate batch concurrency
    if is_powershell_batch_alive():
        return 0

    # 6. Duyệt tìm Tik đầu tiên còn acc chưa bao giờ được up
    for tik in TARGET_TIKS:
        missing_machines = get_unuploaded_machines(tik)
        if missing_machines:
            trigger_avatar_batch(tik, missing_machines, state)
            return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
