#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
post_evening_gpm_login_watchdog.py

Watchdog tự động Login Gmail lên GPMLogin sau Ca 3 (Tối).
Chạy sau post-evening-avatar-watchdog kết thúc (hoặc sau 22:00).

NGUỒN TỰA CHỌN ACC (ưu tiên theo thứ tự):
  1. Gmail cooldown_7days đã hết hạn trong oauth_pipeline_status.json.
  2. Gmail LIVE trong master_gmail_manager.xlsx chưa có trong Group 10 (chưa login GPM).

CONSTRAINT PROXY (BẮT BUỘC):
  - Mỗi proxy port chỉ được login TỐI ĐA 2 máy/ngày (2 acc).
  - Mỗi máy (mid) chỉ login ĐÚNG 1 lần/ngày.

CONCURRENCY: 10 workers song song, stagger 2s.
KHUNG GIỜ: 21:30 - 23:45 (HCM), sau khi avatar cron xong.
"""

from __future__ import annotations

import os
import sys
import json
import glob
import time
import sqlite3
import subprocess
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

HCMC = ZoneInfo("Asia/Ho_Chi_Minh")

STATE_DIR        = Path(r"D:\Taadaa\runtime\kibe\cron-state")
STATE_FILE       = STATE_DIR / "post_evening_gpm_login_state.json"
AVATAR_STATE     = STATE_DIR / "post_evening_avatar_state.json"
LOCK_DIR         = Path(os.path.expanduser("~/.codex/device-locks"))
MANIFEST_DIR     = Path(r"D:\Taadaa\runtime\kibe\cron-state\manifests")
STATUS_JSON      = Path(r"D:\Taadaa\GPM auto\config\oauth_pipeline_status.json")
MASTER_XLSX      = Path(r"D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx")
CLEAN_GMAIL_XLSX = Path(r"D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx")
GPM_DB           = Path(r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db")
GPM_SCRIPT       = Path(r"D:\Taadaa\GPM auto\scripts\run_oauth_s7_pipeline.py")
PYTHON_EXE       = sys.executable

MAX_WORKERS        = 2     # hạ 2 workers theo chỉ thị user để chống checkpoint và nghẽn proxy
MAX_LOGINS_PER_PROXY = 2   # tối đa 2 acc / proxy / ngày
MIN_IDLE_BUFFER_MIN  = 45  # cách ca tiếp theo ít nhất 45 phút

def log(msg: str):
    now_str = datetime.now(HCMC).strftime("%H:%M:%S")
    sys.stderr.write(f"[{now_str}] [GPM-LOGIN] {msg}\n")
    sys.stderr.flush()

def is_within_time_window() -> bool:
    """Cho phép chạy trong các khoảng thời gian rảnh giữa các ca nuôi:
    - Sáng: 07:15 đến 08:45
    - Trưa: 12:00 đến 13:45
    - Tối: 20:15 đến 23:45
    """
    now = datetime.now(HCMC)
    current = now.hour * 60 + now.minute
    morning = 7 * 60 + 15 <= current <= 8 * 60 + 45
    noon = 12 * 60 <= current <= 13 * 60 + 45
    evening = 20 * 60 + 15 <= current <= 23 * 60 + 45
    return morning or noon or evening

def get_current_shift_info() -> tuple[str, str, str]:
    """Trả về thông tin ca hiện tại: (shift_code, shift_label, shift_desc)
    - 07:15 - 08:45 -> ("SANG", "SÁNG", "sáng")
    - 12:00 - 13:45 -> ("TRUA", "TRƯA", "trưa")
    - 20:15 - 23:45 -> ("TOI", "TỐI", "tối")
    - Fallback: < 12 -> SANG, < 18 -> TRUA, else TOI
    """
    now = datetime.now(HCMC)
    current = now.hour * 60 + now.minute
    if 7 * 60 + 15 <= current <= 8 * 60 + 45:
        return ("SANG", "SÁNG", "sáng")
    if 12 * 60 <= current <= 13 * 60 + 45:
        return ("TRUA", "TRƯA", "trưa")
    if 20 * 60 + 15 <= current <= 23 * 60 + 45:
        return ("TOI", "TỐI", "tối")

    if now.hour < 12:
        return ("SANG", "SÁNG", "sáng")
    elif now.hour < 18:
        return ("TRUA", "TRƯA", "trưa")
    else:
        return ("TOI", "TỐI", "tối")

def is_machine_avatar_ready(mid: int | None) -> bool:
    """Kiểm tra máy đã có avatar hoặc đã hoàn tất up avatar trên các file Tik."""
    if not mid:
        return True
    try:
        import openpyxl
        wb_dir = Path(r"D:\OneDrive\TaadaaData\kibe")
        for tik in [5, 6, 7, 8, 3, 4]:
            fn = f"Tik{tik}.xlsx" if tik != 3 else "tik3.xlsx"
            p = wb_dir / fn
            if not p.exists():
                continue
            wb = openpyxl.load_workbook(p, data_only=True, read_only=True)
            ws = wb["TaiKhoan"] if "TaiKhoan" in wb.sheetnames else wb.active
            for r in ws.iter_rows(values_only=True):
                if r and r[0] == mid:
                    # Cột avatar thường ở cuối hoặc cột 12
                    ava = r[12] if len(r) > 12 else None
                    wb.close()
                    if ava and str(ava).strip().lower() in ("ok", "present", "true", "done", "yes"):
                        return True
                    return False
            wb.close()
    except Exception:
        pass
    return True

def is_avatar_done(today_str: str) -> bool:
    """Cuốn chiếu: không chặn toàn farm, luôn cho phép kiểm tra theo máy."""
    return True

def get_all_gpm_emails() -> set[str]:
    """Lấy set email đã có profile trong GPM DB (bất kể GroupId)."""
    emails = set()
    try:
        conn = sqlite3.connect(GPM_DB)
        cur = conn.cursor()
        cur.execute("SELECT Name FROM profiles")
        for (name,) in cur.fetchall():
            m = re.search(r"([a-z0-9._%+\-]+@gmail\.com)", name.lower())
            if m:
                emails.add(m.group(1))
        conn.close()
    except Exception as e:
        log(f"Lỗi đọc GPM DB: {e}")
    return emails

def sync_gpm_profiles_lifecycle():
    """
    Tự động đồng bộ vòng đời profile GPM trước khi lấy candidates:
    1. Quét Master Excel (sheet Kibe_Farm_S7).
    2. DỌN DẸP: Xóa profile GPM của các Gmail DIE / BAN / SUSPENDED.
    3. TẠO MỚI: Tự động sinh profile GPM cho các Gmail LIVE mới chưa có trong GPM DB.
       - Lấy proxy từ cột Proxy trong Excel hoặc PROXYgandienthoai.xlsx.
       - CẤM TUYỆT ĐỐI đòi máy S7 online ADB (tạo profile độc lập trên PC).
    """
    try:
        sys.path.insert(0, r"D:\Taadaa\GPM auto\src")
        from gpm_client import GPMClient
        client = GPMClient()
    except Exception as e:
        log(f"Không thể import GPMClient: {e}")
        return

    # Kiểm tra GPM API có hoạt động không
    if not client.check_health():
        log("GPM API không online, đang khởi động GPMLogin...")
        gpm_exe = Path(r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\GPMLogin.exe")
        if gpm_exe.exists():
            try:
                subprocess.Popen([str(gpm_exe)])
                time.sleep(5)
            except Exception as e:
                log(f"Không thể khởi động GPMLogin: {e}")

    if not client.check_health():
        log("GPM API vẫn offline sau khi thử bật, bỏ qua sync lifecycle vòng này.")
        return

    if not MASTER_XLSX.exists() or not GPM_DB.exists():
        return

    try:
        import openpyxl
        wb = openpyxl.load_workbook(MASTER_XLSX, data_only=True, read_only=True)
        ws = wb["Kibe_Farm_S7"]
        die_emails = set()
        live_candidates = {}  # email -> {mid, raw_proxy, port}

        for r in list(ws.iter_rows(values_only=True))[1:]:
            if not (r and r[1] and "@" in str(r[1])):
                continue
            email = str(r[1]).strip().lower()
            status = str(r[6] or "").strip().upper()
            recovery = str(r[3] or "").strip().lower()
            if "khoale" in email or "khoale" in recovery:
                continue

            mid_str = str(r[7] or "")
            m_mid = re.search(r"(\d+)", mid_str)
            mid = int(m_mid.group(1)) if m_mid else None

            if status in ("DIE", "BAN", "SUSPENDED"):
                die_emails.add(email)
            elif status == "LIVE" and mid:
                raw_proxy = str(r[10] or "").strip()
                m_port = re.search(r":(\d{4,5})", raw_proxy)
                port = m_port.group(1) if m_port else ""
                live_candidates[email] = {
                    "mid": mid,
                    "raw_proxy": raw_proxy,
                    "port": port
                }
        wb.close()

        # Đọc GPM DB
        conn = sqlite3.connect(str(GPM_DB))
        cur = conn.cursor()
        cur.execute("SELECT Id, Name FROM profiles;")
        gpm_profiles = cur.fetchall()
        conn.close()

        existing_gpm_emails = set()
        to_delete = []

        for pid, name in gpm_profiles:
            if not name:
                continue
            for em in re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", name.lower()):
                existing_gpm_emails.add(em)
                if em in die_emails:
                    to_delete.append((pid, name, em))

        # 1. Dọn profile DIE
        deleted_cnt = 0
        for pid, name, em in to_delete:
            try:
                res = client.delete_profile(pid, mode=2)
                if res.get("success"):
                    deleted_cnt += 1
                    log(f"Đã xóa profile DIE: {name} (ID: {pid})")
            except Exception as ex_del:
                log(f"Lỗi xóa profile {name}: {ex_del}")

        # 2. Sinh profile LIVE chưa có (BỎ QUA HOÀN TOÀN KIỂM TRA ADB CỦA S7)
        created_cnt = 0
        for email, info in live_candidates.items():
            if email in existing_gpm_emails:
                continue
            mid = info["mid"]
            port = info["port"]
            raw_proxy = info["raw_proxy"]
            prof_name = f"{mid:02d} - {email} - {port}" if port else f"{mid:02d} - {email}"

            try:
                res = client.create_profile(
                    name=prof_name,
                    raw_proxy=raw_proxy,
                    group_id=1
                )
                if res.get("success"):
                    created_cnt += 1
                    existing_gpm_emails.add(email)
                    log(f"Đã sinh profile GPM mới: {prof_name}")
            except Exception as ex_cr:
                log(f"Lỗi tạo profile {prof_name}: {ex_cr}")

        if deleted_cnt > 0 or created_cnt > 0:
            log(f"[SYNC GPM] Dọn dẹp {deleted_cnt} profile DIE | Sinh mới {created_cnt} profile LIVE.")

    except Exception as e:
        log(f"Lỗi trong sync_gpm_profiles_lifecycle: {e}")

def _load_gmail_clean_creation_dates() -> dict[str, dict]:
    cache = {}
    if CLEAN_GMAIL_XLSX.exists():
        try:
            import openpyxl
            wb = openpyxl.load_workbook(CLEAN_GMAIL_XLSX, data_only=True, read_only=True)
            ws = wb.active
            for r in list(ws.iter_rows(values_only=True))[1:]:
                if r and len(r) > 1 and r[1] and "@" in str(r[1]):
                    em = str(r[1]).strip().lower()
                    created_raw = r[6] if len(r) > 6 else None
                    dob_raw = r[5] if len(r) > 5 else None
                    created_date = None
                    if created_raw:
                        if hasattr(created_raw, "date"):
                            created_date = created_raw.date()
                        elif isinstance(created_raw, str):
                            try:
                                created_date = datetime.fromisoformat(created_raw[:10]).date()
                            except Exception:
                                pass
                    cache[em] = {"created_date": created_date, "has_dob": bool(dob_raw)}
            wb.close()
        except Exception as e:
            log(f"Lỗi đọc {CLEAN_GMAIL_XLSX}: {e}")
    return cache

def _get_live_omniroute_antigravity_emails() -> set[str]:
    """Lấy danh sách các tài khoản Antigravity đang live trực tiếp từ server OmniRoute (:20129)."""
    try:
        import urllib.request
        req = urllib.request.Request('http://127.0.0.1:20129/api/providers')
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            conns = data.get('connections', [])
            emails = set()
            for c in conns:
                if c.get('provider') == 'antigravity':
                    em = (c.get('email') or c.get('name') or '').strip().lower()
                    if em and '@' in em:
                        emails.add(em)
            return emails
    except Exception as e:
        log(f'[OMNI-LIVE-WARN] Không thể lấy live conns từ :20129 ({e}), fallback.')
        return set()


def _get_gpm_profiles_with_google_session() -> set[str]:
    """Kiểm tra các profile GPM đã có sẵn session cookie Google (đã login thành công nhưng chưa OAuth)."""
    emails_with_session = set()
    if not GPM_DB.exists():
        return emails_with_session
    try:
        conn = sqlite3.connect(str(GPM_DB))
        cur = conn.cursor()
        cur.execute('SELECT Name, ProfilePath FROM profiles;')
        rows = cur.fetchall()
        conn.close()

        base_prof_dir = GPM_DB.parent
        for name, ppath in rows:
            if not name or not ppath:
                continue
            ems = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', name.lower())
            if not ems:
                continue
            em = ems[0]
            p_folder = base_prof_dir / ppath
            for cp in [p_folder / 'Default' / 'Network' / 'Cookies', p_folder / 'Default' / 'Cookies']:
                if cp.exists():
                    try:
                        c_conn = sqlite3.connect(str(cp))
                        c_cur = c_conn.cursor()
                        c_cur.execute("SELECT count(*) FROM cookies WHERE host_key LIKE '%google.com' AND name IN ('SID', 'SSID', 'HSID', 'SAPISID')")
                        cnt = c_cur.fetchone()[0]
                        c_conn.close()
                        if cnt >= 2:
                            emails_with_session.add(em)
                            break
                    except Exception:
                        pass
    except Exception as e:
        log(f'[SESSION-CHECK-ERR] Lỗi kiểm tra session cookie GPM: {e}')
    return emails_with_session


def get_candidates(today_str: str, processed: list[str]) -> list[dict]:
    """
    Trả về danh sách candidates cần login:
    - Nhóm 1 (Priority 1): Profile GPM ĐÃ CÓ GOOGLE SESSION COOKIE nhưng chưa có trên OmniRoute -> Ăn ngay không checkpoint.
    - Nhóm 2 (Priority 2): Profile GPM mới/chưa login nhưng đã bồi trust (CHATGPT_READY).
    - Nhóm 3 (Priority 3): Profile GPM chưa nạp OmniRoute, nếu fail trước đó chỉ retry khi đã cooldown >= 24h.
    """
    clean_map    = _load_gmail_clean_creation_dates()
    gpm_emails   = get_all_gpm_emails()
    seen_emails  = set(processed)
    proxy_count  = defaultdict(int)
    candidates   = []

    state = {}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    if state.get("date") == today_str:
        for em in state.get("processed", []):
            seen_emails.add(em)
        for port, cnt in state.get("proxy_count", {}).items():
            proxy_count[port] = cnt

    # Lấy OmniRoute success: kết hợp live API :20129 + file status json
    omniroute_success = _get_live_omniroute_antigravity_emails()
    excluded_emails   = set()
    cooldown_expired  = []

    if STATUS_JSON.exists():
        try:
            data = json.loads(STATUS_JSON.read_text(encoding="utf-8"))
            omniroute_success.update(k.lower() for k in data.get("omniroute_success", {}).keys())
            excluded_emails.update(k.lower() for k in data.get("excluded_khoalee", []))
            excluded_emails.update(k.lower() for k in data.get("wrong_password_or_checkpoint", {}).keys())

            for em, info in data.get("ip_cooling_recaptcha", {}).items():
                r_after = (info.get("retry_after") or "")[:10]
                if r_after > today_str:
                    excluded_emails.add(em.lower())

            for em, info in data.get("cooldown_7days", {}).items():
                em_l = em.lower()
                r_after = (info.get("retry_after") or "")[:10]
                if r_after <= today_str:
                    cooldown_expired.append((em_l, info.get("machine")))
                else:
                    excluded_emails.add(em_l)
        except Exception as e:
            log(f"Lỗi đọc oauth_pipeline_status: {e}")

    # Danh sách profile đã có session cookie Google
    session_emails = _get_gpm_profiles_with_google_session()

    for em_l, mid in cooldown_expired:
        if em_l not in seen_emails and em_l not in omniroute_success and em_l not in excluded_emails and em_l in gpm_emails:
            port = _get_proxy_port_for_machine(mid)
            candidates.append({
                "email": em_l,
                "mid": mid,
                "port": port,
                "priority": 1 if em_l in session_emails else 2,
                "reason": "cooldown_expired_session" if em_l in session_emails else "cooldown_expired",
            })

    completed_chatgpt = set()
    cg_state_file = Path("D:/Taadaa/runtime/kibe/cron-state/chatgpt_link_backlog_state.json")
    if cg_state_file.exists():
        try:
            cg_data = json.loads(cg_state_file.read_text(encoding="utf-8"))
            completed_chatgpt = set(k.lower() for k in cg_data.get("completed_chatgpt", {}).keys())
        except Exception:
            pass

    if MASTER_XLSX.exists():
        try:
            import openpyxl
            wb = openpyxl.load_workbook(MASTER_XLSX, data_only=True)
            ws = wb["Kibe_Farm_S7"]
            for r in list(ws.iter_rows(values_only=True))[1:]:
                if not (r and r[1] and "@" in str(r[1])):
                    continue
                em_l   = str(r[1]).strip().lower()
                state_ = str(r[6] or "").strip().upper()
                if state_ in ("DIE", "BAN", "SUSPENDED"):
                    continue

                if em_l in clean_map:
                    info = clean_map[em_l]
                    c_date = info.get("created_date")
                    if not c_date:
                        log(f"[CANDIDATE-FILTER] {em_l}: clean_map missing created_date (fail-closed)")
                        continue
                    from datetime import date
                    d_today = date.fromisoformat(today_str[:10])
                    if (d_today - c_date).days < 7:
                        log(f"[CANDIDATE-FILTER] {em_l}: clean_map soak < 7 days ({(d_today - c_date).days}d)")
                        continue
                else:
                    updated_raw = str(r[14] or "").strip() if len(r) > 14 else ""
                    if not updated_raw:
                        log(f"[CANDIDATE-FILTER] {em_l}: no updated_raw date in master (fail-closed)")
                        continue
                    try:
                        from datetime import date
                        d_updated = date.fromisoformat(updated_raw[:10])
                        d_today = date.fromisoformat(today_str[:10])
                        if (d_today - d_updated).days < 7:
                            log(f"[CANDIDATE-FILTER] {em_l}: master updated soak < 7 days ({(d_today - d_updated).days}d)")
                            continue
                    except Exception as ex_dt:
                        log(f"[CANDIDATE-FILTER] {em_l}: invalid updated_raw '{updated_raw}' (fail-closed: {ex_dt})")
                        continue

                if em_l in seen_emails or em_l in omniroute_success or em_l in excluded_emails:
                    continue
                if em_l not in gpm_emails:
                    continue

                rec = str(r[3] or "").lower()
                if "khoale" in rec or "khoale" in em_l:
                    continue
                proxy_raw = str(r[10] or "")
                m = re.search(r":(\d{4,5})", proxy_raw)
                port = m.group(1) if m else None
                m2 = re.search(r"(\d+)", str(r[7] or ""))
                mid = int(m2.group(1)) if m2 else None

                note_val = str(r[13] or "").lower() if len(r) > 13 else ""
                is_chatgpt_ready = "chatgpt_ready" in note_val or "chatgpt" in note_val or em_l in completed_chatgpt

                if em_l in session_emails:
                    priority = 1
                    reason = "has_google_session_ready_oauth"
                elif is_chatgpt_ready:
                    priority = 2
                    reason = "chatgpt_ready_priority"
                else:
                    priority = 3
                    reason = "ready_gpm_oauth"

                candidates.append({
                    "email": em_l,
                    "mid": mid,
                    "port": port,
                    "priority": priority,
                    "reason": reason,
                })
        except Exception as e:
            log(f"Lỗi đọc XLSX: {e}")

    # Sắp xếp ưu tiên: priority=1 (Session sẵn) -> priority=2 (ChatGPT trust) -> priority=3 (Khác)
    candidates.sort(key=lambda x: x.get("priority", 3))

    seen_mids = set()
    filtered  = []
    current_run_proxy_count = dict(proxy_count)
    for c in candidates:
        port = c.get("port")
        mid  = c.get("mid")
        if mid in seen_mids:
            log(f"[CANDIDATE-FILTER] {c.get('email')} skipped: mid M{mid} already scheduled in this batch")
            continue
        if port and current_run_proxy_count.get(port, 0) >= MAX_LOGINS_PER_PROXY:
            log(f"[CANDIDATE-FILTER] {c.get('email')} skipped: proxy port {port} reached daily limit ({MAX_LOGINS_PER_PROXY})")
            continue
        filtered.append(c)
        seen_mids.add(mid)
        if port:
            current_run_proxy_count[port] = current_run_proxy_count.get(port, 0) + 1

    return filtered, proxy_count

ADB_PATH     = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"

def get_online_adb_serials() -> set[str]:
    """Lấy danh sách các serial thiết bị ADB đang online."""
    online = set()
    try:
        res = subprocess.run([ADB_PATH, "devices"], capture_output=True, text=True, timeout=5)
        for line in res.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] == "device":
                online.add(parts[0])
    except Exception as e:
        log(f"Lỗi kiểm tra adb devices: {e}")
    return online

def get_machine_serial_map() -> dict[int, str]:
    """Lấy map mid -> serial từ Master Excel hoặc PROXYgandienthoai.xlsx."""
    serial_map = {}
    proxy_file = Path(r"D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx")
    if proxy_file.exists():
        try:
            import openpyxl
            wb = openpyxl.load_workbook(proxy_file, data_only=True, read_only=True)
            ws = wb["Proxy"]
            for r in list(ws.iter_rows(values_only=True))[1:]:
                if r and r[0] is not None and r[1]:
                    try:
                        serial_map[int(r[0])] = str(r[1]).strip()
                    except Exception:
                        pass
            wb.close()
        except Exception:
            pass

    if not serial_map and MASTER_XLSX.exists():
        try:
            import openpyxl
            wb = openpyxl.load_workbook(MASTER_XLSX, data_only=True, read_only=True)
            ws = wb["Kibe_Farm_S7"]
            for r in list(ws.iter_rows(values_only=True))[1:]:
                if r and r[7] and r[9]:
                    m = re.search(r"(\d+)", str(r[7]))
                    if m:
                        serial_map[int(m.group(1))] = str(r[9]).strip()
            wb.close()
        except Exception:
            pass
    return serial_map

def _get_proxy_port_for_machine(mid: int | None) -> str | None:
    """Tra port proxy của máy từ MASTER_XLSX."""
    if not mid or not MASTER_XLSX.exists():
        return None
    try:
        import openpyxl
        wb = openpyxl.load_workbook(MASTER_XLSX, data_only=True)
        ws = wb["Kibe_Farm_S7"]
        for r in list(ws.iter_rows(values_only=True))[1:]:
            m = re.search(r"(\d+)", str(r[7] or ""))
            if m and int(m.group(1)) == mid:
                m2 = re.search(r":(\d{4,5})", str(r[10] or ""))
                return m2.group(1) if m2 else None
    except Exception:
        pass
    return None

def is_machine_idle(mid: int) -> bool:
    if LOCK_DIR.exists():
        for f in os.listdir(LOCK_DIR):
            if f.endswith(".lock.json") and f"machine_{mid}." in f:
                return False
    now_dt = datetime.now()
    dirs = glob.glob(str(MANIFEST_DIR / "*"))
    if dirs:
        latest = max(dirs, key=os.path.getmtime)
        files  = glob.glob(os.path.join(latest, "assignment-v1-*.json"))
        if files:
            try:
                mdata = json.loads(Path(max(files, key=os.path.getmtime)).read_text(encoding="utf-8"))
                for e in mdata.get("entries", []):
                    if e.get("machine") == mid:
                        st = datetime.fromisoformat(e["slot_time"]).replace(tzinfo=None)
                        et = datetime.fromisoformat(e["slot_end"]).replace(tzinfo=None)
                        if (st <= now_dt < et) or (now_dt <= st < now_dt + timedelta(minutes=MIN_IDLE_BUFFER_MIN)):
                            return False
            except Exception:
                pass
    return True

def run_login(c: dict) -> dict:
    mid   = c["mid"]
    email = c["email"]
    log(f"[M{mid:02d}] {c['reason']} → {email}")
    try:
        proc = subprocess.run(
            [PYTHON_EXE, str(GPM_SCRIPT), email],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
        )
        combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
        success = (
            (("SUCCESS" in combined and "LAUNCH_FAILED" not in combined and "EXCHANGE_FAILED" not in combined)
             or "ALREADY_SUCCESS" in combined)
        )
        if success:
            log(f"[M{mid:02d}] ✓ {email}")
            try:
                conn = sqlite3.connect(GPM_DB)
                conn.execute("UPDATE profiles SET GroupId = 10 WHERE Name LIKE ?", (f"%{email}%",))
                conn.commit()
                conn.close()
            except Exception:
                pass

            dual_script = r"D:\Taadaa\GPM auto\scripts\batch_dual_oauth_5workers.py"
            if os.path.exists(dual_script):
                log(f"[M{mid:02d}] Chạy tiếp Dual OAuth (ChatGPT-Web & Codex) cho {email}...")
                try:
                    proc_dual = subprocess.run(
                        [PYTHON_EXE, dual_script, "--email", email],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300
                    )
                    log(f"[M{mid:02d}] Dual OAuth output: {proc_dual.stdout[:200]}")
                except Exception as ex_dual:
                    log(f"[M{mid:02d}] Dual OAuth error (bỏ qua): {ex_dual}")
        else:
            log(f"[M{mid:02d}] ✗ {email}")
        return {**c, "status": "SUCCESS" if success else "FAIL"}
    except Exception as ex:
        log(f"[M{mid:02d}] ERR {email}: {ex}")
        return {**c, "status": "FAIL", "error": str(ex)}
def _format_summary_report(total_success: int, total_fail: int, shift_label: str = "TỐI", shift_desc: str = "tối") -> str:
    live_anti_count = len(_get_live_omniroute_antigravity_emails())
    session_count = len(_get_gpm_profiles_with_google_session())
    return (
        f"[LOGIN GPM {shift_label} - TỔNG KẾT]\n"
        f"• Kết quả ca: ✓ {total_success} | ✗ {total_fail} | proxy_limit 2/port/ngày | Hoàn tất ca {shift_desc}\n"
        f"• Antigravity Pool: {live_anti_count} accounts LIVE trên OmniRoute (:20129)\n"
        f"• Profile sẵn Google Session chờ OAuth: {session_count} accounts"
    )

def main():
    if not is_within_time_window():
        return 0

    shift_code, shift_label, shift_desc = get_current_shift_info()

    today_str = datetime.now(HCMC).strftime("%Y-%m-%d")
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    # Đọc state
    state = {}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    is_same_day = (state.get("date") == today_str)
    finished_shifts = list(state.get("finished_shifts", [])) if is_same_day else []
    reported_shifts = list(state.get("reported_shifts", [])) if is_same_day else []

    if is_same_day and shift_code in finished_shifts:
        return 0

    if not is_avatar_done(today_str):
        log("Chờ Avatar cron kết thúc...")
        return 0

    try:
        sync_gpm_profiles_lifecycle()
    except Exception as e:
        log(f"Lỗi chạy sync_gpm_profiles_lifecycle: {e}")

    processed = state.get("processed", []) if is_same_day else []
    total_success = state.get("total_success", 0) if is_same_day else 0
    total_fail = state.get("total_fail", 0) if is_same_day else 0

    candidates, proxy_count = get_candidates(today_str, processed)

    if not candidates:
        if shift_code not in reported_shifts:
            if total_success > 0 or total_fail > 0:
                print(_format_summary_report(total_success, total_fail, shift_label, shift_desc))
            reported_shifts.append(shift_code)
        if shift_code not in finished_shifts:
            finished_shifts.append(shift_code)

        all_day_finished = (shift_code == "TOI") or ({"SANG", "TRUA", "TOI"}.issubset(set(finished_shifts)))

        state.update({
            "date": today_str,
            "processed": processed,
            "proxy_count": dict(proxy_count),
            "total_success": total_success,
            "total_fail": total_fail,
            "reported": bool(reported_shifts),
            "finished": all_day_finished,
            "finished_shifts": finished_shifts,
            "reported_shifts": reported_shifts,
        })
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0

    # Lọc máy rảnh VÀ PHẢI ONLINE ADB để phối hợp làm việc (OTP/Prompt/Settings)
    online_serials = get_online_adb_serials()
    serial_map = get_machine_serial_map()

    ready = []
    for c in candidates:
        mid = c.get("mid") or 0
        if not is_machine_idle(mid):
            continue
        serial = serial_map.get(mid)
        if not serial or serial not in online_serials:
            log(f"Bỏ qua candidate {c['email']} vì máy M{mid:02d} (serial={serial}) không online ADB.")
            continue
        ready.append(c)

    if not ready:
        log(f"Không có máy nào thỏa mãn (rảnh + online ADB) lúc này ({len(candidates)} candidates đang chờ), chờ tick sau.")
        return 0

    batch = ready[:MAX_WORKERS]
    log(f"Bắt đầu {len(batch)} workers (max {MAX_WORKERS}) / {len(ready)} máy rảnh / {len(candidates)} tổng cần login...")

    success_n = fail_n = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = []
        for c in batch:
            futures.append(ex.submit(run_login, c))
            time.sleep(5)  # stagger 5s
        for fut in as_completed(futures):
            res = fut.result()
            processed.append(res["email"])
            port = res.get("port")
            if port:
                proxy_count[port] = proxy_count.get(port, 0) + 1
            if res["status"] == "SUCCESS":
                success_n += 1
            else:
                fail_n += 1

    total_success += success_n
    total_fail += fail_n

    now_hcm = datetime.now(HCMC)
    is_late = (
        (shift_code == "SANG" and now_hcm.hour == 8 and now_hcm.minute >= 40)
        or (shift_code == "TRUA" and now_hcm.hour == 13 and now_hcm.minute >= 40)
        or (shift_code == "TOI" and now_hcm.hour == 23 and now_hcm.minute >= 30)
    )
    all_done = (len(processed) >= len(candidates) + len(batch)) or is_late

    # IM LẶNG trong lúc chạy batch lẻ; CHỈ BÁO CÁO 1 LẦN DUY NHẤT khi hoàn tất toàn ca hoặc hết giờ ca
    if all_done:
        if shift_code not in reported_shifts:
            if total_success > 0 or total_fail > 0:
                print(_format_summary_report(total_success, total_fail, shift_label, shift_desc))
            reported_shifts.append(shift_code)
        if shift_code not in finished_shifts:
            finished_shifts.append(shift_code)

    all_day_finished = (shift_code == "TOI" and all_done) or ({"SANG", "TRUA", "TOI"}.issubset(set(finished_shifts)))

    state = {
        "date": today_str,
        "processed": processed,
        "proxy_count": dict(proxy_count),
        "total_success": total_success,
        "total_fail": total_fail,
        "reported": bool(reported_shifts),
        "finished": all_day_finished,
        "finished_shifts": finished_shifts,
        "reported_shifts": reported_shifts,
    }
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0

if __name__ == "__main__":
    main()
