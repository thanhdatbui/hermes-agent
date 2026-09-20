#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cron_gpm_gmail_nurture.py - Chuyên biệt nuôi định kỳ Gmail trên GPMLogin.

Đặc điểm:
- Chạy HOÀN TOÀN ĐỘC LẬP trên PC qua GPM Chromium & Proxy 4G (KHÔNG đụng tới S7/ADB).
- Quản lý trạng thái nuôi bằng file JSON: D:/Taadaa/runtime/kibe/cron-state/gpm_gmail_nurture_state.json.
- Lọc profile chưa nuôi hoặc nuôi > 5 ngày trước (mặc định BATCH_SIZE = 2, chạy tuần tự an toàn).
- Thao tác tự nhiên & xáo trộn thứ tự tác vụ (Task Shuffling):
  + YouTube: tìm & click phát video ngẫu nhiên, xem 60-90s, chụp ảnh nghiệm thu nurture_{email}.png.
  + Google News: lướt tin 45-60s, cuộn trang mượt mà (human_scroll), click 1 bài báo bất kỳ.
  + Google Search: search từ khóa đời sống ngẫu nhiên, cuộn mượt mà xem kết quả 10-15s.
- Hỗ trợ CLI: --email <email> (test canary lẻ) và --limit <int> (mặc định 2).
"""

import os
import sys
import time
import json
import random
import re
import argparse
import logging
import urllib.parse
from typing import Optional
from datetime import datetime
import sqlite3
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright

# --- Config & Paths ---
GPM_DB = Path(r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db")
LOG_DIR = r"D:\Taadaa\GPM auto\logs"
LOG_FILE = os.path.join(LOG_DIR, "cron_gpm_gmail_nurture.log")
GPM_API_BASE = "http://127.0.0.1:19995/api/v3"
STATE_FILE = r"D:\Taadaa\runtime\kibe\cron-state\gpm_gmail_nurture_state.json"
SCREENSHOT_DIR = r"D:\Taadaa\GPM auto\debug_screenshots"
NURTURE_INTERVAL_SECONDS = 5 * 86400  # 5 ngày

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
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("gpm_gmail_nurture")

SEARCH_QUERIES = [
    "thoi tiet hom nay", "tin tuc 24h", "gia vang hom nay",
    "bong da ngoai hang anh", "cong nghe ai moi nhat",
    "dia diem du lich dep viet nam", "am thuc mien tay",
    "meo vat cuoc song", "dien thoai tot nhat 2026",
    "kinh te viet nam nam nay", "xe dien vinfast moi"
]

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Lỗi đọc state file, khởi tạo mới: {e}")
    return {}

def save_state(state: dict):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Lỗi lưu state file: {e}")

def get_emails_with_session() -> set:
    """Kiểm tra các profile GPM đã có sẵn session cookie Google (đã login thành công)."""
    emails_with_session = set()
    if not GPM_DB.exists():
        logger.warning(f"GPM DB không tồn tại tại {GPM_DB}")
        return emails_with_session
    try:
        uri = f"file:{GPM_DB}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        cur = conn.cursor()
        cur.execute("SELECT Name, ProfilePath FROM profiles;")
        rows = cur.fetchall()
        conn.close()

        base_prof_dir = GPM_DB.parent
        for name, ppath in rows:
            if not name or not ppath:
                continue
            em = extract_email(name)
            if not em:
                continue
            p_folder = base_prof_dir / ppath
            for cp in [p_folder / 'Default' / 'Network' / 'Cookies', p_folder / 'Default' / 'Cookies']:
                if cp.exists():
                    try:
                        c_uri = f"file:{cp}?mode=ro"
                        c_conn = sqlite3.connect(c_uri, uri=True)
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
        logger.error(f"Lỗi kiểm tra session cookie GPM: {e}")
    return emails_with_session

def get_all_gpm_profiles() -> list:
    url = f"{GPM_API_BASE}/profiles?page=1&per_page=300"
    try:
        res = requests.get(url, timeout=15).json()
        data = res.get("data")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("list", [])
        return []
    except Exception as e:
        logger.error(f"Lỗi kết nối GPM API: {e}")
        return []

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
    try:
        requests.get(f"{GPM_API_BASE}/profiles/stop/{profile_id}", timeout=15)
    except Exception:
        pass

def extract_email(name: str) -> str:
    m = re.search(r'([a-zA-Z0-9_.+-]+@gmail\.com)', name)
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

# ==============================================================================
# CÁC TÁC VỤ NUÔI ĐỘC LẬP (Modular Sub-Tasks)
# ==============================================================================

def task_youtube(context, yt_page, email: str, ss_path: str):
    """Tác vụ YouTube: Duyệt trang, tìm & phát video /watch, xem và né ad thông minh."""
    logger.info(f"[{email}] [Task: YouTube] Mở https://www.youtube.com...")
    try:
        if yt_page.is_closed():
            yt_page = context.new_page()

        yt_page.goto("https://www.youtube.com", timeout=35000, wait_until="domcontentloaded")
        time.sleep(random.uniform(3.0, 4.0))

        # Cuộn nhẹ trang chủ khám phá feed
        human_scroll(yt_page, random.randint(300, 600), steps=4)
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

        # NẾU BỊ TRỐNG FEED:
        if is_yt_empty(yt_page):
            logger.info(f"[{email}] Trang chủ YouTube trống, chuyển qua Shorts xem 5-8s để bung feed...")
            try:
                shorts_btn = yt_page.locator("a[title='Shorts'], a#endpoint[title='Shorts']").first
                if shorts_btn.count() > 0 and shorts_btn.is_visible():
                    shorts_btn.click(force=True)
                else:
                    yt_page.goto("https://www.youtube.com/shorts", timeout=20000, wait_until="domcontentloaded")
                time.sleep(random.uniform(5.0, 8.0))
            except Exception as e_sh:
                logger.warning(f"[{email}] Lỗi mở Shorts: {e_sh}")

            # Sau đó click lại Trang chủ
            try:
                home_btn = yt_page.locator("a#logo, a[title='Trang chủ YouTube'], a[title='YouTube Home']").first
                if home_btn.count() > 0 and home_btn.is_visible():
                    home_btn.click(force=True)
                else:
                    yt_page.goto("https://www.youtube.com", timeout=20000, wait_until="domcontentloaded")
                time.sleep(4)
            except Exception as e_hm:
                logger.warning(f"[{email}] Lỗi quay lại Trang chủ: {e_hm}")

        # NẾU VẪN CHƯA CÓ VIDEO:
        if is_yt_empty(yt_page):
            logger.info(f"[{email}] Feed vẫn trống, tìm kiếm từ khóa ngẫu nhiên...")
            try:
                kw = random.choice(["nhac tre", "tin tuc hom nay", "review phim"])
                search_inp = yt_page.locator("input#search, input[name='search_query']").first
                if search_inp.count() > 0:
                    search_inp.fill(kw)
                    yt_page.keyboard.press("Enter")
                    time.sleep(4)
                else:
                    yt_page.goto(f"https://www.youtube.com/results?search_query={urllib.parse.quote(kw)}", timeout=25000, wait_until="domcontentloaded")
                    time.sleep(4)
            except Exception as e_sr:
                logger.warning(f"[{email}] Lỗi search YouTube: {e_sr}")

        # CLICK VÀO VIDEO THẬT ĐỂ PHÁT (TRÁNH QUẢNG CÁO + BẮT BUỘC VÀO /watch):
        video_links = yt_page.locator("a#video-title-link[href*='/watch'], ytd-rich-grid-media a#video-title-link, a#thumbnail[href*='/watch'], ytd-video-renderer a#video-title[href*='/watch']")
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
                    yt_page.goto(target_url, timeout=25000, wait_until="domcontentloaded")
        else:
            fallback_links = yt_page.locator("a[href*='/watch']")
            for j in range(min(fallback_links.count(), 10)):
                fb = fallback_links.nth(j)
                h = fb.get_attribute("href") or ""
                if "/watch" in h and "ad" not in h.lower():
                    target_url = h if h.startswith("http") else f"https://www.youtube.com{h}"
                    yt_page.goto(target_url, timeout=25000, wait_until="domcontentloaded")
                    break

        try:
            yt_page.wait_for_url("**/watch*", timeout=15000)
        except Exception:
            pass

        time.sleep(5)
        try:
            yt_page.keyboard.press("k")
        except Exception:
            pass

        watch_duration = random.randint(90, 120)
        logger.info(f"[{email}] Đang xem YouTube video trong {watch_duration}s (Smart Ad Skip & Watch Simulation)...")
        ad_selector = "button.ytp-skip-ad-button, .ytp-ad-skip-button, button.ytp-ad-skip-button-modern, [class*='ytp-ad-skip-button']"
        start_watch = time.time()
        ad_ignored = False
        ss_taken = False

        while time.time() - start_watch < watch_duration:
            elapsed = time.time() - start_watch
            try:
                skip_btn = yt_page.locator(ad_selector).first
                if skip_btn.is_visible():
                    if not ad_ignored:
                        if random.random() < 0.70:
                            delay = round(random.uniform(2.0, 5.5), 2)
                            time.sleep(delay)
                            try:
                                skip_btn.hover(timeout=2000)
                            except Exception:
                                pass
                            skip_btn.click(force=True, timeout=2000)
                            logger.info(f"[{email}] Đã bấm Bỏ qua quảng cáo (sau delay ngẫu nhiên)")
                        else:
                            logger.info(f"[{email}] Giữ nguyên cho quảng cáo chạy tự nhiên")
                            ad_ignored = True
                else:
                    ad_ignored = False
            except Exception:
                pass

            # Chụp ảnh debug khi video đã chạy ổn định >= 25s (tránh trúng preroll ad)
            if elapsed >= 25 and not ss_taken:
                try:
                    yt_page.screenshot(path=ss_path, timeout=5000, animations="disabled", type="jpeg", quality=80)
                    logger.info(f"[{email}] ✓ Đã lưu ảnh debug video đang phát ({int(elapsed)}s): {ss_path}")
                    ss_taken = True
                except Exception as e_ss:
                    logger.warning(f"[{email}] Lỗi chụp screenshot: {e_ss}")

            time.sleep(2)

        if not ss_taken:
            try:
                yt_page.screenshot(path=ss_path, timeout=5000, animations="disabled", type="jpeg", quality=80)
            except Exception:
                pass

        logger.info(f"[{email}] ✓ Hoàn thành xem YouTube ({watch_duration}s).")
    except Exception as e_yt:
        logger.warning(f"[{email}] Lỗi trong luồng YouTube: {e_yt}")
        if not os.path.exists(ss_path):
            try:
                yt_page.screenshot(path=ss_path, timeout=5000)
            except Exception:
                pass

def task_google_news(context, email: str):
    """Tác vụ Google News: Lướt tin tức, cuộn trang mượt mà và đọc 1 bài báo."""
    logger.info(f"[{email}] [Task: Google News] Mở https://news.google.com...")
    try:
        news_page = context.new_page()
        news_page.goto("https://news.google.com", timeout=35000, wait_until="domcontentloaded")
        time.sleep(3)

        # Cuộn trang ngẫu nhiên đọc lướt bằng human_scroll
        for _ in range(3):
            human_scroll(news_page, random.randint(350, 650), steps=random.randint(4, 6))
            time.sleep(random.uniform(1.5, 3.0))

        # Click vào 1 bài báo thật sự (mở tab bài báo mới hoặc chuyển trang)
        article_link = news_page.locator("article a[href*='./read/'], article a[href*='/articles/'], article a, c-wiz a[href*='./read/'], c-wiz a[href*='/articles/']").first
        reading_page = news_page
        if article_link.count() > 0:
            try:
                with context.expect_page(timeout=5000) as new_page_info:
                    article_link.click(force=True)
                new_art_page = new_page_info.value
                new_art_page.wait_for_load_state("domcontentloaded", timeout=20000)
                reading_page = new_art_page
                logger.info(f"[{email}] Đã click mở bài báo tab mới: {reading_page.url}")
            except Exception:
                try:
                    article_link.click(force=True)
                    logger.info(f"[{email}] Đã click bài báo trên trang hiện tại.")
                except Exception as e_art:
                    logger.warning(f"[{email}] Click bài báo thất bại: {e_art}")

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

        try:
            if reading_page != news_page:
                reading_page.close()
            news_page.close()
        except Exception:
            pass
        logger.info(f"[{email}] ✓ Hoàn thành đọc báo Google News ({read_duration}s).")
    except Exception as e_news:
        logger.warning(f"[{email}] Lỗi trong luồng Google News: {e_news}")

def task_google_search(context, email: str):
    """Tác vụ Google Search: Tìm kiếm từ khóa đời sống, cuộn mượt mà xem kết quả."""
    q = random.choice(SEARCH_QUERIES)
    logger.info(f"[{email}] [Task: Google Search] Tìm kiếm Google với từ khóa: '{q}'...")
    try:
        search_page = context.new_page()
        search_url = f"https://www.google.com/search?q={urllib.parse.quote(q)}"
        search_page.goto(search_url, timeout=35000, wait_until="domcontentloaded")
        time.sleep(2)

        # Cuộn nhẹ trang kết quả bằng human_scroll
        human_scroll(search_page, random.randint(250, 500), steps=random.randint(3, 5))
        stay_duration = random.randint(10, 15)
        logger.info(f"[{email}] Dừng lại xem kết quả tìm kiếm trong {stay_duration}s...")
        time.sleep(stay_duration)

        search_page.close()
        logger.info(f"[{email}] ✓ Hoàn thành tìm kiếm Google.")
    except Exception as e_search:
        logger.warning(f"[{email}] Lỗi trong luồng Google Search: {e_search}")

# ==============================================================================
# HÀM ĐIỀU PHỐI NUÔI 1 PROFILE
# ==============================================================================

def nurture_profile(p: dict) -> bool:
    p_id = p["id"]
    email = p["email"]
    p_name = p.get("name", "")
    logger.info(f"========== Bắt đầu nuôi profile: {email} (ID: {p_id}, Name: {p_name}) ==========")

    addr = start_gpm_profile(p_id)
    if not addr:
        logger.error(f"[{email}] Không thể khởi động profile GPM!")
        return False

    time.sleep(2)
    ss_path = os.path.join(SCREENSHOT_DIR, f"nurture_{email}.png")

    try:
        with sync_playwright() as pw:
            logger.info(f"[{email}] Kết nối Playwright tới CDP {addr}...")
            browser = pw.chromium.connect_over_cdp(f"http://{addr}", timeout=20000)
            context = browser.contexts[0]

            # Kiểm tra live session Google trong context
            live_cookies = context.cookies(["https://accounts.google.com", "https://www.youtube.com", "https://google.com"])
            found_session = {c.get("name") for c in live_cookies if c.get("name") in ('SID', 'SSID', 'HSID', 'SAPISID')}
            if len(found_session) < 2:
                logger.warning(f"[{email}] CẢNH BÁO: Profile chưa login Google hoặc mất session (chỉ thấy {len(found_session)} token). Dừng nuôi để tránh lãng phí!")
                state_cur = load_state()
                entry = state_cur.get(email, {})
                entry.update({
                    "last_checked": time.time(),
                    "last_checked_iso": datetime.now().isoformat(),
                    "status": "NEEDS_LOGIN",
                    "profile_id": p_id
                })
                state_cur[email] = entry
                save_state(state_cur)
                browser.close()
                return False

            pages = [pg for pg in context.pages if not pg.url.startswith("chrome-extension://")]
            yt_page = pages[0] if pages else context.new_page()

            # 1. XÁO TRỘN THỨ TỰ TÁC VỤ (Task Shuffling & Behavioral Entropy)
            tasks = [task_youtube, task_google_news, task_google_search]
            random.shuffle(tasks)
            task_names = [t.__name__.replace('task_', '').capitalize() for t in tasks]
            logger.info(f"[{email}] Thứ tự tác vụ đã xáo trộn ngẫu nhiên: {' -> '.join(task_names)}")

            for idx, task_fn in enumerate(tasks, 1):
                logger.info(f"[{email}] [{idx}/3] Tiến hành: {task_fn.__name__}...")
                if task_fn == task_youtube:
                    task_fn(context, yt_page, email, ss_path)
                else:
                    task_fn(context, email)

                # Nghỉ ngẫu nhiên giữa các tác vụ (3 - 6 giây)
                if idx < len(tasks):
                    pause_s = round(random.uniform(3.0, 6.0), 2)
                    logger.info(f"[{email}] Nghỉ giữa các tác vụ {pause_s}s...")
                    time.sleep(pause_s)

            browser.close()
            logger.info(f"[{email}] Đã hoàn thành toàn bộ luồng nuôi!")
            return True

    except Exception as e:
        logger.error(f"[{email}] Lỗi bất thường trong quá trình nuôi: {e}")
        return False
    finally:
        logger.info(f"[{email}] Đang tắt profile GPM {p_id} an toàn...")
        stop_gpm_profile(p_id)
        time.sleep(2)

def main():
    parser = argparse.ArgumentParser(description="Chương trình nuôi định kỳ Gmail trên GPMLogin")
    parser.add_argument("--email", type=str, default="", help="Chỉ định email cần nuôi (chạy canary đơn lẻ)")
    parser.add_argument("--limit", type=int, default=2, help="Số lượng profile nuôi trong mỗi tick (mặc định 2)")
    parser.add_argument("--concurrency", type=int, default=1, help="Số worker chạy song song so le (mặc định 1)")
    parser.add_argument("--stagger", type=int, default=45, help="Độ trễ giãn cách khởi động so le giữa các profile (giây)")
    args = parser.parse_args()

    state = load_state()
    now_ts = time.time()

    all_profiles = get_all_gpm_profiles()
    if not all_profiles:
        logger.error("Không lấy được danh sách profile từ GPM API! Hãy kiểm tra GPMLogin đang chạy.")
        sys.exit(1)

    # Lọc danh sách profile có session Google hợp lệ
    emails_with_session = get_emails_with_session()
    logger.info(f"Tổng số profile Gmail có session Google hợp lệ: {len(emails_with_session)}")

    candidates = []
    for p in all_profiles:
        name = p.get("name", "")
        email = extract_email(name)
        if not email:
            continue
        if email not in emails_with_session:
            continue
        p_copy = dict(p)
        p_copy["email"] = email
        candidates.append(p_copy)

    logger.info(f"Tổng số profile Gmail sẵn sàng nuôi (đã login): {len(candidates)}")

    target_profiles = []
    if args.email:
        target_email = args.email.strip().lower()
        matched = [p for p in candidates if p["email"] == target_email]
        if not matched:
            logger.error(f"Không tìm thấy profile có email '{target_email}' trong GPM!")
            sys.exit(1)
        target_profiles = matched[:1]
    else:
        # Lọc profile chưa nuôi hoặc đã nuôi > 5 ngày
        due_profiles = []
        for p in candidates:
            em = p["email"]
            info = state.get(em, {})
            last_nurtured = info.get("last_nurtured", 0)
            if (now_ts - last_nurtured) >= NURTURE_INTERVAL_SECONDS:
                due_profiles.append((last_nurtured, p))

        # Ưu tiên nuôi những profile lâu chưa nuôi nhất
        due_profiles.sort(key=lambda x: x[0])
        target_profiles = [p for _, p in due_profiles[:args.limit]]

    if not target_profiles:
        logger.info("Không có profile nào cần nuôi trong tick này (tất cả đều nuôi < 5 ngày trước). Hoàn thành.")
        return

    # 3. ĐỘ LỆCH THỜI GIAN NGẪU NHIÊN KHI BẮT ĐẦU CRON (Jitter Injection)
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
        ok = nurture_profile(p)
        if ok:
            state_cur = load_state()
            state_cur[em] = {
                "last_nurtured": time.time(),
                "last_nurtured_iso": datetime.now().isoformat(),
                "status": "success",
                "profile_id": p["id"]
            }
            save_state(state_cur)
            logger.info(f"[{em}] Đã cập nhật trạng thái vào state file.")
        else:
            logger.warning(f"[{em}] Nuôi thất bại hoặc có lỗi nghiêm trọng.")

        ss_path = os.path.join(SCREENSHOT_DIR, f"nurture_{em}.png")
        return {
            "email": em,
            "ok": ok,
            "status": "OK" if ok else "FAIL",
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

    report_lines = [
        f"✓ [GPM Nurture] Hoàn tất nuôi {success_count}/{total_count} profile Gmail:"
    ]
    for r in results:
        report_lines.append(f"- {r['email']}: {r['status']}")

    print("\n".join(report_lines), flush=True)

if __name__ == "__main__":
    main()
