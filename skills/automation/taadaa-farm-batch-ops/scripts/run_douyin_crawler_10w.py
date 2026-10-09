#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Douyin Feed AI Crawler (10 Workers) with Dual AI Filter & Grid Image Evidence.
Flow:
1. Connect to Chrome CDP (port 9222) where Douyin tab is open.
2. Extract live cookie from Douyin page context.
3. Scroll and collect video candidate URLs from Douyin feed, filtering out blacklist keywords.
4. Concurrently download with 10 workers using `f2 dy -u <url> -M one -k <cookie> -p <temp_dir>`.
5. Apply Dual AI Filters:
   - Gate 1: ViT ONNX female confidence >= 0.75.
   - Gate 2: faster-whisper pure BGM (reject Chinese voice and continuous speech).
6. Save qualifying videos to target folder (default: evidence/douyin_clean_girls).
7. Extract frame at second 2 from each video and compose a contact-sheet grid image evidence.
"""
import argparse
import json
import logging
import os
import shutil
import socket
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from PIL import Image
import requests

try:
    from scripts.ai_channel_filter import AIFemaleFilter
except ImportError:
    from ai_channel_filter import AIFemaleFilter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("douyin_crawler_10w")

DEFAULT_EVIDENCE_DIR = Path("C:/Users/Kibe/AppData/Local/hermes/evidence/douyin_clean_girls")
DEFAULT_GRID_IMAGE = Path("C:/Users/Kibe/AppData/Local/hermes/evidence/douyin_clean_girls_grid.jpg")
DEFAULT_TEMP_DIR = Path("C:/Users/Kibe/AppData/Local/hermes/evidence/douyin_temp_crawler")

DOUYIN_BLACKLIST_KEYWORDS = [
    "动漫", "动画", "二次元", "漫剧", "ai漫剧", "ai动画", "ai画",
    "游戏", "王者", "吃鸡", "原神", "无畏契约", "我的世界", "英雄联盟",
    "段子", "搞笑", "电影", "影视", "解说", "纪录片", "美食", "做饭",
    "萌宠", "奶龙", "奥特曼", "小猪佩奇", "沙雕", "测评", "数码", "车",
    "anime", "review", "3d"
]

def get_douyin_cdp(cdp_port: int = 9222) -> Tuple[Optional[str], Optional[str]]:
    try:
        resp = requests.get(f"http://127.0.0.1:{cdp_port}/json", timeout=5).json()
        for tab in resp:
            url = tab.get("url", "")
            if "douyin.com" in url and tab.get("type") == "page":
                return tab.get("webSocketDebuggerUrl"), url
    except Exception as e:
        logger.error(f"Cannot connect to Chrome CDP at port {cdp_port}: {e}")
    return None, None

def cdp_send(ws_url: str, method: str, params: dict = None) -> dict:
    parsed = urlparse(ws_url)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10.0)
    sock.connect((parsed.hostname, parsed.port))
    key = "dGhlIHNhbXBsZSBub25jZQ=="
    req = (
        f"GET {parsed.path} HTTP/1.1\r\n"
        f"Host: {parsed.hostname}:{parsed.port}\r\n"
        "Upgrade: websocket\r\nConnection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
    )
    sock.sendall(req.encode())
    sock.recv(4096)
    msg = json.dumps({"id": 1, "method": method, "params": params or {}}).encode()
    frame = bytearray([0x81])
    if len(msg) < 126:
        frame.append(0x80 | len(msg))
    else:
        frame.append(0x80 | 126)
        frame.extend(len(msg).to_bytes(2, "big"))
    mask = os.urandom(4)
    frame.extend(mask)
    frame.extend(bytearray(msg[i] ^ mask[i % 4] for i in range(len(msg))))
    sock.sendall(frame)

    buf = b""
    while True:
        try:
            chunk = sock.recv(65536)
            if not chunk:
                break
            buf += chunk
            if b'{"id":1' in buf and (b'"result":' in buf or b'"error":' in buf):
                idx = buf.find(b'{"id":1')
                raw = json.loads(buf[idx:].decode("utf-8", errors="ignore"))
                sock.close()
                return raw.get("result", {})
        except Exception:
            break
    sock.close()
    return {}

def get_cookie(ws_url: str) -> str:
    res = cdp_send(ws_url, "Runtime.evaluate", {"expression": "document.cookie", "returnByValue": True})
    val = res.get("result", {}).get("value", "")
    if val and len(val) > 20:
        return val
    res2 = cdp_send(ws_url, "Network.getCookies", {"urls": ["https://www.douyin.com"]})
    return "; ".join([f"{c['name']}={c['value']}" for c in res2.get("cookies", [])])

def collect_candidates(ws_url: str, limit: int = 40) -> List[str]:
    vids = set()
    for _ in range(20):
        cdp_send(ws_url, "Runtime.evaluate", {"expression": "window.scrollBy(0, 1500)"})
        time.sleep(1.2)
        js = '''(() => {
            const res = [];
            document.querySelectorAll('div[href*="/video/"], a[href*="/video/"]').forEach(el => {
                const h = el.getAttribute('href') || el.href;
                const text = (el.innerText || '') + ' ' + (el.parentElement ? el.parentElement.innerText : '');
                if (h) res.push({url: h, text: text});
            });
            return res;
        })()'''
        r = cdp_send(ws_url, "Runtime.evaluate", {"expression": js, "returnByValue": True})
        items = r.get("result", {}).get("value", [])
        for it in items:
            u = it.get("url", "")
            t = it.get("text", "").lower()
            if any(k in t for k in DOUYIN_BLACKLIST_KEYWORDS):
                continue
            if "/video/" in u:
                vid = u.split("/video/")[-1].split("?")[0].strip("/")
                if vid.isdigit():
                    vids.add(f"https://www.douyin.com/video/{vid}")
        if len(vids) >= limit:
            break
    return list(vids)

def download_and_verify(video_url: str, cookie: str, ai_filter: AIFemaleFilter, temp_dir: Path) -> Optional[Path]:
    vid_id = video_url.split("/video/")[-1].split("?")[0]
    out_dir = temp_dir / f"f2_{vid_id}_{threading.get_ident()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["f2", "dy", "-u", video_url, "-M", "one", "-k", cookie, "-p", str(out_dir)]
    subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    mp4s = list(out_dir.rglob("*.mp4"))
    if not mp4s:
        shutil.rmtree(out_dir, ignore_errors=True)
        return None

    video_file = max(mp4s, key=lambda p: p.stat().st_mtime)

    # Gate 1: ViT Female Filter >= 0.75
    passed, score, reason = ai_filter.verify_video_is_female(str(video_file))
    if not passed or score < 0.75:
        logger.info(f"  [AI REJECT VISUAL] {vid_id} score={score:.2f} ({reason})")
        shutil.rmtree(out_dir, ignore_errors=True)
        return None

    # Gate 2: Audio pure music / no speech
    if hasattr(ai_filter, "verify_audio_no_speech"):
        a_pass, a_stat, a_reason = ai_filter.verify_audio_no_speech(str(video_file))
        if not a_pass:
            logger.info(f"  [AI REJECT AUDIO] {vid_id} ({a_reason})")
            shutil.rmtree(out_dir, ignore_errors=True)
            return None

    logger.info(f"  [AI PASS ALL] {vid_id}: score={score:.2f}")
    return video_file

def create_grid(video_paths: List[Path], out_grid: Path, temp_dir: Path):
    frames = []
    for vp in video_paths:
        f_path = temp_dir / f"frame_{vp.stem}.jpg"
        cmd = ["ffmpeg", "-y", "-ss", "2.0", "-i", str(vp), "-vframes", "1", "-q:v", "2", str(f_path)]
        subprocess.run(cmd, capture_output=True)
        if f_path.exists():
            frames.append(Image.open(f_path).convert("RGB"))

    if not frames:
        return

    n = len(frames)
    cols = min(n, 5)
    rows = (n + cols - 1) // cols
    w, h = 360, 640
    grid = Image.new("RGB", (cols * w, rows * h), (0, 0, 0))

    for idx, img in enumerate(frames):
        img_resized = img.resize((w, h))
        c = idx % cols
        r = idx // cols
        grid.paste(img_resized, (c * w, r * h))

    out_grid.parent.mkdir(parents=True, exist_ok=True)
    grid.save(out_grid, quality=90)
    logger.info(f"[GRID SAVED] {out_grid}")
