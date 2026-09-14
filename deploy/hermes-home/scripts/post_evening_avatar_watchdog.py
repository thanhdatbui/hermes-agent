"""
Watchdog cuốn chiếu: Tự động chạy upload Avatar cho các acc CHƯA BAO GIỜ ĐƯỢC UP
ngay sau ca tối (khung giờ 21:00 -> 23:45) và CHỈ BÁO CÁO KHI CHẠY XONG vào Farm Alert.

Kênh Farm Alert: Telegram chat_id = -5373649734

Nguyên tắc:
- Quét các workbook theo host_id (admin vs kibe).
- Lọc chính xác các máy mà cột Avatar != 'OK' (chưa bao giờ được up).
- Sau khi kích hoạt batch -> Chạy ngầm im lặng, không spam lúc bắt đầu.
- IM LẶNG hoàn toàn sau mỗi batch lẻ.
- CHỈ BÁO CÁO 1 LẦN DUY NHẤT khi tất cả các Tik hoàn tất 100% HOẶC hết khung giờ ca tối (sau 23:30).
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
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

HCMC = ZoneInfo("Asia/Ho_Chi_Minh")

FARM_ALERT_CHAT_ID = "-5373649734"
LAUNCHER = Path(r"D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1")
TIKTOK_VIDEO_DIR = Path(r"D:\Taadaa\Tiktok-video")
BATCH_RUNS_DIR = Path(r"D:\CodexRuntime\tiktok-video\batch-runs")
LOCK_DIR = Path(os.path.expanduser("~/.codex/device-locks"))


def get_host_context(config_path_override: str | Path | None = None) -> dict:
    """Xác định host context (host_id, target_tiks, workbook_dir, state_file) từ config hoặc fallback kibe."""
    if config_path_override:
        cfg_path = Path(config_path_override)
    else:
        env_cfg = os.environ.get("TAADAA_HOST_CONFIG")
        if env_cfg:
            cfg_path = Path(env_cfg)
        else:
            cfg_path = Path(r"D:\Taadaa\machine-config\kibe.yaml")

    host_id = "kibe"
    if cfg_path.exists():
        try:
            try:
                import yaml
                data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("host_id"):
                    host_id = str(data["host_id"]).strip().lower()
            except Exception:
                for line in cfg_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("host_id:"):
                        host_id = line.split(":", 1)[1].strip().strip('"').strip("'").lower()
                        break
        except Exception:
            pass

    if host_id == "admin":
        target_tiks = [2, 1, 3, 4, 5, 6, 7, 8]
        workbook_dir = Path(r"D:\OneDrive\TaadaaData\admin")
        state_file = Path(r"D:\Taadaa\runtime\admin\cron-state\post_evening_avatar_state.json")
    else:
        host_id = "kibe"
        target_tiks = [5, 6, 7, 8, 3, 4]
        workbook_dir = Path(r"D:\OneDrive\TaadaaData\kibe")
        state_file = Path(r"D:\Taadaa\runtime\kibe\cron-state\post_evening_avatar_state.json")

    return {
        "host_id": host_id,
        "host_config_path": cfg_path,
        "target_tiks": target_tiks,
        "workbook_dir": workbook_dir,
        "state_file": state_file,
    }


# Khởi tạo mặc định theo môi trường hiện tại
HOST_CONTEXT = get_host_context()
HOST_ID = HOST_CONTEXT["host_id"]
TARGET_TIKS = HOST_CONTEXT["target_tiks"]
WORKBOOK_DIR = HOST_CONTEXT["workbook_dir"]
STATE_FILE = HOST_CONTEXT["state_file"]
HOST_CONFIG = HOST_CONTEXT["host_config_path"]


def now_hcmc() -> datetime:
    return datetime.now(HCMC)


def get_session_key(now_dt: datetime) -> str:
    """Xác định session date (nếu chạy qua đêm 00:00 -> 05:00 vẫn tính là ca tối ngày hôm trước)."""
    if now_dt.hour < 6:
        return (now_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    return now_dt.strftime("%Y-%m-%d")


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
    """Khung giờ chạy upload ca tối: 21:00 đến 23:30."""
    h, m = now_dt.hour, now_dt.minute
    if h in (21, 22):
        return True
    if h == 23 and m <= 30:
        return True
    return False


def is_after_evening_window(now_dt: datetime) -> bool:
    """Hết khung giờ ca tối (sau 23:30 đến 04:00 sáng hôm sau)."""
    h, m = now_dt.hour, now_dt.minute
    if h == 23 and m > 30:
        return True
    if 0 <= h < 4:
        return True
    return False


def count_active_locks() -> int:
    """Đếm số device locks active/running/queued/queued_v2."""
    lock_dirs = [
        LOCK_DIR,
        Path(os.path.expanduser(r"~\AppData\Local\automation-core\device-locks")),
    ]
    count = 0
    for ldir in lock_dirs:
        if not ldir.exists():
            continue
        for f in ldir.iterdir():
            if f.is_file() and f.suffix == ".json" and (f.name.startswith("machine_") or f.name.startswith("serial_")):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    st = data.get("status")
                    if st in ("active", "running", "queued", "queued_v2"):
                        count += 1
                    elif st == "blocked" and data.get("owner_active", True) is not False:
                        count += 1
                except Exception:
                    pass
            elif f.is_file() and f.suffix == ".lock":
                count += 1
    return count


def is_ca3_finished(today_str: str) -> bool:
    reported_file = Path(r"D:\Taadaa\runtime\kibe\cron-state\feed_session_reported.json")
    if not reported_file.is_file():
        return False
    try:
        data = json.loads(reported_file.read_text(encoding="utf-8"))
        sessions = set(data.get("reported_sessions", []))
        return f"{today_str}_ca3_phien2" in sessions or f"{today_str}_ca3" in sessions or f"{today_str}_ca3_phien3" in sessions
    except Exception:
        return False


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


def get_tik_avatar_stats(tik: int, workbook_dir: Path | None = None) -> dict:
    """Đọc workbook TikN.xlsx và trả về thống kê avatar:
    {
        'unuploaded': list[int],
        'uploaded_count': int,
        'total_accounts': int
    }
    """
    wb_base = workbook_dir or WORKBOOK_DIR
    fn = f"Tik{tik}.xlsx" if tik != 3 else "tik3.xlsx"
    wb_path = wb_base / fn
    if not wb_path.exists():
        return {"unuploaded": [], "uploaded_count": 0, "total_accounts": 0}

    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(wb_path), data_only=True, read_only=True)
        ws = wb["TaiKhoan"] if "TaiKhoan" in wb.sheetnames else wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return {"unuploaded": [], "uploaded_count": 0, "total_accounts": 0}

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
        uploaded_count = 0
        total_accounts = 0
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

            total_accounts += 1
            ava = r[ava_col] if (ava_col != -1 and ava_col < len(r)) else None
            if ava and str(ava).strip().lower() in ("ok", "present", "true", "done", "yes"):
                uploaded_count += 1
            else:
                unuploaded.append(m_int)

        wb.close()
        return {
            "unuploaded": sorted(list(set(unuploaded))),
            "uploaded_count": uploaded_count,
            "total_accounts": total_accounts
        }
    except Exception as e:
        sys.stderr.write(f"Error reading {fn}: {e}\n")
        return {"unuploaded": [], "uploaded_count": 0, "total_accounts": 0}


def get_unuploaded_machines(tik: int, workbook_dir: Path | None = None) -> list[int]:
    return get_tik_avatar_stats(tik, workbook_dir=workbook_dir)["unuploaded"]


def get_tik_avatar_status(tik: int, workbook_dir: Path | None = None) -> tuple[int, list[int]]:
    st = get_tik_avatar_stats(tik, workbook_dir=workbook_dir)
    return st["total_accounts"], st["unuploaded"]


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


def get_state(state_file: Path | None = None) -> dict:
    target_file = state_file or STATE_FILE
    if target_file.exists():
        try:
            return json.loads(target_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"running_batch": None}


def save_state(st: dict, state_file: Path | None = None):
    target_file = state_file or STATE_FILE
    target_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = target_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(target_file)


def check_batch_status(state: dict, state_file: Path | None = None) -> bool:
    """Kiểm tra batch đang chạy. Trả về True nếu vẫn đang chạy ngầm."""
    running = state.get("running_batch")
    if not running:
        return False

    start_time = running.get("start_time", 0)

    # Nếu process vẫn còn sống và chưa quá 45 phút -> Vẫn đang chạy
    if is_powershell_batch_alive() and (time.time() - start_time) < 2700:
        return True

    # Process đã xong -> Im lặng xóa state running_batch, KHÔNG gửi alert lẻ
    state["running_batch"] = None
    save_state(state, state_file=state_file)
    return False


def format_report_html(
    host_id: str,
    all_done: bool,
    stats_by_tik: dict[int, dict],
    target_tiks: list[int] | None = None,
    now_dt: datetime | None = None,
) -> str:
    """Định dạng template HTML báo cáo Farm Alert chuẩn hóa."""
    if now_dt is None:
        now_dt = now_hcmc()
    if target_tiks is None:
        target_tiks = list(stats_by_tik.keys())

    total_unuploaded = sum(len(stats_by_tik.get(tik, {}).get("unuploaded", [])) for tik in target_tiks)
    total_uploaded = sum(stats_by_tik.get(tik, {}).get("uploaded_count", 0) for tik in target_tiks)
    total_accounts = sum(stats_by_tik.get(tik, {}).get("total_accounts", 0) for tik in target_tiks)
    total_pct = (total_uploaded / total_accounts * 100) if total_accounts > 0 else 0.0

    tik_lines = []
    for tik in target_tiks:
        st = stats_by_tik.get(tik, {})
        unuploaded = st.get("unuploaded", [])
        up_cnt = st.get("uploaded_count", 0)
        tot_cnt = st.get("total_accounts", 0)
        pct = (up_cnt / tot_cnt * 100) if tot_cnt > 0 else 0.0

        if tot_cnt == 0:
            tik_lines.append(f"• <b>Tik {tik}:</b> chưa gán nick (0/80 acc)")
        elif unuploaded:
            preview = ",".join(map(str, unuploaded[:15]))
            suffix = f"... (+{len(unuploaded)-15})" if len(unuploaded) > 15 else ""
            tik_lines.append(
                f"• <b>Tik {tik}:</b> Đã có {up_cnt}/{tot_cnt} ({pct:.1f}%) — còn {len(unuploaded)} máy ({preview}{suffix})"
            )
        else:
            tik_lines.append(f"• <b>Tik {tik}:</b> Đã có {up_cnt}/{tot_cnt} (hoàn tất 100%)")

    if all_done or total_unuploaded == 0:
        title = f"🎉 <b>[FARM REPORT][{host_id.upper()}] HOÀN TẤT UP AVATAR CHO CÁC ACC ĐÃ CÓ NICK</b>"
        status_line = f"• <b>Trạng thái:</b> Tất cả các acc hiện có nick đã được up avatar ({total_uploaded}/{total_accounts} acc)"
    else:
        title = f"⏰ <b>[FARM REPORT][{host_id.upper()}] BÁO CÁO UP AVATAR: HẾT KHUNG GIỜ</b>"
        status_line = f"• <b>Trạng thái:</b> Hết khung giờ ca tối (sau 23:30) — Đã có: {total_uploaded}/{total_accounts} acc ({total_pct:.1f}%), còn {total_unuploaded} máy chưa up"

    lines = [
        title,
        f"• <b>Thời gian:</b> {now_dt.strftime('%H:%M:%S %d/%m/%Y')}",
        status_line,
        "• <b>Chi tiết từng Tik:</b>",
    ] + tik_lines

    return "\n".join(lines)


def report_final_summary(
    state: dict,
    all_done: bool,
    host_context: dict | None = None,
    stats_by_tik: dict[int, dict] | None = None,
) -> None:
    """Gửi DUY NHẤT 1 báo cáo tổng kết khi tất cả Tik hoàn tất 100% hoặc hết khung giờ ca tối."""
    now = now_hcmc()
    sess_key = get_session_key(now)
    if state.get("last_reported_session") == sess_key or state.get("last_reported_date") == sess_key:
        return

    ctx = host_context or get_host_context()
    target_tiks = ctx["target_tiks"]
    wb_dir = ctx["workbook_dir"]
    host_id = ctx["host_id"]

    if stats_by_tik is None:
        stats_by_tik = {tik: get_tik_avatar_stats(tik, workbook_dir=wb_dir) for tik in target_tiks}

    report_msg = format_report_html(
        host_id=host_id,
        all_done=all_done,
        stats_by_tik=stats_by_tik,
        target_tiks=target_tiks,
        now_dt=now,
    )
    # Cronjob no_agent=True tu dong bat stdout (print) gui Telegram Farm Alert, tranh goi send_farm_alert gay gui dup
    print(report_msg)

    state["last_reported_session"] = sess_key
    state["last_reported_date"] = sess_key
    save_state(state, state_file=ctx["state_file"])


def trigger_avatar_batch(tik: int, machines: list[int], state: dict, host_context: dict | None = None) -> bool:
    """Khởi chạy batch upload avatar qua PowerShell background (hoàn toàn im lặng)."""
    ctx = host_context or get_host_context()
    machine_list_str = ",".join(str(m) for m in machines)
    cmd = [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(LAUNCHER),
        "-Tik", str(tik),
        "-ForceAvatarMachineList", machine_list_str,
        "-MaxParallel", "30",
        "-HostConfigPath", str(ctx["host_config_path"]),
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
        save_state(state, state_file=ctx["state_file"])
        return True
    except Exception as e:
        sys.stderr.write(f"post_evening_avatar: Failed to spawn Tik{tik}: {e}\n")
        return False


def main() -> int:
    ctx = get_host_context()
    now = now_hcmc()
    state = get_state(state_file=ctx["state_file"])

    # 1. Chỉ hoạt động trong khung giờ ca tối hoặc ngay sau ca tối (21:00 -> 04:00)
    in_window = is_post_evening_window(now)
    after_window = is_after_evening_window(now)
    if not (in_window or after_window):
        return 0

    # 2. Kiểm tra tiến trình batch hiện tại (nếu có)
    if check_batch_status(state, state_file=ctx["state_file"]):
        # Vẫn đang có batch chạy ngầm
        return 0

    # 3. Thu thập danh sách máy chưa up avatar cho tất cả các Tik
    all_unuploaded: dict[int, list[int]] = {}
    total_missing = 0
    for tik in ctx["target_tiks"]:
        missing = get_unuploaded_machines(tik, workbook_dir=ctx["workbook_dir"])
        all_unuploaded[tik] = missing
        total_missing += len(missing)

    # 4. Nếu tất cả các Tik đã hoàn tất 100% -> Báo cáo duy nhất 1 lần
    if total_missing == 0:
        report_final_summary(state, all_done=True, host_context=ctx)
        return 0

    # 5. Nếu đã hết khung giờ ca tối (sau 23:30) -> Báo cáo duy nhất 1 lần tổng kết máy còn tồn
    if after_window:
        report_final_summary(state, all_done=False, host_context=ctx)
        return 0

    # 6. Trong khung giờ (21:00 -> 23:30) & còn máy chưa up:
    # Kiểm tra an toàn trước khi kích hoạt batch
    if is_feed_active():
        return 0

    today_str = now.strftime("%Y-%m-%d")
    if not is_ca3_finished(today_str):
        return 0

    if count_active_locks() > 0:
        return 0

    if is_powershell_batch_alive():
        return 0

    # Kích hoạt batch cho Tik đầu tiên còn acc chưa bao giờ được up
    for tik in ctx["target_tiks"]:
        missing_machines = all_unuploaded.get(tik, [])
        if missing_machines:
            trigger_avatar_batch(tik, missing_machines, state, host_context=ctx)
            return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
