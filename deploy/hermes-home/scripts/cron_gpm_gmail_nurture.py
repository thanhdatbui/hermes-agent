#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cron_gpm_gmail_nurture.py - Chuyên biệt nuôi định kỳ Gmail trên GPMLogin.

Đặc điểm:
- Chạy HOÀN TOÀN ĐỘC LẬP trên PC qua GPM Chromium & Proxy 4G (KHÔNG đụng tới S7/ADB).
- Quản lý trạng thái nuôi bằng file JSON: D:/Taadaa/runtime/kibe/cron-state/gpm_gmail_nurture_state.json.
- Lọc profile chưa nuôi hoặc nuôi > 5 ngày trước (mặc định BATCH_SIZE = 6, concurrency = 2).
- PHÂN BỔ TỶ LỆ HÀNH VI (Task Distribution):
  + 50% lượt nuôi: CHỈ xem YouTube (1 video 90-120s, xử lý ad, like/scroll nhẹ).
  + 30% lượt nuôi: Đọc Google News (45-60s, cuộn bài báo) + Search Google 1 từ khóa (15-20s). (KHÔNG mở YouTube).
  + 20% lượt nuôi: Xem YouTube + Đọc News hoặc Search (tuần tự 2 việc, xáo trộn thứ tự).
- QUẢN LÝ TAB TUẦN TỰ (Sequential Tab Lifecycle):
  + Chỉ dùng DUY NHẤT 1 tab, đóng tab hoặc điều hướng sang trang kế tiếp, tuyệt đối không để tab chạy nền.
- ĐÓNG DỨT ĐIỂM PROFILE GPM (Hard Process Cleanup):
  + Gọi close API (/api/v3/profiles/close/{id}) kèm stop API fallback (/api/v3/profiles/stop/{id}).
  + Browser.close() -> Context.close() -> Stop GPM -> Chờ 2s kiểm tra -> Force kill process nếu còn treo taskbar.
- Hỗ trợ CLI: --email <email> (test canary lẻ) và --limit <int> (mặc định 2).
"""

import os
import sys
import time
import json
import random
import re
import socket
import argparse
import logging
import threading
import urllib.parse
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright

try:
    import psutil
except ImportError:
    psutil = None

# --- Config & Paths ---
LOG_DIR = r"D:\Taadaa\GPM auto\logs"
LOG_FILE = os.path.join(LOG_DIR, "cron_gpm_gmail_nurture.log")
GPM_API_BASE = "http://127.0.0.1:19995/api/v3"
STATE_FILE = r"D:\Taadaa\runtime\kibe\cron-state\gpm_gmail_nurture_state.json"
SCREENSHOT_DIR = r"D:\Taadaa\GPM auto\debug_screenshots"
NURTURE_INTERVAL_SECONDS = 5 * 86400  # 5 ngày mới lặp lại nuôi profile

# Nhóm GPM Profile đã đăng nhập Google sống thành công (Google_Live_Ready)
DEFAULT_NURTURE_GROUP_ID = 10

# Danh sách từ khóa email/recovery bị loại trừ khỏi nuôi tự động để tránh kích hoạt checkpoint Google
DEFAULT_EXCLUDED_KEYWORDS = ("khoale", "khoalee")
EXCLUDED_EMAIL_KEYWORDS = tuple(
    [k.strip().lower() for k in os.environ.get("GPM_NURTURE_EXCLUDED_KEYWORDS", "").split(",") if k.strip()]
) or DEFAULT_EXCLUDED_KEYWORDS

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# --- Setup Logging ---
from logging.handlers import RotatingFileHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("gpm_gmail_nurture")

TELEMETRY_LOG = Path(r"D:\Taadaa\GPM auto\logs\batch_gpm_supervisor_telemetry.jsonl")
_telemetry_lock = threading.Lock()

def log_telemetry_metric(event_type: str, data: dict):
    """Ghi nhận telemetry metric có cấu trúc JSON và lưu logfile phục vụ giám sát hệ thống."""
    metric = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        "pid": os.getpid(),
        "correlation_id": data.get("correlation_id", f"gpm_{os.getpid()}"),
        "data": data
    }
    logger.info(f"[TELEMETRY_METRIC] {json.dumps(metric, ensure_ascii=False)}")
    try:
        TELEMETRY_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _telemetry_lock:
            if TELEMETRY_LOG.exists() and TELEMETRY_LOG.stat().st_size > 10 * 1024 * 1024:
                try:
                    rotated = TELEMETRY_LOG.with_name(f"{TELEMETRY_LOG.name}.1")
                    TELEMETRY_LOG.replace(rotated)
                except Exception:
                    pass
            with open(TELEMETRY_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(metric, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return metric

GPM_PROFILE_BASE = Path(r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile")

def has_google_session(profile_path: Optional[str]) -> bool:
    """Preflight check O(1) kiểm tra file SQLite cookies của profile trên đĩa."""
    if not profile_path:
        return False
    base = GPM_PROFILE_BASE / profile_path
    for cp in (base / "Default" / "Network" / "Cookies", base / "Default" / "Cookies"):
        if cp.exists():
            try:
                conn = sqlite3.connect(f"file:{cp}?mode=ro", uri=True)
                cur = conn.cursor()
                cur.execute("SELECT count(*) FROM cookies WHERE host_key LIKE '%google.com' AND name IN ('SID', 'SSID', 'HSID', 'SAPISID')")
                cnt = cur.fetchone()[0]
                conn.close()
                return cnt >= 2
            except Exception:
                pass
    return False

def filter_nurture_candidates(
    all_profiles: List[Dict[str, Any]],
    target_group_id: int = DEFAULT_NURTURE_GROUP_ID,
    allow_all_groups: bool = False,
    exclude_keywords: Tuple[str, ...] = EXCLUDED_EMAIL_KEYWORDS,
) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    Lọc danh sách profile hợp lệ theo chính sách GroupId và Exclusion Keywords (case-insensitive).
    Trả về: (candidates, skipped_group_count, skipped_blacklist_count)
    """
    if allow_all_groups:
        logger.warning("[SAFETY_GUARD] allow_all_groups=True: Bỏ qua kiểm tra GroupId, mọi group đều được quét!")
    candidates = []
    skipped_group = 0
    skipped_blacklist = 0

    for p in all_profiles:
        name = p.get("name", "")
        email = extract_email(name)
        if not email:
            continue

        email_lower = email.lower()
        # THỨ TỰ ƯU TIÊN KIỂM TRA (INVARIANT): 1. Blacklist keyword -> 2. GroupId filter.
        # Lý do: Tài khoản dính blacklist cấm tuyệt đối tham gia nuôi bất kể thuộc Group nào.
        # Kiểm tra từ khóa loại trừ (triệt để case-insensitive)
        if any(kw.lower() in email_lower for kw in exclude_keywords):
            logger.debug(f"[FILTER] Bỏ qua profile {name}: email {email} chứa từ khóa bị loại trừ")
            skipped_blacklist += 1
            continue

        # Kiểm tra GroupId nếu không bật flag all-groups
        if not allow_all_groups:
            gid = p.get("group_id")
            try:
                # Ép kiểu an toàn: chỉ chấp nhận integer chính xác (tránh 10.7 bị làm tròn thành 10)
                if isinstance(gid, float):
                    gid_int = int(gid) if gid.is_integer() else 0
                else:
                    val_str = str(gid).strip()
                    val_float = float(val_str)
                    gid_int = int(val_float) if val_float.is_integer() else 0
            except (ValueError, TypeError):
                gid_int = 0
            if gid_int != target_group_id:
                logger.debug(f"[FILTER] Bỏ qua profile {name}: group_id {gid_int} != {target_group_id}")
                skipped_group += 1
                continue

        p_copy = dict(p)
        p_copy["email"] = email
        candidates.append(p_copy)

    return candidates, skipped_group, skipped_blacklist

SEARCH_QUERIES = [
    "thoi tiet hom nay", "tin tuc 24h", "gia vang hom nay",
    "bong da ngoai hang anh", "cong nghe ai moi nhat",
    "dia diem du lich dep viet nam", "am thuc mien tay",
    "meo vat cuoc song", "dien thoai tot nhat 2026",
    "kinh te viet nam nam nay", "xe dien vinfast moi"
]

_STATE_LOCK = threading.Lock()

def load_state() -> dict:
    with _STATE_LOCK:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Lỗi đọc state file, khởi tạo mới: {e}")
        return {}

def save_state(state: dict):
    with _STATE_LOCK:
        try:
            temp_file = f"{STATE_FILE}.tmp_{os.getpid()}_{int(time.time()*1000)}"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            os.replace(temp_file, STATE_FILE)
        except Exception as e:
            logger.error(f"Lỗi lưu state file: {e}")

def update_profile_state(email: str, entry: dict):
    """Atomic update: đọc-sửa-ghi được bảo vệ trọn vẹn trong lock chống race condition."""
    with _STATE_LOCK:
        state = {}
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except Exception as e:
                logger.warning(f"Lỗi đọc state file: {e}")
        cur = state.get(email, {})
        cur.update(entry)
        state[email] = cur
        try:
            temp_file = f"{STATE_FILE}.tmp_{os.getpid()}_{int(time.time()*1000)}"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            os.replace(temp_file, STATE_FILE)
        except Exception as e:
            logger.error(f"Lỗi lưu state atomic: {e}")

def get_all_gpm_profiles() -> list:
    all_profiles = []
    page = 1
    while True:
        try:
            res = requests.get(f"{GPM_API_BASE}/profiles?page={page}&per_page=300", timeout=15).json()
            data = res.get("data")
            items = data if isinstance(data, list) else (data or {}).get("list", [])
            if not items:
                break
            all_profiles.extend(items)
            if page >= (res.get("pagination") or {}).get("total_page", 1):
                break
            page += 1
        except Exception as e:
            logger.error(f"Lỗi kết nối GPM API: {e}")
            break
    return all_profiles

def start_gpm_profile(profile_id: str) -> Optional[str]:
    url = f"{GPM_API_BASE}/profiles/start/{profile_id}?win_scale=0.8"
    for attempt in range(3):
        try:
            res = requests.get(url, timeout=30).json()
            data = res.get("data") or {}
            addr = data.get("remote_debugging_address")
            if addr:
                return addr
            logger.warning(f"Thử {attempt+1}: Start {profile_id} thất bại: {res.get('message')}")
        except Exception as e:
            logger.warning(f"Thử {attempt+1}: Lỗi GPM API start: {e}")
        time.sleep(2)
    return None

def stop_gpm_profile(profile_id: str):
    """
    Đóng profile GPM theo chuẩn:
    1. Gọi GET /api/v3/profiles/close/{profile_id} (endpoint chuẩn để đóng).
    2. Gọi GET /api/v3/profiles/stop/{profile_id} để fallback.
    """
    try:
        requests.get(f"{GPM_API_BASE}/profiles/close/{profile_id}", timeout=10)
    except Exception as e:
        logger.debug(f"Gọi profiles/close/{profile_id}: {e}")

    try:
        requests.get(f"{GPM_API_BASE}/profiles/stop/{profile_id}", timeout=10)
    except Exception as e:
        logger.debug(f"Gọi profiles/stop/{profile_id} (fallback): {e}")

def is_profile_still_running(remote_port: Optional[int] = None, profile_path: Optional[str] = None) -> bool:
    """Kiểm tra xem profile có còn tiến trình chạy không (qua socket port hoặc psutil)."""
    if remote_port:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex(('127.0.0.1', remote_port)) == 0:
                    return True
        except Exception:
            pass

    if psutil and (remote_port or profile_path):
        target_port_flag = rf"^--remote-debugging-port={remote_port}$" if remote_port else None
        norm_target_path = os.path.normpath(profile_path).lower() if profile_path else None
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = (p.info.get('name') or '').lower()
                if 'chrome' in name:
                    cmdline = p.info.get('cmdline') or []
                    if target_port_flag and any(re.match(target_port_flag, arg) for arg in cmdline):
                        return True
                    if norm_target_path:
                        for arg in cmdline:
                            if arg.startswith("--user-data-dir="):
                                val = arg.split("=", 1)[1].strip('"\'')
                                if norm_target_path in os.path.normpath(val).lower():
                                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    return False

def force_kill_profile_process(profile_id: str, remote_port: Optional[int] = None, profile_path: Optional[str] = None):
    """Force close dứt điểm tiến trình Chrome của profile nếu vẫn còn kẹt taskbar."""
    stop_gpm_profile(profile_id)

    if psutil is None or (not remote_port and not profile_path):
        return

    try:
        target_port_flag = rf"^--remote-debugging-port={remote_port}$" if remote_port else None
        norm_target_path = os.path.normpath(profile_path).lower() if profile_path else None

        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = (p.info.get('name') or '').lower()
                if 'chrome' in name:
                    cmdline = p.info.get('cmdline') or []
                    match = False
                    if target_port_flag and any(re.match(target_port_flag, arg) for arg in cmdline):
                        match = True
                    elif norm_target_path:
                        for arg in cmdline:
                            if arg.startswith("--user-data-dir="):
                                val = arg.split("=", 1)[1].strip('"\'')
                                if norm_target_path in os.path.normpath(val).lower():
                                    match = True
                                    break
                    if match:
                        logger.warning(f"Force kill Chrome zombie PID {p.info['pid']} (Port: {remote_port})...")
                        p.terminate()
                        try:
                            p.wait(timeout=2.0)
                        except Exception:
                            p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        logger.warning(f"Lỗi khi force kill Chrome process: {e}")

def extract_email(name: str) -> str:
    m = re.search(r'([a-zA-Z0-9_.+-]+@gmail\.com)', name, re.IGNORECASE)
    return m.group(1).lower() if m else ""

def human_scroll(page, total_pixels: int, steps: int = 5):
    """Mô phỏng cuộn trang tự nhiên mượt mà từng bước ngẫu nhiên."""
    for _ in range(steps):
        chunk = total_pixels // steps + random.randint(-15, 15)
        try:
            page.mouse.wheel(0, chunk)
        except Exception:
            break
        time.sleep(random.uniform(0.3, 0.7))

def cleanup_extra_tabs(context, keep_page=None):
    """
    Quy tắc quản lý tab tuần tự:
    Chỉ duy nhất 1 tab hoạt động, đóng toàn bộ tab thừa/popup/extension.
    """
    try:
        all_pages = [pg for pg in context.pages if not pg.url.startswith("chrome-extension://")]
        target = keep_page if (keep_page and not getattr(keep_page, "is_closed", lambda: True)()) else (all_pages[0] if all_pages else None)
        for pg in all_pages:
            if pg != target and not pg.is_closed():
                try:
                    pg.close()
                except Exception:
                    pass
        return target
    except Exception:
        return keep_page

def take_proof_screenshot(context, page, ss_path: str, email: str):
    """Chụp ảnh nghiệm thu chất lượng cao (Direct screenshot kèm fallback qua CDP)."""
    try:
        time.sleep(1)
        page.screenshot(path=ss_path, timeout=5000, animations="disabled", type="jpeg", quality=80)
        logger.info(f"[{email}] ✓ Đã chụp ảnh nghiệm thu: {ss_path}")
    except Exception as e_ss:
        logger.warning(f"[{email}] Lỗi chụp screenshot thường ({e_ss}), fallback qua CDP...")
        try:
            cdp_session = context.new_cdp_session(page)
            res_shot = cdp_session.send("Page.captureScreenshot", {"format": "jpeg", "quality": 80})
            import base64
            with open(ss_path, "wb") as f_ss:
                f_ss.write(base64.b64decode(res_shot["data"]))
            cdp_session.detach()
            logger.info(f"[{email}] ✓ Đã chụp ảnh qua CDP thành công: {ss_path}")
        except Exception as e_cdp:
            logger.warning(f"[{email}] Chụp qua CDP cũng lỗi: {e_cdp}")

# ==============================================================================
# CÁC TÁC VỤ NUÔI ĐỘC LẬP (Modular Sub-Tasks) - CHỈ DÙNG 1 TAB TUẦN TỰ
# ==============================================================================

def task_youtube(context, page, email: str, ss_path: str):
    """Tác vụ YouTube: Xem 1 video 90-120s, né ad, like/scroll nhẹ."""
    logger.info(f"[{email}] [Task: YouTube] Điều hướng tới https://www.youtube.com...")
    try:
        if page.is_closed():
            page = context.new_page()

        page.goto("https://www.youtube.com", timeout=35000, wait_until="domcontentloaded")
        time.sleep(random.uniform(3.0, 4.0))

        # Cuộn nhẹ trang chủ khám phá feed
        human_scroll(page, random.randint(300, 600), steps=4)
        time.sleep(1)

        def is_yt_empty(pg):
            try:
                if pg.locator("ytd-rich-item-renderer a#video-title-link, a#thumbnail").count() == 0:
                    return True
                body_txt = pg.locator("body").inner_text()
                if "Thử tìm kiếm để bắt đầu" in body_txt or "Try searching to get started" in body_txt:
                    return True
            except Exception:
                pass
            return False

        # Nếu bị trống feed: chuyển qua Shorts xem 5-8s để bung feed
        if is_yt_empty(page):
            logger.info(f"[{email}] Trang chủ YouTube trống, chuyển qua Shorts xem 5-8s để bung feed...")
            try:
                shorts_btn = page.locator("a[title='Shorts'], a#endpoint[title='Shorts']").first
                if shorts_btn.count() > 0 and shorts_btn.is_visible():
                    shorts_btn.click(force=True)
                else:
                    page.goto("https://www.youtube.com/shorts", timeout=20000, wait_until="domcontentloaded")
                time.sleep(random.uniform(5.0, 8.0))
            except Exception as e_sh:
                logger.warning(f"[{email}] Lỗi mở Shorts: {e_sh}")

            try:
                home_btn = page.locator("a#logo, a[title='Trang chủ YouTube'], a[title='YouTube Home']").first
                if home_btn.count() > 0 and home_btn.is_visible():
                    home_btn.click(force=True)
                else:
                    page.goto("https://www.youtube.com", timeout=20000, wait_until="domcontentloaded")
                time.sleep(4)
            except Exception as e_hm:
                logger.warning(f"[{email}] Lỗi quay lại Trang chủ: {e_hm}")

        # Nếu vẫn chưa có video: search từ khóa ngẫu nhiên
        if is_yt_empty(page):
            logger.info(f"[{email}] Feed vẫn trống, tìm kiếm từ khóa ngẫu nhiên...")
            try:
                kw = random.choice(["nhac tre", "tin tuc hom nay", "review phim"])
                search_inp = page.locator("input#search, input[name='search_query']").first
                if search_inp.count() > 0:
                    search_inp.fill(kw)
                    page.keyboard.press("Enter")
                    time.sleep(4)
                else:
                    page.goto(f"https://www.youtube.com/results?search_query={urllib.parse.quote(kw)}", timeout=25000, wait_until="domcontentloaded")
                    time.sleep(4)
            except Exception as e_sr:
                logger.warning(f"[{email}] Lỗi search YouTube: {e_sr}")

        # Click vào video thật để phát (/watch)
        video_links = page.locator("a#video-title-link[href*='/watch'], ytd-rich-grid-media a#video-title-link, a#thumbnail[href*='/watch'], ytd-video-renderer a#video-title[href*='/watch']")
        count = video_links.count()
        target_video = None
        target_href = None
        for i in range(min(count, 15)):
            el = video_links.nth(i)
            href = el.get_attribute("href") or ""
            if "/watch" in href and "ad" not in href.lower():
                try:
                    parent_txt = el.locator("xpath=ancestor::ytd-rich-item-renderer | ancestor::ytd-video-renderer").inner_text()
                    if any(w in parent_txt for w in ["Được tài trợ", "Sponsored", "Ad", "advertisement"]):
                        continue
                except Exception:
                    pass
                target_video = el
                target_href = href
                break

        if target_video:
            try:
                target_video.click(force=True)
                logger.info(f"[{email}] Đã click video YouTube thật để phát: {target_href}")
            except Exception as e_clk:
                logger.warning(f"[{email}] Click video thất bại ({e_clk}), goto trực tiếp href...")
                if target_href:
                    target_url = target_href if target_href.startswith("http") else f"https://www.youtube.com{target_href}"
                    page.goto(target_url, timeout=25000, wait_until="domcontentloaded")
        else:
            fallback_links = page.locator("a[href*='/watch']")
            for j in range(min(fallback_links.count(), 10)):
                fb = fallback_links.nth(j)
                h = fb.get_attribute("href") or ""
                if "/watch" in h and "ad" not in h.lower():
                    target_url = h if h.startswith("http") else f"https://www.youtube.com{h}"
                    page.goto(target_url, timeout=25000, wait_until="domcontentloaded")
                    break

        try:
            page.wait_for_url("**/watch*", timeout=15000)
        except Exception:
            pass

        time.sleep(4)
        try:
            page.evaluate("() => { const v = document.querySelector('video'); if (v && v.paused) { v.play(); } }")
        except Exception:
            pass

        # Chụp screenshot nghiệm thu lúc đang phát video
        take_proof_screenshot(context, page, ss_path, email)

        watch_duration = random.randint(300, 360)
        logger.info(f"[{email}] Đang xem YouTube video trong {watch_duration}s (Smart Ad Skip & Like/Scroll Simulation)...")
        ad_selector = (
            "button.ytp-skip-ad-button, .ytp-ad-skip-button, button.ytp-ad-skip-button-modern, "
            "[class*='ytp-ad-skip-button'], .ytp-ad-skip-button-slot button, "
            "button:has-text('Bỏ qua'), button:has-text('Skip')"
        )
        start_watch = time.time()
        ad_notified = False
        liked = False
        while time.time() - start_watch < watch_duration:
            try:
                # Xử lý quảng cáo: ưu tiên bấm Bỏ qua ngay khi xuất hiện
                skip_btn = page.locator(ad_selector).first
                if skip_btn.is_visible():
                    time.sleep(round(random.uniform(1.2, 2.5), 2))
                    try:
                        skip_btn.hover(timeout=2000)
                    except Exception:
                        pass
                    skip_btn.click(force=True, timeout=2000)
                    logger.info(f"[{email}] ✓ Đã bấm Bỏ qua quảng cáo YouTube thành công")
                    time.sleep(2)
                    take_proof_screenshot(context, page, ss_path, email)
                elif page.locator(".ad-showing, .ad-interrupting").count() > 0:
                    if not ad_notified:
                        logger.info(f"[{email}] Phát hiện quảng cáo đang phát, chờ nút Bỏ qua...")
                        ad_notified = True
                else:
                    ad_notified = False

                # Like và cuộn nhẹ ngẫu nhiên mô phỏng người thật
                elapsed = time.time() - start_watch
                if elapsed > 25 and not liked:
                    if random.random() < 0.40:
                        try:
                            like_btn = page.locator("like-button-view-model button, #segmented-like-button button, ytd-toggle-button-renderer button").first
                            if like_btn.count() > 0 and like_btn.is_visible():
                                like_btn.click(force=True)
                                logger.info(f"[{email}] Đã click Thích (Like) video")
                        except Exception:
                            pass
                    liked = True

                if int(elapsed) % 30 == 0:
                    human_scroll(page, random.randint(150, 300), steps=2)
            except Exception:
                pass
            time.sleep(2)

        logger.info(f"[{email}] ✓ Hoàn thành xem YouTube ({watch_duration}s).")
    except Exception as e_yt:
        logger.warning(f"[{email}] Lỗi trong luồng YouTube: {e_yt}")
        if not os.path.exists(ss_path):
            try:
                page.screenshot(path=ss_path, timeout=5000)
            except Exception:
                pass

    return page

def task_google_news(context, page, email: str, ss_path: str):
    """
    Tác vụ Google News: Lướt tin tức, cuộn trang mượt mà và đọc 1 bài báo (45-60s).
    QUẢN LÝ TAB TUẦN TỰ: Nếu bài báo mở tab mới, đóng tab News cũ ngay lập tức.
    """
    logger.info(f"[{email}] [Task: Google News] Điều hướng tới https://news.google.com...")
    reading_page = page
    try:
        if reading_page.is_closed():
            reading_page = context.new_page()

        reading_page.goto("https://news.google.com", timeout=35000, wait_until="domcontentloaded")
        time.sleep(3)

        # Cuộn trang ngẫu nhiên đọc lướt bằng human_scroll
        for _ in range(3):
            human_scroll(reading_page, random.randint(350, 600), steps=random.randint(4, 6))
            time.sleep(random.uniform(1.5, 3.0))

        # Click vào 1 bài báo thật sự
        article_link = reading_page.locator("article a[href*='./read/'], article a[href*='/articles/'], article a, c-wiz a[href*='./read/'], c-wiz a[href*='/articles/']").first
        if article_link.count() > 0:
            try:
                with context.expect_page(timeout=5000) as new_page_info:
                    article_link.click(force=True)
                new_art_page = new_page_info.value
                new_art_page.wait_for_load_state("domcontentloaded", timeout=20000)
                # Đóng tab News cũ ngay lập tức để duy trì đúng 1 tab duy nhất
                try:
                    reading_page.close()
                except Exception:
                    pass
                reading_page = new_art_page
                logger.info(f"[{email}] Đã mở bài báo và đóng tab News cũ: {reading_page.url}")
            except Exception:
                try:
                    article_link.click(force=True)
                    logger.info(f"[{email}] Đã click bài báo trên trang hiện tại.")
                except Exception as e_art:
                    logger.warning(f"[{email}] Click bài báo thất bại: {e_art}")

        # Chụp ảnh nếu chưa có ảnh nghiệm thu
        if not os.path.exists(ss_path):
            take_proof_screenshot(context, reading_page, ss_path, email)

        # Đọc bài báo trong 45 - 60 giây (vừa đọc vừa cuộn trang từ từ mô phỏng người thật)
        read_duration = random.randint(45, 60)
        logger.info(f"[{email}] Đang đọc bài báo trong {read_duration}s...")
        start_read = time.time()
        while time.time() - start_read < read_duration:
            scroll_sleep = random.uniform(5.0, 8.0)
            time.sleep(min(scroll_sleep, max(1.0, read_duration - (time.time() - start_read))))
            try:
                human_scroll(reading_page, random.randint(250, 450), steps=random.randint(3, 5))
            except Exception:
                pass

        logger.info(f"[{email}] ✓ Hoàn thành đọc báo Google News ({read_duration}s).")
    except Exception as e_news:
        logger.warning(f"[{email}] Lỗi trong luồng Google News: {e_news}")

    return reading_page

def task_google_search(context, page, email: str, ss_path: str):
    """
    Tác vụ Google Search: Tìm kiếm từ khóa đời sống, cuộn mượt mà xem kết quả (15-20s).
    QUẢN LÝ TAB TUẦN TỰ: Điều hướng trực tiếp trên tab hiện tại.
    """
    q = random.choice(SEARCH_QUERIES)
    logger.info(f"[{email}] [Task: Google Search] Điều hướng Google Search với từ khóa: '{q}'...")
    try:
        if page.is_closed():
            page = context.new_page()

        search_url = f"https://www.google.com/search?q={urllib.parse.quote(q)}"
        page.goto(search_url, timeout=35000, wait_until="domcontentloaded")
        time.sleep(2)

        # Cuộn nhẹ trang kết quả bằng human_scroll
        human_scroll(page, random.randint(250, 500), steps=random.randint(3, 5))
        stay_duration = random.randint(15, 20)
        logger.info(f"[{email}] Xem kết quả tìm kiếm trong {stay_duration}s...")
        time.sleep(stay_duration)

        # Chụp ảnh nếu chưa có ảnh nghiệm thu
        if not os.path.exists(ss_path):
            take_proof_screenshot(context, page, ss_path, email)

        logger.info(f"[{email}] ✓ Hoàn thành tìm kiếm Google ({stay_duration}s).")
    except Exception as e_search:
        logger.warning(f"[{email}] Lỗi trong luồng Google Search: {e_search}")

    return page

# ==============================================================================
# HÀM ĐIỀU PHỐI NUÔI 1 PROFILE
# ==============================================================================

def choose_behavior_tasks(rnd: Optional[float] = None, task_override: str = "") -> Tuple[str, List[str]]:
    """Phân bổ tỷ lệ hành vi: 50% chỉ YouTube, 30% Google News + Search, 20% Hỗn hợp."""
    if task_override == "youtube":
        return "100% Chỉ YouTube (Canary Override)", ["youtube"]
    if task_override == "news":
        return "100% Đọc tin tức (Canary Override)", ["news", "search"]
    if rnd is None:
        rnd = random.random()
    if rnd < 0.50:
        return "50% Giải trí (CHỈ YouTube)", ["youtube"]
    elif rnd < 0.80:
        return "30% Đọc tin tức (Google News + Search)", ["news", "search"]
    else:
        mixed_sub = ["youtube", random.choice(["news", "search"])]
        random.shuffle(mixed_sub)
        return "20% Hỗn hợp (YouTube + News/Search)", mixed_sub

def nurture_profile(p: dict, task_override: str = "") -> Tuple[bool, str]:
    p_id = p["id"]
    email = p["email"]
    p_name = p.get("name", "")
    p_path = p.get("profile_path", "")
    logger.info(f"========== Bắt đầu nuôi profile: {email} (ID: {p_id}, Name: {p_name}) ==========")

    addr = start_gpm_profile(p_id)
    if not addr:
        logger.error(f"[{email}] Không thể khởi động profile GPM!")
        log_telemetry_metric("profile_start_failed", {"email": email, "profile_id": p_id})
        return False, "START_FAILED"

    remote_port = None
    try:
        remote_port = int(addr.split(":")[-1])
    except Exception:
        remote_port = None

    # Chờ CDP socket lắng nghe ổn định (tối đa 15s)
    if remote_port:
        for _ in range(15):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1.0)
                    if s.connect_ex(('127.0.0.1', remote_port)) == 0:
                        break
            except Exception:
                pass
            time.sleep(1)
        else:
            time.sleep(2)
    else:
        time.sleep(3)

    ss_path = os.path.join(SCREENSHOT_DIR, f"nurture_{email}.png")

    browser = None
    context = None

    try:
        with sync_playwright() as pw:
            logger.info(f"[{email}] Kết nối Playwright tới CDP {addr}...")
            browser = pw.chromium.connect_over_cdp(f"http://{addr}", timeout=20000)
            context = browser.contexts[0]

            # QUẢN LÝ TAB TUẦN TỰ: Chỉ giữ duy nhất 1 tab hoạt động
            active_page = context.pages[0] if context.pages else context.new_page()
            active_page = cleanup_extra_tabs(context, keep_page=active_page)

            # KIỂM TRA LIVE SESSION GOOGLE (Preflight Cookie Guard):
            # Tránh lãng phí mở nuôi nếu profile chưa login hoặc mất session Google
            try:
                live_cookies = context.cookies(["https://accounts.google.com", "https://www.youtube.com", "https://google.com"])
                found_session = {c.get("name") for c in live_cookies if c.get("name") in ("SID", "SSID", "HSID", "SAPISID")}
                if len(found_session) < 2:
                    logger.warning(f"[{email}] CẢNH BÁO: Profile chưa có acc Google hoặc mất session (chỉ thấy {len(found_session)} token). Dừng nuôi để tránh lãng phí!")
                    log_telemetry_metric("profile_session_lost", {"email": email, "status": "NEEDS_LOGIN", "tokens_found": len(found_session)})
                    update_profile_state(email, {
                        "last_checked": time.time(),
                        "last_checked_iso": datetime.now().isoformat(),
                        "status": "NEEDS_LOGIN",
                        "profile_id": p_id
                    })
                    return False, "NEEDS_LOGIN"
            except Exception as e_ck:
                logger.warning(f"[{email}] Lỗi kiểm tra cookie (bỏ qua guard): {e_ck}")

            # 1. PHÂN BỔ TỶ LỆ HÀNH VI (Task Distribution):
            behavior_type, tasks = choose_behavior_tasks(task_override=task_override)
            logger.info(f"[{email}] Phân bổ hành vi: [{behavior_type}] -> Tác vụ: {' -> '.join(t.upper() for t in tasks)}")

            for idx, task_name in enumerate(tasks, 1):
                logger.info(f"[{email}] [{idx}/{len(tasks)}] Bắt đầu tác vụ: {task_name.upper()}...")
                
                # Đảm bảo tab tuần tự duy nhất còn sống
                if active_page.is_closed():
                    active_page = context.new_page()
                active_page = cleanup_extra_tabs(context, keep_page=active_page)

                if task_name == "youtube":
                    active_page = task_youtube(context, active_page, email, ss_path)
                elif task_name == "news":
                    active_page = task_google_news(context, active_page, email, ss_path)
                elif task_name == "search":
                    active_page = task_google_search(context, active_page, email, ss_path)

                active_page = cleanup_extra_tabs(context, keep_page=active_page)

                # Nghỉ giữa các tác vụ nếu còn tác vụ tiếp theo (3 - 6s)
                if idx < len(tasks):
                    pause_s = round(random.uniform(3.0, 6.0), 2)
                    logger.info(f"[{email}] Nghỉ giữa các tác vụ {pause_s}s...")
                    time.sleep(pause_s)

            logger.info(f"[{email}] ✓ Đã hoàn thành toàn bộ kịch bản nuôi!")
            return True, "OK"

    except Exception as e:
        logger.error(f"[{email}] Lỗi bất thường trong quá trình nuôi: {e}")
        return False, f"ERROR: {e}"
    finally:
        # 3. ĐÓNG DỨT ĐIỂM PROFILE GPM (Hard Process Cleanup)
        logger.info(f"[{email}] Tiến hành đóng dứt điểm profile GPM {p_id}...")
        try:
            if context:
                context.close()
        except Exception:
            pass
        try:
            if browser:
                browser.close()
        except Exception:
            pass

        # Bước 1: Gọi API close + stop fallback
        stop_gpm_profile(p_id)

        # Bước 2: Chờ 2s kiểm tra, nếu profile vẫn còn chạy thì force close dứt điểm
        time.sleep(2)
        if is_profile_still_running(remote_port=remote_port, profile_path=p_path):
            logger.warning(f"[{email}] Profile {p_id} vẫn còn tiến trình sau 2s, tiến hành force kill dứt điểm!")
            force_kill_profile_process(p_id, remote_port=remote_port, profile_path=p_path)
            time.sleep(1)
        else:
            logger.info(f"[{email}] ✓ Profile {p_id} đã đóng sạch sẽ khỏi hệ thống.")

def main():
    parser = argparse.ArgumentParser(description="Chương trình nuôi định kỳ Gmail trên GPMLogin")
    parser.add_argument("--email", type=str, default="", help="Chỉ định email cần nuôi (chạy canary đơn lẻ)")
    parser.add_argument("--limit", type=int, default=5, help="Số lượng profile nuôi trong mỗi tick (mặc định 5)")
    parser.add_argument("--concurrency", type=int, default=5, help="Số worker chạy song song so le (mặc định 5)")
    parser.add_argument("--stagger", type=int, default=45, help="Độ trễ giãn cách khởi động so le giữa các profile (giây)")
    parser.add_argument("--group-id", type=int, default=DEFAULT_NURTURE_GROUP_ID, help="GroupId GPM cần nuôi (mặc định 10: Google_Live_Ready)")
    parser.add_argument("--all-groups", action="store_true", help="Bỏ qua lọc GroupId, quét tất cả profile")
    parser.add_argument("--confirm-all-groups", action="store_true", help="Xác nhận chạy trên tất cả groups (bắt buộc khi dùng --all-groups để tránh cấu hình nhầm)")
    parser.add_argument("--exclude-keywords", nargs="*", default=list(EXCLUDED_EMAIL_KEYWORDS), help="Danh sách từ khóa email loại trừ")
    parser.add_argument("--task", type=str, default="", help="Chỉ định tác vụ cụ thể (vd: youtube, news, search)")
    args = parser.parse_args()

    if args.all_groups and not args.confirm_all_groups:
        logger.error("[SAFETY_GUARD] Cờ --all-groups yêu cầu kèm theo --confirm-all-groups để kích hoạt!")
        sys.exit(1)

    state = load_state()
    now_ts = time.time()

    all_profiles = get_all_gpm_profiles()
    if not all_profiles:
        logger.error("Không lấy được danh sách profile từ GPM API! Hãy kiểm tra GPMLogin đang chạy.")
        sys.exit(1)

    # Lọc danh sách profile hợp lệ theo chính sách GroupId và Exclusion Keywords
    target_group_id = args.group_id
    allow_all_groups = args.all_groups

    candidates, skipped_group, skipped_blacklist = filter_nurture_candidates(
        all_profiles,
        target_group_id=target_group_id,
        allow_all_groups=allow_all_groups,
        exclude_keywords=tuple(args.exclude_keywords)
    )

    if skipped_blacklist > 0:
        logger.warning(f"[BLACKLIST_ALERT] Phát hiện và lọc bỏ {skipped_blacklist} profile chứa từ khóa bị cấm!")

    log_telemetry_metric("filter_candidates_summary", {
        "total_profiles_found": len(all_profiles),
        "eligible_candidates": len(candidates),
        "target_group_id": target_group_id,
        "allow_all_groups": allow_all_groups,
        "skipped_wrong_group": skipped_group,
        "skipped_blacklist": skipped_blacklist
    })

    logger.info(
        f"Tổng số profile Gmail tìm thấy trên GPM: {len(all_profiles)} | "
        f"Đủ điều kiện nuôi (Group {target_group_id}): {len(candidates)} | "
        f"Lọc bỏ: {skipped_group} (khác GroupId), {skipped_blacklist} (blacklist)"
    )

    target_profiles = []
    if args.email:
        target_email = args.email.strip().lower()
        matched = [p for p in candidates if p["email"] == target_email]
        if not matched:
            logger.error(f"Không tìm thấy profile có email '{target_email}' trong GPM!")
            sys.exit(1)
        if not has_google_session(matched[0].get("profile_path")):
            logger.error(f"[{target_email}] Preflight Cookie: Profile không có session Google trên đĩa! Dừng nuôi.")
            update_profile_state(target_email, {"status": "NEEDS_LOGIN", "profile_id": matched[0].get("id"), "last_checked": now_ts})
            sys.exit(1)
        target_profiles = matched[:1]
    else:
        # Lọc profile chưa nuôi hoặc đã nuôi > 5 ngày
        due_profiles = []
        for p in candidates:
            em = p["email"]
            info = state.get(em, {})
            if info.get("status") == "NEEDS_LOGIN":
                continue
            if not has_google_session(p.get("profile_path")):
                logger.warning(f"[{em}] Preflight Cookie: Profile thiếu cookie Google session trên đĩa -> set NEEDS_LOGIN")
                log_telemetry_metric("preflight_cookie_rejected", {"email": em, "profile_id": p.get("id"), "status": "NEEDS_LOGIN"})
                update_profile_state(em, {"status": "NEEDS_LOGIN", "profile_id": p.get("id"), "last_checked": now_ts})
                continue
            last_nurtured = info.get("last_nurtured", 0)
            if (now_ts - last_nurtured) >= NURTURE_INTERVAL_SECONDS:
                due_profiles.append((last_nurtured, p))

        # Ưu tiên nuôi những profile lâu chưa nuôi nhất
        due_profiles.sort(key=lambda x: x[0])
        target_profiles = [p for _, p in due_profiles[:args.limit]]

    if not target_profiles:
        logger.info("Không có profile nào cần nuôi trong tick này (tất cả đều nuôi < 5 ngày trước). Hoàn thành.")
        return

    # Jitter Injection khi chạy tự động
    if not args.email:
        jitter_s = random.randint(10, 60)
        logger.info(f"Áp dụng Cron Jitter Delay: nghỉ {jitter_s}s trước khi bắt đầu đợt nuôi...")
        time.sleep(jitter_s)

    logger.info(f"Số lượng profile sẽ nuôi trong phiên này: {len(target_profiles)} (Concurrency={args.concurrency}, Stagger={args.stagger}s)")
    
    from concurrent.futures import ThreadPoolExecutor
    
    def worker_task(item):
        idx, p = item
        em = p["email"]
        # Áp dụng Staggered Launch (khởi động so le giữa các profile)
        if idx > 1:
            delay = (idx - 1) * args.stagger + random.randint(5, 15)
            logger.info(f"[{em}] Đợi giãn cách so le {delay}s trước khi mở...")
            time.sleep(delay)
            
        logger.info(f"\n--- Tiến hành nuôi [{idx}/{len(target_profiles)}]: {em} ---")
        t_start = time.time()
        ok, reason = nurture_profile(p, task_override=args.task)
        dur = round(time.time() - t_start, 1)
        if ok:
            update_profile_state(em, {
                "last_nurtured": time.time(),
                "last_nurtured_iso": datetime.now().isoformat(),
                "status": "success",
                "duration_seconds": dur,
                "profile_id": p["id"]
            })
            logger.info(f"[{em}] Đã cập nhật trạng thái vào state file (Thời gian: {dur}s).")
            status_label = f"OK ({dur}s)"
        else:
            if reason == "NEEDS_LOGIN":
                status_label = f"CHƯA_LOGIN (NEEDS_LOGIN, {dur}s)"
            else:
                status_label = f"FAIL ({reason}, {dur}s)"
            logger.warning(f"[{em}] Nuôi thất bại hoặc có lỗi nghiêm trọng: {reason} ({dur}s).")

        ss_path = os.path.join(SCREENSHOT_DIR, f"nurture_{em}.png")
        log_telemetry_metric("profile_nurture_complete", {
            "email": em,
            "ok": ok,
            "duration_s": dur,
            "status": status_label
        })
        return {
            "email": em,
            "ok": ok,
            "duration_s": dur,
            "status": status_label,
            "screenshot": ss_path if (ok and os.path.exists(ss_path)) else None,
        }

    items = list(enumerate(target_profiles, 1))
    if args.concurrency > 1:
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            results = list(executor.map(worker_task, items))
    else:
        results = [worker_task(it) for it in items]

    logger.info("\n========== Tất cả tiến trình nuôi trong lượt này đã hoàn tất ==========")

    success_count = sum(1 for r in results if r["ok"])
    total_count = len(results)

    log_telemetry_metric("batch_nurture_summary", {
        "success_count": success_count,
        "total_count": total_count,
        "success_rate": round(success_count / total_count, 2) if total_count > 0 else 0
    })

    if success_count < total_count:
        failed_items = [f"{r['email']}: {r['status']}" for r in results if not r.get("ok")]
        err_detail = "; ".join(failed_items)[:100]
        print(f"❌ [GPM Nurture Alert] Lỗi {total_count - success_count}/{total_count} profile: {err_detail}", flush=True)
    else:
        logger.info(f"✓ Hoàn tất nuôi toàn bộ {success_count}/{total_count} profile thành công (Silent Watchdog).")

if __name__ == "__main__":
    main()
