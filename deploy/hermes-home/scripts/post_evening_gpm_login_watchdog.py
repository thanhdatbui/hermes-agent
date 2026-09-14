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
GPM_DB           = Path(r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db")
GPM_SCRIPT       = Path(r"D:\Taadaa\GPM auto\scripts\run_oauth_s7_pipeline.py")
PYTHON_EXE       = sys.executable

MAX_WORKERS        = 10
MAX_LOGINS_PER_PROXY = 2   # tối đa 2 acc / proxy / ngày
MIN_IDLE_BUFFER_MIN  = 45  # cách ca tiếp theo ít nhất 45 phút

def log(msg: str):
    now_str = datetime.now(HCMC).strftime("%H:%M:%S")
    sys.stderr.write(f"[{now_str}] [GPM-LOGIN] {msg}\n")
    sys.stderr.flush()

def is_within_time_window() -> bool:
    now = datetime.now(HCMC)
    after_start  = (now.hour == 21 and now.minute >= 30) or now.hour in [22, 23]
    before_end   = not (now.hour == 23 and now.minute > 45)
    return after_start and before_end

def is_avatar_done(today_str: str) -> bool:
    if AVATAR_STATE.exists():
        try:
            d = json.loads(AVATAR_STATE.read_text(encoding="utf-8"))
            if d.get("date") == today_str and d.get("finished"):
                return True
        except Exception:
            pass
    now = datetime.now(HCMC)
    return now.hour >= 22 or (now.hour == 21 and now.minute >= 45)

def get_gpm_live_emails() -> set[str]:
    """Lấy set email đang nằm trong Group 10 (Google_Live_Ready) trên GPM."""
    live = set()
    try:
        conn = sqlite3.connect(GPM_DB)
        cur = conn.cursor()
        cur.execute("SELECT Name FROM profiles WHERE GroupId = 10")
        for (name,) in cur.fetchall():
            m = re.search(r"([a-z0-9._%+\-]+@gmail\.com)", name.lower())
            if m:
                live.add(m.group(1))
        conn.close()
    except Exception as e:
        log(f"Lỗi đọc GPM DB: {e}")
    return live

def get_candidates(today_str: str, processed: list[str]) -> list[dict]:
    """
    Trả về danh sách candidates cần login, đã lọc:
    - Chưa xử lý hôm nay (processed).
    - Theo đúng constraint proxy 2 acc/ngày.
    - Ưu tiên: cooldown_expired trước, new_gmail sau.
    """
    live_gpm     = get_gpm_live_emails()
    seen_emails  = set(processed)
    proxy_count  = defaultdict(int)   # port -> số lần đã login trong ngày này
    candidates   = []

    # Đọc state proxy_count của ngày hôm nay (để idempotent qua nhiều lần watchdog tick)
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

    # --- Nhóm 1: Cooldown đã hết hạn ---
    if STATUS_JSON.exists():
        try:
            data = json.loads(STATUS_JSON.read_text(encoding="utf-8"))
            for em, info in data.get("cooldown_7days", {}).items():
                em_l = em.lower()
                retry_after = (info.get("retry_after") or "")[:10]
                if retry_after <= today_str and em_l not in seen_emails:
                    port = _get_proxy_port_for_machine(info.get("machine"))
                    candidates.append({
                        "email": em_l,
                        "mid": info.get("machine"),
                        "port": port,
                        "reason": "cooldown_expired",
                    })
        except Exception as e:
            log(f"Lỗi đọc oauth_pipeline_status: {e}")

    # --- Nhóm 2: Gmail mới chưa có trong Group 10 ---
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
                if em_l in seen_emails or em_l in live_gpm:
                    continue
                proxy_raw = str(r[10] or "")
                m = re.search(r":(\d{4,5})", proxy_raw)
                port = m.group(1) if m else None
                m2 = re.search(r"(\d+)", str(r[7] or ""))
                mid = int(m2.group(1)) if m2 else None
                candidates.append({
                    "email": em_l,
                    "mid": mid,
                    "port": port,
                    "reason": "new_gmail_or_unlogged",
                })
        except Exception as e:
            log(f"Lỗi đọc XLSX: {e}")

    # --- Áp dụng constraint: proxy <= 2, machine <= 1 ---
    seen_mids = set()
    filtered  = []
    for c in candidates:
        port = c.get("port")
        mid  = c.get("mid")
        if mid in seen_mids:
            continue
        if port and proxy_count[port] >= MAX_LOGINS_PER_PROXY:
            continue
        filtered.append(c)
        seen_mids.add(mid)
        if port:
            proxy_count[port] += 1

    return filtered, proxy_count

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
        success = "SUCCESS" in proc.stdout
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

def main():
    if not is_within_time_window():
        return 0

    today_str = datetime.now(HCMC).strftime("%Y-%m-%d")
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    # Đọc state
    state = {}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    if state.get("date") == today_str and state.get("finished"):
        return 0

    if not is_avatar_done(today_str):
        log("Chờ Avatar cron kết thúc...")
        return 0

    processed   = state.get("processed", []) if state.get("date") == today_str else []
    candidates, proxy_count = get_candidates(today_str, processed)

    if not candidates:
        state.update({"date": today_str, "processed": processed, "finished": True})
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0

    # Lọc máy rảnh
    ready = [c for c in candidates if is_machine_idle(c["mid"] or 0)]
    if not ready:
        log("Không có máy nào rảnh lúc này, chờ tick sau.")
        return 0

    batch = ready[:MAX_WORKERS]
    log(f"Bắt đầu {len(batch)} workers (max {MAX_WORKERS}) / {len(ready)} máy rảnh / {len(candidates)} tổng cần login...")

    success_n = fail_n = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = []
        for c in batch:
            futures.append(ex.submit(run_login, c))
            time.sleep(2)  # stagger 2s
        for fut in as_completed(futures):
            res = fut.result()
            processed.append(res["email"])
            if res["status"] == "SUCCESS":
                success_n += 1
            else:
                fail_n += 1

    all_done = len(processed) >= len(candidates) + len(batch)
    state = {
        "date": today_str,
        "processed": processed,
        "proxy_count": dict(proxy_count),
        "finished": all_done,
    }
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    if success_n or fail_n:
        print(f"[LOGIN GPM ĐÊM] ✓ {success_n} | ✗ {fail_n} | proxy_limit 2/port/ngày áp dụng")
    return 0

if __name__ == "__main__":
    main()
