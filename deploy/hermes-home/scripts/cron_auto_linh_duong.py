#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Watchdog tự động tìm và đẩy con 'Linh Dương' sáng sớm (06:00 AM).
Sử dụng chính model Gemini đang chạy Hermes (ag-gemini-pool-3 qua OmniRoute :20129) để suy luận.
Đính kèm Direct Link 1-click trên Telegram để User bấm là nhảy thẳng vào Topic làm dở.
Có cơ chế fallback heuristic an toàn 100% không bao giờ trượt tin nhắn sáng sớm.
"""
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# Đảm bảo UTF-8 cho stdout trên Windows
reconf = getattr(sys.stdout, "reconfigure", None)
if callable(reconf):
    reconf(encoding="utf-8")

STATE_DB = os.environ.get(
    "HERMES_STATE_DB", 
    str(Path.home() / "AppData" / "Local" / "hermes" / "state.db")
)
OMNI_URL = "http://127.0.0.1:20129/v1/chat/completions"
MODEL_NAME = "ag-gemini-pool-3"
CHAT_ID = "1076231895"

HIGH_PRIORITY_PATTERNS = [
    re.compile(r'\b' + re.escape(w) + r'\b', re.IGNORECASE)
    for w in ["lỗi", "fix", "gate", "script", "upload", "feed", "runner", "sync", 
             "proxy", "farm", "openwrt", "watchdog", "healer", "refactor", "bug", "crash"]
]

RE_CLOSEOUT_APPROVED = re.compile(r'closeout\s+approved|verdict:\s*approved', re.IGNORECASE)
RE_CLOSEOUT_REJECTED = re.compile(r'closeout\s+rejected|verdict:\s*rejected|strike\s+\d|blocked', re.IGNORECASE)

def get_candidates():
    if not os.path.exists(STATE_DB):
        return [], f"Không tìm thấy file state.db tại: {STATE_DB}"
    
    conn = None
    try:
        norm_path = Path(STATE_DB).as_posix()
        encoded_path = urllib.parse.quote(norm_path)
        db_uri = f"file:{encoded_path}?mode=ro"
        conn = sqlite3.connect(db_uri, uri=True, timeout=10.0)
        cur = conn.cursor()
        
        now_ts = time.time()
        cutoff_ts = now_ts - 86400
        
        cur.execute("""
            SELECT s.id, s.thread_id, s.title, s.last_activity_at, s.message_count
            FROM sessions s
            WHERE s.last_activity_at > ? AND s.thread_id IS NOT NULL
            ORDER BY s.last_activity_at DESC
            LIMIT 10
        """, (cutoff_ts,))
        rows = cur.fetchall()
        
        if not rows:
            cur.execute("""
                SELECT s.id, s.thread_id, s.title, s.last_activity_at, s.message_count
                FROM sessions s
                WHERE s.thread_id IS NOT NULL
                ORDER BY s.last_activity_at DESC
                LIMIT 5
            """)
            rows = cur.fetchall()
            
        candidates = []
        for r in rows:
            s_id, thread_id, title, last_act, msg_count = r
            cur.execute("""
                SELECT role, content FROM messages 
                WHERE session_id = ? AND role IN ('user', 'assistant') AND content IS NOT NULL AND content NOT LIKE '[%Task%]'
                ORDER BY id DESC LIMIT 4
            """, (s_id,))
            msgs = cur.fetchall()
            msgs.reverse()
            
            clean_exchanges = []
            for m in msgs:
                c_text = (m[1] or "").strip()
                if c_text:
                    clean_exchanges.append({"role": m[0], "text": c_text[:250]})

            full_exchange_text = " ".join((m[1] or "").strip() for m in msgs if (m[1] or "").strip())
            if RE_CLOSEOUT_APPROVED.search(full_exchange_text) or re.search(r'\b(done|xong|chốt\s+phiên|hoàn\s+tất)\b', full_exchange_text, re.IGNORECASE) and not RE_CLOSEOUT_REJECTED.search(full_exchange_text):
                continue

            candidates.append({
                "session_id": str(s_id),
                "thread_id": str(thread_id),
                "title": (title or "").strip() or "Không tiêu đề",
                "msg_count": msg_count or 0,
                "recent_exchanges": clean_exchanges
            })
        return candidates, None
    except Exception as exc:
        return [], f"Lỗi đọc state.db: {exc}"
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

def ask_gemini_for_linh_duong(candidates):
    if not candidates:
        return None
        
    prompt_data = json.dumps(candidates, ensure_ascii=False, indent=2)
    prompt = f"""Bạn là AI Coordinator tinh nhuệ của Hermes Agent. Dưới đây là danh sách các session làm việc gần đây của User:
{prompt_data}

Nhiệm vụ:
Theo triết lý Tim Ferriss (Linh Dương vs Chuột Đồng):
- Chuột Đồng: việc vụn vặt, định kỳ, lặp lại, kiểm tra lặt vặt, các task đã báo Closeout Approved/xong xuôi.
- Linh Dương: việc có đòn bẩy lớn nhất ĐANG DỞ DANG hoặc ĐANG CẦN GIẢI QUYẾT: nghẽn kiến trúc, lỗi script/flow cốt lõi chưa xong, task bị Closeout Rejected/Blocked, hoàn thiện gate/tính năng chặn lỗi hàng loạt.

Hãy chọn ra ĐÚNG 1 NHIỆM VỤ LÕI (Linh Dương) đang cần làm dở hoặc cần giải quyết nhất.
Trả về DUY NHẤT một khối JSON hợp lệ theo định dạng:
{{
  "thread_id": "<thread_id được chọn trong danh sách>",
  "mission": "<Tên nhiệm vụ ngắn gọn súc tích, tối đa 10 từ>",
  "current_status": "<Hiện trạng đang dừng ở đâu / nút thắt là gì, tối đa 2 dòng>",
  "action_prompt": "<Gợi ý 1 hành động/lệnh tiếp theo cụ thể cho User>"
}}
Không thêm bất kỳ văn bản giải thích nào ngoài khối JSON."""

    req_body = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a disciplined AI Coordinator. Output strictly JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    
    data = json.dumps(req_body).encode("utf-8")
    req = urllib.request.Request(
        OMNI_URL, 
        data=data, 
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            content = res_json["choices"][0]["message"]["content"]
            
            raw_text = content.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()
            
            start_idx = raw_text.find("{")
            end_idx = raw_text.rfind("}")
            if start_idx != -1 and end_idx != -1:
                raw_text = raw_text[start_idx:end_idx+1]
                
            parsed = json.loads(raw_text)
            if not isinstance(parsed, dict):
                return None
                
            valid_threads = {c["thread_id"] for c in candidates}
            if str(parsed.get("thread_id")) not in valid_threads:
                sys.stderr.write(f"[WARN] Thread ID '{parsed.get('thread_id')}' không khớp candidates -> Fallback\n")
                return None
                
            return parsed
    except Exception as exc:
        sys.stderr.write(f"[WARN] ask_gemini error: {exc}\n")
        return None

def fallback_heuristic(candidates):
    if not candidates:
        return None
        
    best = candidates[0]
    best_score = -999
    
    for c in candidates:
        score = 0
        t_str = c["title"]
        exchanges_str = " ".join([m.get("text", "") for m in c.get("recent_exchanges", [])])
        full_text = f"{t_str} {exchanges_str}"
        
        for pat in HIGH_PRIORITY_PATTERNS:
            if pat.search(full_text):
                score += 3
                
        if RE_CLOSEOUT_REJECTED.search(full_text):
            score += 15
            
        if RE_CLOSEOUT_APPROVED.search(full_text):
            score -= 20
            
        if c["msg_count"] > 30:
            score += 2
                
        if score > best_score:
            best_score = score
            best = c
            
    last_text = ""
    if best["recent_exchanges"]:
        last_text = best["recent_exchanges"][-1]["text"]
        
    return {
        "thread_id": best["thread_id"],
        "mission": best["title"],
        "current_status": f"Trao đổi gần nhất: \"{last_text[:150]}\"",
        "action_prompt": "Nhảy vào thread và gõ lệnh tiếp tục.",
        "_is_fallback": True
    }

def main():
    today_str = time.strftime("%Y-%m-%d")
    marker_file = Path("D:/Taadaa/runtime/linh_duong_last_run.txt")

    if '--force' not in sys.argv and '--test' not in sys.argv:
        # Chỉ chạy đúng trong khung 06:00 - 06:59 sáng
        if time.localtime().tm_hour != 6:
            return
        # Mỗi ngày chỉ chạy đúng 1 lần duy nhất, chống lặp lại
        if marker_file.exists():
            try:
                if marker_file.read_text(encoding="utf-8").strip() == today_str:
                    return
            except Exception:
                pass

    try:
        candidates, err = get_candidates()
        if err:
            sys.stderr.write(f"[WARN] {err}\n")
            return

        if not candidates:
            return

        decision = None
        is_fallback = False
        try:
            decision = ask_gemini_for_linh_duong(candidates)
        except Exception:
            decision = None

        if not decision or not isinstance(decision, dict) or not decision.get("mission"):
            decision = fallback_heuristic(candidates)
            is_fallback = True

        if not isinstance(decision, dict):
            return

        raw_mission = decision.get("mission")
        if raw_mission is None or str(raw_mission).strip().lower() in ("", "none", "null"):
            return

        thread_id = decision.get("thread_id", candidates[0]["thread_id"])
        mission = raw_mission
        status = decision.get("current_status", "Đang dở dang.")
        action = decision.get("action_prompt", "Tiếp tục xử lý.")
        tag = " *(Phân tích từ Gemini AG Pool)*" if not is_fallback else " *(Dự phòng Heuristic)*"
        
        # Tạo Telegram Direct Link 1-click
        if CHAT_ID == "1076231895" or not CHAT_ID.startswith("-100"):
            topic_link = "https://t.me/Taadaa_hermes_sever_bot"
        else:
            topic_link = f"https://t.me/c/{CHAT_ID}/{thread_id}"
        
        msg = (
            f"🦁 **[LINH DƯƠNG SÁNG NAY - ĐÒN BẨY SỐ 1]**{tag}\n\n"
            f"🎯 **Nhiệm vụ lõi:** {mission}\n"
            f"🧵 **Thread ID:** `{thread_id}`\n"
            f"📍 **Hiện trạng:** {status}\n\n"
            f"🔗 **Truy cập nhanh:** 👉 [BẤM VÀO ĐÂY ĐỂ VÀO PHIÊN ĐANG DỞ]({topic_link})\n\n"
            f"⚡ **Hành động đề xuất:** {action}\n"
            f"*(Tập trung xử lý dứt điểm việc này trước khi mở các session lặt vặt!)*"
        )
        try:
            marker_file.parent.mkdir(parents=True, exist_ok=True)
            marker_file.write_text(today_str, encoding="utf-8")
        except Exception:
            pass

        print(msg[:3900])
    except Exception as exc:
        print(f"🦁 **[LINH DƯƠNG SÁNG NAY - CẢNH BÁO]** Lỗi hệ thống: {exc}")

if __name__ == "__main__":
    main()
