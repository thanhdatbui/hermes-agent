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
import logging
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger("post_evening_avatar_watchdog")
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)

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
        target_tiks = [1, 2, 3, 4, 5, 6, 7, 8]
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
    prefix = "morning" if 6 <= now_dt.hour < 14 else "evening"
    date_str = (now_dt - timedelta(days=1)).strftime("%Y-%m-%d") if now_dt.hour < 6 else now_dt.strftime("%Y-%m-%d")
    return f"{date_str}_{prefix}"


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
    """Mở cuốn chiếu an toàn sau ca nuôi acc:
    - Ca tối: sau P2 (20:15 -> 23:45)
    - Ca sáng: sau Ca 1 P2 (08:30 -> 11:15)
    """
    h, m = now_dt.hour, now_dt.minute
    if h in (21, 22):
        return True
    if h == 20 and m >= 15:
        return True
    if h == 23 and m <= 45:
        return True
    if (h == 8 and m >= 30) or h in (9, 10) or (h == 11 and m <= 15):
        return True
    return False


def is_after_evening_window(now_dt: datetime) -> bool:
    """Hết khung giờ ca tối (sau 23:45 đến 04:00 sáng) hoặc sau khung sáng (11:15 đến 11:35)."""
    h, m = now_dt.hour, now_dt.minute
    if h == 23 and m > 45:
        return True
    if 0 <= h < 4:
        return True
    if h == 11 and 15 < m <= 35:
        return True
    return False


def count_active_locks() -> int:
    """Đếm số device locks còn fresh (< 45 phút / 2700s) và active/running/queued/queued_v2."""
    lock_dirs = [
        LOCK_DIR,
        Path(os.path.expanduser(r"~\AppData\Local\automation-core\device-locks")),
    ]
    cur_time = time.time()
    count = 0
    seen_files: set[str] = set()
    for ldir in lock_dirs:
        if not ldir.exists():
            continue
        try:
            for f in ldir.iterdir():
                if f.name in seen_files:
                    continue
                if f.is_file() and f.suffix == ".json" and (
                    f.name.startswith("machine_") or f.name.startswith("serial_")
                ):
                    try:
                        if (cur_time - f.stat().st_mtime) < 2700:
                            data = json.loads(f.read_text(encoding="utf-8"))
                            st = data.get("status")
                            if st in ("active", "running", "queued", "queued_v2") or (st == "blocked" and data.get("owner_active", True) is not False):
                                seen_files.add(f.name)
                                count += 1
                    except Exception:
                        pass
                elif f.is_file() and f.suffix == ".lock":
                    try:
                        if (cur_time - f.stat().st_mtime) < 2700:
                            seen_files.add(f.name)
                            count += 1
                    except Exception:
                        pass
        except Exception:
            pass
    return count
def is_feed_session_finished_for_window(now_dt: datetime) -> bool:
    today_str = now_dt.strftime("%Y-%m-%d")
    reported_file = Path(r"D:\Taadaa\runtime\kibe\cron-state\feed_session_reported.json")
    if not reported_file.is_file():
        return False
    try:
        data = json.loads(reported_file.read_text(encoding="utf-8"))
        sessions = set(data.get("reported_sessions", []))
        if 6 <= now_dt.hour < 14:
            return f"{today_str}_ca1_phien2" in sessions or f"{today_str}_ca1" in sessions
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


def rescan_completed_machines(machines: list[int] | None = None, timeout_seconds: int = 180) -> bool:
    """Gọi tiktok_account_tracker.py cập nhật snapshot DB cho các máy vừa chạy xong."""
    tracker_script = Path(r"D:\Taadaa\tools\tiktok_account_tracker.py")
    if not tracker_script.exists():
        sys.stderr.write(f"Tracker script not found: {tracker_script}\n")
        return False

    py_exe = Path(r"D:\Taadaa\python-envs\automation\Scripts\python.exe")
    python_bin = str(py_exe) if py_exe.exists() else sys.executable

    cmd = [python_bin, str(tracker_script)]
    machine_count = 0
    if machines:
        unique_machines = sorted(list(set(machines)))
        cmd.extend(["--machines", ",".join(str(m) for m in unique_machines), "--workers", "10"])
        machine_count = len(unique_machines)

    start_time = time.time()
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        elapsed = time.time() - start_time
        stdout_clean = (res.stdout or "").strip()
        stderr_clean = (res.stderr or "").strip()

        if res.returncode == 0:
            target_desc = f"{machine_count} máy" if machine_count > 0 else "toàn bộ"
            logger.info(f"[TRACKER RESCAN] Hoàn tất cập nhật DB cho {target_desc} (exit: 0, duration: {elapsed:.2f}s).")
            # Rescan thành công: IM LẶNG hoàn toàn trên stdout theo đúng nguyên tắc watchdog (tránh cron spam Telegram)
            return True
        else:
            err_msg = (
                f"[TRACKER RESCAN] Error (exit {res.returncode}, duration: {elapsed:.2f}s)\n"
                f"[TRACKER RESCAN stderr]:\n{stderr_clean or '<empty>'}"
            )
            logger.error(err_msg)
            return False
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[TRACKER RESCAN] Failed to run rescan after {elapsed:.2f}s: {e}")
        return False


def get_tik_avatar_stats(
    tik: int,
    workbook_dir: Path | None = None,
    host_context: dict | None = None,
) -> dict:
    """Lấy danh sách máy chưa có avatar từ SQLite database tiktok_tracker.db có lọc theo host_id.
    Fallback đọc Excel workbook nếu SQLite database lỗi hoặc không mở được.
    """
    ctx = host_context or get_host_context()
    host_id = ctx.get("host_id", "kibe").lower()
    db_path = Path(ctx.get("db_path", r"D:\Taadaa\data\tiktok_tracker.db"))

    if db_path.exists():
        try:
            if host_id == "admin":
                query = """
                WITH Ranked AS (
                    SELECT s.username, s.status, s.has_avatar,
                           ROW_NUMBER() OVER (PARTITION BY s.username ORDER BY s.id DESC) as rn
                    FROM snapshots s
                )
                SELECT m.may, r.has_avatar, r.status
                FROM farm_account_info m
                LEFT JOIN Ranked r ON m.username = r.username AND r.rn = 1
                WHERE m.tik = ? AND (m.host_id = ? OR m.may >= ?)
                ORDER BY m.may
                """
                params = (tik, "admin", 200)
            else:
                query = """
                WITH Ranked AS (
                    SELECT s.username, s.status, s.has_avatar,
                           ROW_NUMBER() OVER (PARTITION BY s.username ORDER BY s.id DESC) as rn
                    FROM snapshots s
                )
                SELECT m.may, r.has_avatar, r.status
                FROM farm_account_info m
                LEFT JOIN Ranked r ON m.username = r.username AND r.rn = 1
                WHERE m.tik = ? AND (m.host_id = ? OR m.host_id IS NULL OR m.host_id = ?) AND m.may < ?
                ORDER BY m.may
                """
                params = (tik, "kibe", "", 200)

            with sqlite3.connect(str(db_path), timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()

            if rows:
                unuploaded = []
                uploaded_count = 0
                for may, has_avatar, _st in rows:
                    if has_avatar == 1:
                        uploaded_count += 1
                    else:
                        unuploaded.append(may)
                return {
                    "unuploaded": sorted(list(set(unuploaded))),
                    "uploaded_count": uploaded_count,
                    "total_accounts": len(rows),
                }
        except Exception as e:
            sys.stderr.write(f"Error querying tiktok_tracker.db for Tik {tik}: {e}\n")

    wb_base = workbook_dir or ctx.get("workbook_dir") or WORKBOOK_DIR
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


def get_unuploaded_machines(
    tik: int,
    workbook_dir: Path | None = None,
    host_context: dict | None = None,
) -> list[int]:
    return get_tik_avatar_stats(tik, workbook_dir=workbook_dir, host_context=host_context)["unuploaded"]


def get_tik_avatar_status(
    tik: int,
    workbook_dir: Path | None = None,
    host_context: dict | None = None,
) -> tuple[int, list[int]]:
    st = get_tik_avatar_stats(tik, workbook_dir=workbook_dir, host_context=host_context)
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


def collect_recent_batch_results(
    tik: int,
    machines: list[int] | None = None,
    batch_runs_dir: Path | None = None,
) -> tuple[list[int], dict[str, list[int]]]:
    base_dir = batch_runs_dir or Path(r"D:\CodexRuntime\tiktok-video\batch-runs")
    if not base_dir.exists():
        return [], {}
    pattern = f"batch_tik{tik}_*"
    try:
        matching_dirs = sorted(base_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    except Exception:
        return [], {}
    if not matching_dirs:
        return [], {}
    summary_file = matching_dirs[0] / "summary.csv"
    if not summary_file.exists():
        return [], {}
    succeeded = []
    failed_by_reason = {}
    target_set = set(machines) if machines else None
    try:
        with open(summary_file, mode="r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                m_val = row.get("Machine") or row.get("machine_id") or row.get("may")
                if not m_val: continue
                try: m = int(m_val)
                except Exception: continue
                if target_set is not None and m not in target_set: continue
                status = (row.get("Status") or "").strip()
                verified = (row.get("Verified") or "").strip().lower() == "true"
                reason_raw = (row.get("Reason") or "").strip()
                report_path = (row.get("Report") or "").strip()
                if verified or status in ("AVATAR_SMOKE_SUCCESS", "SUCCESS"):
                    succeeded.append(m)
                    continue
                err_code = ""
                if report_path and Path(report_path).exists():
                    try:
                        with open(report_path, mode="r", encoding="utf-8") as rf:
                            rd = json.load(rf)
                            err_msg = rd.get("error") or rd.get("avatar_error") or ""
                            mm = re.search(r"\[([A-Z0-9_]+)\]", str(err_msg))
                            if mm: err_code = mm.group(1)
                    except (json.JSONDecodeError, OSError) as e:
                        logger.debug("Cannot parse report json %s: %s", report_path, e)
                if not err_code:
                    mm = re.search(r"\[([A-Z0-9_]+)\]", reason_raw)
                    if mm:
                        err_code = mm.group(1)
                    elif reason_raw:
                        err_code = reason_raw
                    elif status:
                        err_code = status
                    else:
                        err_code = "UNKNOWN_ERROR"
                failed_by_reason.setdefault(err_code, []).append(m)
    except Exception as e:
        logger.warning(f"[WATCHDOG] Error reading batch summary: {e}")
    for k in failed_by_reason:
        failed_by_reason[k] = sorted(list(set(failed_by_reason[k])))
    succeeded_sorted = sorted(list(set(succeeded)))
    logger.info(
        "[WATCHDOG] Batch Tik %s telemetry: succeeded=%d, failed=%d, reasons=%s",
        tik,
        len(succeeded_sorted),
        sum(len(m) for m in failed_by_reason.values()),
        failed_by_reason,
    )
    return succeeded_sorted, failed_by_reason

def check_batch_status(state: dict, state_file: Path | None = None) -> bool:
    """Kiểm tra batch đang chạy. Trả về True nếu vẫn đang chạy ngầm."""
    running = state.get("running_batch")
    if not running:
        return False

    start_time = running.get("start_time", 0)

    # Nếu process vẫn còn sống và chưa quá 45 phút -> Vẫn đang chạy
    if is_powershell_batch_alive() and (time.time() - start_time) < 2700:
        return True

    # Process đã xong -> Kích hoạt rescan DB và thu thập kết quả ca
    completed_machines = running.get("machines", [])
    tik = running.get("tik")
    if completed_machines:
        try:
            rescan_completed_machines(completed_machines)
        except Exception as e:
            logger.error(f"[WATCHDOG] Rescan completed machines failed: {e}")
    if tik and completed_machines:
        try:
            succeeded, failed_by_reason = collect_recent_batch_results(tik, completed_machines)
            sess_key = get_session_key(now_hcmc())
            if state.get("active_session_key") != sess_key:
                state["active_session_key"] = sess_key
                state["session_uploaded_machines"] = []
                state["session_failed_by_reason"] = {}
            cur_up = set(state.get("session_uploaded_machines", []))
            cur_up.update(succeeded)
            state["session_uploaded_machines"] = sorted(list(cur_up))
            cur_failed = state.get("session_failed_by_reason", {})
            for r_code, m_list in failed_by_reason.items():
                m_set = set(cur_failed.get(r_code, []))
                m_set.update(m_list)
                m_set.difference_update(cur_up)
                if m_set:
                    cur_failed[r_code] = sorted(list(m_set))
                elif r_code in cur_failed:
                    del cur_failed[r_code]
            state["session_failed_by_reason"] = cur_failed
        except Exception as e:
            logger.error(f"[WATCHDOG] Collect recent batch results failed: {e}")
    state["running_batch"] = None
    save_state(state, state_file=state_file)
    return False


def format_report_html(
    host_id: str,
    all_done: bool,
    stats_by_tik: dict[int, dict],
    target_tiks: list[int] | None = None,
    now_dt: datetime | None = None,
    stats_by_cluster: dict[str, dict] | None = None,
    session_stats: dict | None = None,
) -> str:
    """Định dạng template báo cáo Farm Alert. Hỗ trợ gộp toàn farm 2 cụm Kibe & Admin gọn gàng, sạch sẽ."""
    if now_dt is None:
        now_dt = now_hcmc()

    # Backward compatibility cho callers truyền unuploaded dạng dict[int, list[int]]
    if stats_by_tik:
        first_val = next(iter(stats_by_tik.values()))
        if isinstance(first_val, list):
            stats_by_tik = {
                tik: {
                    "unuploaded": stats_by_tik.get(tik, []),
                    "uploaded_count": 80 - len(stats_by_tik.get(tik, [])),
                    "total_accounts": 80,
                }
                for tik in (target_tiks or list(stats_by_tik.keys()))
            }


    session_lines = []
    is_morning = 6 <= now_dt.hour < 14
    ca_name = "ca sáng nay" if is_morning else "ca tối nay"
    cutoff_desc = "sau 11:15" if is_morning else "sau 23:30"
    shift_label = "ca sáng" if is_morning else "ca tối"

    if session_stats:
        sess_up = session_stats.get("session_uploaded_machines", [])
        sess_fail = session_stats.get("session_failed_by_reason", {})
        total_fail = sum(len(m_list) for m_list in sess_fail.values())
        if sess_up or sess_fail:
            session_lines.append(f"• Kết quả {ca_name}: Thành công +{len(sess_up)} acc mới | Lỗi {total_fail} máy")
        elif all_done or (stats_by_cluster and tot_miss == 0):
            session_lines.append(f"• Kết quả {ca_name}: Hoàn tất 100%, không ghi nhận lỗi.")
        if sess_fail:
            session_lines.append(f"📋 CHI TIẾT CỤM LỖI {shift_label.upper()} NAY:")
            for r_code, m_list in sorted(sess_fail.items()):
                m_str = ", ".join(map(str, m_list[:10]))
                if len(m_list) > 10: m_str += f"... (+{len(m_list)-10})"
                session_lines.append(f"  ❌ [{r_code}] ({len(m_list)} máy): {m_str}")
    # Nếu có stats_by_cluster -> Báo cáo gộp TOÀN FARM (định dạng sạch, không lộ tag HTML)
    if stats_by_cluster:
        tot_up = 0
        tot_acc = 0
        tot_miss = 0
        cluster_blocks = []

        # Thứ tự hiển thị: kibe trước, admin sau
        cluster_order = [
            ("kibe", "FARM KIBE - MÁY 1-80", [5, 6, 7, 8, 3, 4]),
            ("admin", "FARM ADMIN - MÁY 201-280", [1, 2, 3, 4, 5, 6, 7, 8]),
        ]

        for c_id, c_label, c_tiks in cluster_order:
            if c_id not in stats_by_cluster:
                continue
            c_stats = stats_by_cluster[c_id]
            c_up = sum(c_stats.get(t, {}).get("uploaded_count", 0) for t in c_tiks)
            c_acc = sum(c_stats.get(t, {}).get("total_accounts", 0) for t in c_tiks)
            c_un = sum(len(c_stats.get(t, {}).get("unuploaded", [])) for t in c_tiks)
            c_pct = (c_up / c_acc * 100) if c_acc > 0 else 0.0

            tot_up += c_up
            tot_acc += c_acc
            tot_miss += c_un

            c_lines = [
                f"🏢 【{c_label}】: Đã có {c_up}/{c_acc} ({c_pct:.1f}%), còn {c_un} máy"
            ]

            done_tiks = []
            pending_lines = []

            for t in c_tiks:
                st = c_stats.get(t, {})
                un = st.get("unuploaded", [])
                up = st.get("uploaded_count", 0)
                tot = st.get("total_accounts", 0)
                pct = (up / tot * 100) if tot > 0 else 0.0

                if tot == 0:
                    continue
                elif un:
                    preview = ", ".join(map(str, un[:10]))
                    suffix = f"... (+{len(un)-10})" if len(un) > 10 else ""
                    pending_lines.append(
                        f"  • Tik {t}: Đã có {up}/{tot} ({pct:.1f}%) — còn {len(un)} máy ({preview}{suffix})"
                    )
                else:
                    done_tiks.append(f"Tik {t}")

            if pending_lines:
                c_lines.extend(pending_lines)
            if done_tiks:
                c_lines.append(f"  • Hoàn tất 100%: {', '.join(done_tiks)}")

            cluster_blocks.append("\n".join(c_lines))

        tot_pct = (tot_up / tot_acc * 100) if tot_acc > 0 else 0.0
        if all_done or tot_miss == 0:
            title = "🎉 [FARM REPORT][TOÀN FARM] HOÀN TẤT UP AVATAR CHO CÁC ACC ĐÃ CÓ NICK"
            status_line = f"• Trạng thái: Tất cả các acc hiện có nick đã được up avatar ({tot_up}/{tot_acc} acc)"
        else:
            title = "⏰ [FARM REPORT][TOÀN FARM] BÁO CÁO UP AVATAR: HẾT KHUNG GIỜ"
            status_line = f"• Trạng thái: Hết khung giờ {shift_label} ({cutoff_desc}) — Đã có: {tot_up}/{tot_acc} acc ({tot_pct:.1f}%), còn {tot_miss} máy chưa up"

        lines = [
            title,
            f"• Thời gian: {now_dt.strftime('%H:%M:%S %d/%m/%Y')}",
            status_line,
        ] + session_lines + ["", "\n\n".join(cluster_blocks)]
        return "\n".join(lines)

    # Chế độ báo cáo đơn cụm (backward-compatible cho unit test)
    if target_tiks is None:
        target_tiks = list(stats_by_tik.keys())

    total_unuploaded = sum(len(stats_by_tik.get(tik, {}).get("unuploaded", [])) for tik in target_tiks)
    total_uploaded = sum(stats_by_tik.get(tik, {}).get("uploaded_count", 0) for tik in target_tiks)
    total_accounts = sum(stats_by_tik.get(tik, {}).get("total_accounts", 0) for tik in target_tiks)
    total_pct = (total_uploaded / total_accounts * 100) if total_accounts > 0 else 0.0

    tik_lines = []
    unassigned_tiks = []
    for tik in target_tiks:
        st = stats_by_tik.get(tik, {})
        unuploaded = st.get("unuploaded", [])
        up_cnt = st.get("uploaded_count", 0)
        tot_cnt = st.get("total_accounts", 0)
        pct = (up_cnt / tot_cnt * 100) if tot_cnt > 0 else 0.0

        if tot_cnt == 0:
            unassigned_tiks.append(tik)
        elif unuploaded:
            preview = ",".join(map(str, unuploaded[:15]))
            suffix = f"... (+{len(unuploaded)-15})" if len(unuploaded) > 15 else ""
            tik_lines.append(
                f"• <b>Tik {tik}:</b> Đã có {up_cnt}/{tot_cnt} ({pct:.1f}%) — còn {len(unuploaded)} máy ({preview}{suffix})"
            )
        else:
            tik_lines.append(f"• <b>Tik {tik}:</b> Đã có {up_cnt}/{tot_cnt} (hoàn tất 100%)")

    if unassigned_tiks:
        tik_lines.append(f"• <b>Chưa gán nick:</b> {', '.join(f'Tik {t}' for t in unassigned_tiks)}")

    if (all_done and total_accounts > 0) or (total_unuploaded == 0 and total_accounts > 0):
        title = f"🎉 <b>[FARM REPORT][{host_id.upper()}] HOÀN TẤT UP AVATAR CHO CÁC ACC ĐÃ CÓ NICK</b>"
        status_line = f"• <b>Trạng thái:</b> Tất cả các acc hiện có nick đã được up avatar ({total_uploaded}/{total_accounts} acc)"
    elif total_accounts == 0:
        title = f"⏰ <b>[FARM REPORT][{host_id.upper()}] BÁO CÁO UP AVATAR: CHƯA CÓ NICK</b>"
        status_line = "• <b>Trạng thái:</b> Chưa có tài khoản nào được gán trên các Tik đã cấu hình"
    else:
        title = f"⏰ <b>[FARM REPORT][{host_id.upper()}] BÁO CÁO UP AVATAR: HẾT KHUNG GIỜ</b>"
        status_line = f"• <b>Trạng thái:</b> Hết khung giờ {shift_label} ({cutoff_desc}) — Đã có: {total_uploaded}/{total_accounts} acc ({total_pct:.1f}%), còn {total_unuploaded} máy chưa up"

    lines = [
        title,
        f"• <b>Thời gian:</b> {now_dt.strftime('%H:%M:%S %d/%m/%Y')}",
        status_line,
    ] + session_lines + ["• <b>Chi tiết từng Tik:</b>"] + tik_lines

    return "\n".join(lines)


def report_final_summary(
    state: dict,
    all_done: bool,
    host_context: dict | None = None,
    stats_by_tik: dict[int, dict] | None = None,
) -> None:
    """Gửi DUY NHẤT 1 báo cáo tổng kết khi tất cả Tik hoàn tất 100% hoặc hết khung giờ ca tối.
    Khi host_id == 'kibe', tự động thu thập thêm thống kê từ cụm Admin để xuất báo cáo [TOÀN FARM].
    """
    now = now_hcmc()
    sess_key = get_session_key(now)
    day_str = (now - timedelta(days=1)).strftime("%Y-%m-%d") if now.hour < 6 else now.strftime("%Y-%m-%d")
    if state.get("last_reported_session") in (sess_key, day_str) or state.get("last_reported_date") in (sess_key, day_str):
        return

    ctx = host_context or get_host_context()
    target_tiks = ctx["target_tiks"]
    wb_dir = ctx["workbook_dir"]
    host_id = ctx["host_id"]

    if stats_by_tik is None:
        stats_by_tik = {tik: get_tik_avatar_stats(tik, workbook_dir=wb_dir) for tik in target_tiks}

    # Nếu là Kibe Master -> Tự động tổng hợp cả 2 cụm Kibe và Admin để làm báo cáo [TOÀN FARM]
    stats_by_cluster = None
    if host_id == "kibe":
        admin_tiks = [1, 2, 3, 4, 5, 6, 7, 8]
        admin_wb = Path(os.environ.get("TAADAA_ADMIN_WORKBOOK_ROOT", r"D:\OneDrive\TaadaaData\admin"))
        admin_stats = {
            tik: get_tik_avatar_stats(tik, workbook_dir=admin_wb, host_context={"host_id": "admin", "workbook_dir": admin_wb})
            for tik in admin_tiks
        }
        stats_by_cluster = {
            "kibe": stats_by_tik,
            "admin": admin_stats,
        }

    session_stats = {
        "session_uploaded_machines": state.get("session_uploaded_machines", []),
        "session_failed_by_reason": state.get("session_failed_by_reason", {}),
    }
    report_msg = format_report_html(
        host_id=host_id,
        all_done=all_done,
        stats_by_tik=stats_by_tik,
        target_tiks=target_tiks,
        now_dt=now,
        stats_by_cluster=stats_by_cluster,
        session_stats=session_stats,
    )
    # Gửi báo cáo trực tiếp qua Telegram Bot API (không in STDOUT để tránh rò rỉ cron)
    try:
        send_farm_alert(report_msg)
        logger.info(
            "[WATCHDOG] Đã gửi báo cáo tổng kết %s qua Telegram (all_done=%s, host=%s)",
            sess_key,
            all_done,
            host_id,
        )
    except Exception as e:
        sys.stderr.write(f"[WATCHDOG] send_farm_alert failed: {e}\n")
        logger.error("[WATCHDOG] Thất bại khi gửi báo cáo tổng kết %s: %s", sess_key, e)

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
    stats_by_tik: dict[int, dict] = {}
    all_unuploaded: dict[int, list[int]] = {}
    total_missing = 0
    total_accounts = 0
    for tik in ctx["target_tiks"]:
        st = get_tik_avatar_stats(tik, workbook_dir=ctx["workbook_dir"], host_context=ctx)
        stats_by_tik[tik] = st
        missing = st.get("unuploaded", [])
        all_unuploaded[tik] = missing
        total_missing += len(missing)
        total_accounts += st.get("total_accounts", 0)

    # 4. Nếu tất cả các Tik đã hoàn tất 100% -> Báo cáo duy nhất 1 lần
    if total_missing == 0 and total_accounts > 0:
        report_final_summary(state, all_done=True, host_context=ctx, stats_by_tik=stats_by_tik)
        return 0

    # 5. Nếu đã hết khung giờ ca tối (sau 23:30) -> Báo cáo duy nhất 1 lần tổng kết máy còn tồn
    if after_window:
        report_final_summary(state, all_done=False, host_context=ctx, stats_by_tik=stats_by_tik)
        return 0

    # 6. Trong khung giờ (21:00 -> 23:30) & còn máy chưa up:
    # Kiểm tra an toàn trước khi kích hoạt batch
    if is_feed_active():
        return 0

    if not is_feed_session_finished_for_window(now):
        return 0

    if count_active_locks() > 0:
        return 0

    if is_powershell_batch_alive():
        return 0

    # Kích hoạt batch cho Tik tiếp theo theo cơ chế Round-Robin + Cooldown chống spam
    target_tiks = ctx["target_tiks"]
    cursor = int(state.get("avatar_rr_cursor", 0)) % len(target_tiks)
    ordered_tiks = target_tiks[cursor:] + target_tiks[:cursor]
    recent_launches = state.get("avatar_launch_history", [])

    for offset, tik in enumerate(ordered_tiks):
        missing_machines = all_unuploaded.get(tik, [])
        if missing_machines:
            # Cooldown 15 phút giữa các batch của cùng 1 Tik để tránh spam
            last_for_tik = next((l for l in reversed(recent_launches) if l.get("tik") == tik), None)
            if last_for_tik and (time.time() - last_for_tik.get("timestamp", 0) < 900):
                continue
            trigger_avatar_batch(tik, missing_machines, state, host_context=ctx)
            state["avatar_rr_cursor"] = (cursor + offset + 1) % len(target_tiks)
            save_state(state, state_file=ctx["state_file"])
            return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
