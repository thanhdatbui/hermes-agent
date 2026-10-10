#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
advisor_consult.py
Module và CLI thực thi truy vấn Advisor Sol độc lập cho hệ thống Hermes Coordinator.
Tự động fallback đa tầng để chống timeout/waterfall, đảm bảo luôn có kết quả phản hồi < 35s.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from typing import Any, Tuple


# Regex nhận diện câu hỏi tư vấn / kiến trúc / phân tích nguyên nhân
ADVICE_PATTERNS = [
    r"tại sao",
    r"vì sao",
    r"thấy sao",
    r"nghĩ sao",
    r"mày nghĩ",
    r"là sao",
    r"hợp lý",
    r"hợp lí",
    r"đúng không",
    r"đúng ko",
    r"đúng k",
    r"hay không",
    r"hay ko",
    r"hay k",
    r"thì sao",
    r"chứ hay",
    r"có nên",
    r"k nên",
    r"không nên",
    r"nên dùng.*(?:hay|hoặc)",
    r"nên chọn.*(?:hay|hoặc)",
    r"nên làm.*(?:hay|hoặc)",
    r"nên.*(?:cách nào|phương án nào|hướng nào)",
    r"ổn không",
    r"ổn ko",
    r"ổn k",
    r"đánh giá",
    r"kiến trúc",
    r"lên plan",
    r"xin plan",
    r"nhờ plan",
    r"tư vấn",
    r"lời khuyên",
    r"review giúp",
    r"review cho",
    r"phân tích",
    r"theo mày",
    r"(nhìn|thấy|đánh giá|xử lý).*thế nào",
    r"có hợp không",
    r"có ổn không",
    r"đc k nhỉ",
    r"đc ko nhỉ",
    r"ko nhỉ",
    r"k nhỉ",
    r"liệu",
    r"hay là do",
    r"nguyên nhân",
    r"căn nguyên",
    r"hướng giải quyết",
    r"nên làm gì",
    r"nên xử lý thế nào",
    r"phải làm sao",
    r"xem có gì lạ",
    r"có bất thường không",
    r"sao lại",
    r"sao thế",
    r"sao bữa nay",
    r"sao dạo này",
    r"sao cứ",
    r"sao không",
    r"sao k",
    r"sao chưa",
    r"sao nhìn",
    r"sao.*(?:v|vậy|thế|ấy|hả)",
    r"sao.*(cứ|lại|bị|được|mất|rớt|lỗi)",
    r"k ổn định",
    r"không ổn định",
    r"chập chờn",
]

EXCLUDE_ADVICE_PHRASES = [
    r"(kiểm tra|check|xem|đọc|báo cáo|gửi)\s+(?:lại\s+)?(?:tiến độ|trạng thái|status|plan|kế hoạch)",
    r"(trạng thái|status|tiến độ).*(thế nào|ra sao|sao rồi|sao r)",
    r"sao rồi",
    r"sao r",
    r"như thế nào rồi",
    r"ra sao rồi",
    r"sao cho",
]

IMPERATIVE_STARTS = [
    r"^\s*chạy",
    r"^\s*sửa",
    r"^\s*fix",
    r"^\s*làm đi",
    r"^\s*làm luôn",
    r"^\s*triển khai",
    r"^\s*restart",
    r"^\s*upload",
    r"^\s*adb",
    r"^\s*git",
    r"^\s*xem",
    r"^\s*kiểm tra",
]
def redact_secrets(text: str) -> str:
    """Loại bỏ token, API key, password và dữ liệu nhạy cảm trước khi gửi ra ngoài."""
    if not text:
        return ""
    # Redact OpenAI / Hermes API keys
    text = re.sub(r"sk-[a-zA-Z0-9_\-]{20,}", "[REDACTED_API_KEY]", text)
    # Redact Bearer tokens
    text = re.sub(r"Bearer\s+[a-zA-Z0-9_\-\.]{15,}", "Bearer [REDACTED_TOKEN]", text)
    # Redact URL basic auth user:pass@
    text = re.sub(r"://[^:\s/]+:[^@\s/]+@", "://[REDACTED_USER_PASS]@", text)
    # Redact JSON key-value pairs (e.g. {"password": "abc"}, {"api_key": "k"}, {"access_token": "xyz"}, {"session_id": "123"})
    text = re.sub(
        r"""(?i)(["']?(?:password|passwd|pass|api_key|token|access_token|session_id|sessionid)["']?\s*:\s*)["'][^"']+["']""",
        r'\1"[REDACTED]"',
        text,
    )
    # Redact unquoted Vietnamese 'mật khẩu là ...'
    text = re.sub(
        r"(?i)\bmật khẩu\s+là\s+[^\s,;]+",
        "mật khẩu là [REDACTED]",
        text,
    )
    # Redact query/field tokens, passwords, sessions (e.g. password=abc, access_token: xyz)
    text = re.sub(
        r"(?i)\b(password|passwd|pass|mật khẩu|token|api_key|access_token|session_id|sessionid)\s*[:=]\s*[^\s,;]+",
        r"\1=[REDACTED]",
        text,
    )
    return text


def classify_advice_intent(message: str) -> bool:
    """
    Xác định tin nhắn có chứa ý định hỏi ý kiến / tư vấn / phân tích nguyên nhân hay không.
    Hỗ trợ chuẩn xác các câu hỗn hợp (mệnh lệnh + câu hỏi) và loại trừ phó từ / hỏi tiến độ / lệnh chạy combo.
    """
    if not message or not message.strip():
        return False

    msg_lower = message.lower().strip()

    # 1. Kiểm tra các câu hỗn hợp có chứa ý định hỏi tư vấn rõ ràng (Compound Intent)
    for p in [r"\bnên làm gì\b", r"\bnên xử lý thế nào\b", r"\bphải làm sao\b", r"\bxem có gì lạ\b", r"\bcó bất thường không\b"]:
        if re.search(p, msg_lower):
            return True

    # 2. Loại trừ false-positive khi "review" hoặc "plan" là đối tượng của động từ mệnh lệnh/thao tác
    # ("chạy review combo", "chạy lại review combo", "lập plan", "lên plan cho phase 2", "tạo plan")
    msg_cleaned = re.sub(r"\b(chạy|chạy lại|run|tạo|lập|lên|thực thi|viết)\s+(?:lại\s+)?(review(\s+combo)?|plan(\s+cho\s+\S+)?)\b", " ", msg_lower)

    # 3. Loại trừ các cụm từ phó từ hoặc hỏi trạng thái tiến độ ("sao rồi", "sao cho")
    # Đảm bảo không đè các từ hỏi tư vấn như "vì sao", "thấy sao"
    # Đồng thời loại trừ false-positive từ các danh từ chứa "liệu": "dữ liệu", "tài liệu" (tránh dính r"\bliệu\b")
    msg_cleaned = re.sub(r"\b(dữ liệu|tài liệu|vật liệu|nguyên liệu)\b", " ", msg_cleaned)
    for exc in EXCLUDE_ADVICE_PHRASES:
        msg_cleaned = re.sub(exc, " ", msg_cleaned)

    # 4. Loại trừ các câu hỏi xin phép / xác nhận mệnh lệnh đơn thuần ("Đăng ký bù, được không?")
    if re.search(r"^\s*(đăng ký|chạy|sửa|upload|restart)\b.*(được không|đc ko|đc k)\??$", msg_lower):
        return False

    # 5. Nếu là câu lệnh mệnh lệnh thuần túy ở đầu câu mà không có dấu hỏi hoặc ý định hỏi
    for imp in IMPERATIVE_STARTS:
        if re.search(imp, msg_cleaned) and "?" not in msg_cleaned and not any(re.search(p, msg_cleaned) for p in ADVICE_PATTERNS):
            return False

    # 6. Kiểm tra toàn bộ danh mục Advice Patterns trên câu đã chuẩn hóa
    for p in ADVICE_PATTERNS:
        if re.search(p, msg_cleaned):
            return True

    # 7. Kiểm tra cấu trúc câu hỏi đánh giá / nguyên nhân với từ để hỏi và dấu '?'
    if "?" in msg_cleaned:
        if re.search(r"\b(tại sao|vì sao|lý do gì|nguyên nhân gì|thế nào|ra sao|có nên|thấy sao|hợp lý|hợp lí|đúng không|đúng ko|đúng k|ổn không|ổn ko|ổn k|được không|đc ko|đc k|hay không|hay ko|hay k|thì sao)\b", msg_cleaned):
            return True
        if re.search(r"\bsao\b", msg_cleaned) and not re.search(r"\bsao (rồi|r|cho)\b", message.lower()):
            return True

    return False


def _call_stream_chat(url: str, headers: dict[str, str], payload: dict[str, Any], timeout_sec: float) -> Tuple[bool, str]:
    """Gọi endpoint chat completion có hỗ trợ SSE streaming với wall-clock deadline nghiêm ngặt."""
    t_start = time.time()
    payload["stream"] = True
    payload["tools"] = []
    payload["tool_choice"] = "none"

    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data_bytes, headers=headers)
    text_chunks = []
    completed_cleanly = False

    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            for line in resp:
                if time.time() - t_start > timeout_sec:
                    return False, f"Wall-clock deadline exceeded ({timeout_sec}s)"
                line_str = line.decode("utf-8", errors="replace").strip()
                if line_str == "data: [DONE]":
                    completed_cleanly = True
                    break
                if line_str.startswith("data: "):
                    try:
                        chunk = json.loads(line_str[6:])
                        delta = chunk["choices"][0].get("delta", {}).get("content", "")
                        if delta:
                            text_chunks.append(delta)
                    except Exception:
                        pass
        full_text = "".join(text_chunks).strip()

        # Kiểm tra pseudo-200 limit hoặc lỗi upstream trên toàn bộ text nhận được
        if full_text.startswith("[Error:") or "You've hit your limit" in full_text:
            return False, "Pseudo-200 usage limit rejected"

        # BẮT BUỘC có marker [DONE] để đảm bảo stream không bị đứt gãy giữa chừng
        if not completed_cleanly:
            return False, "Premature stream termination without [DONE] marker"

        if full_text:
            # Giới hạn độ dài an toàn tối đa 2500 ký tự
            return True, full_text[:2500]
        return False, "Empty stream response"
    except Exception as exc:
        return False, str(exc)


def consult_advisor(prompt: str, context: str = "", timeout_sec: float = 45.0) -> dict[str, Any]:
    """Truy vấn trực tiếp Advisor Sol (:20129 review / gpt-web-sol) với deadline tổng <= 45s."""
    cleaned_prompt = redact_secrets(prompt)
    cleaned_context = redact_secrets(context)

    messages = []
    system_text = (
        "Bạn là Advisor Sol, cố vấn chiến lược và kiến trúc hệ thống Taadaa Farm. "
        "Hãy phân tích sắc bén, khách quan, đưa ra giải pháp rõ ràng, súc tích."
    )
    messages.append({"role": "system", "content": system_text})
    if cleaned_context:
        messages.append({"role": "user", "content": f"[BỐI CẢNH HIỆN TRƯỜNG]
{cleaned_context}

[CÂU HỎI]
{cleaned_prompt}"})
    else:
        messages.append({"role": "user", "content": cleaned_prompt})

    omni_url = "http://127.0.0.1:20129/v1/chat/completions"
    omni_headers = {"Content-Type": "application/json", "Authorization": "Bearer dummy"}

    t_start = time.monotonic()
    max_total_sec = 45.0

    for target_model in ["gpt-web-sol", "review"]:
        elapsed = time.monotonic() - t_start
        remaining = max_total_sec - elapsed
        if remaining <= 3.0:
            break
        timeout_this_call = min(timeout_sec, remaining)
        payload = {"model": target_model, "messages": messages}
        ok, text_resp = _call_stream_chat(omni_url, omni_headers, payload, timeout_sec=timeout_this_call)
        if ok and len(text_resp) > 20:
            return {
                "status": "success",
                "model": "Sol / review",
                "tier": 1,
                "advice": text_resp,
                "formatted": f"--- Advisor (Sol / review) ---
{text_resp}",
            }

    err_msg = "Advisor: unavailable (Sol / review timeout hoặc pool limit; chỉ hiển thị câu trả lời Coordinator)"
    return {
        "status": "unavailable",
        "model": "none",
        "tier": 0,
        "advice": "",
        "formatted": f"--- Advisor ---
{err_msg}",
    }
if __name__ == "__main__":
    main()
