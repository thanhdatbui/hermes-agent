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
    r"\btại sao\b",
    r"\bvì sao\b",
    r"\bthấy sao\b",
    r"\blà sao\b",
    r"\bcó nên\b",
    r"\bđánh giá\b",
    r"\bkiến trúc\b",
    r"\bplan\b",
    r"\btư vấn\b",
    r"\blời khuyên\b",
    r"\breview\b",
    r"\bphân tích\b",
    r"\btheo mày\b",
    r"\bnhìn\b.*\bthế nào\b",
    r"\bthế nào\b",
    r"\bcó hợp không\b",
    r"\bcó ổn không\b",
    r"\bđc k nhỉ\b",
    r"\bđc ko nhỉ\b",
    r"\bko nhỉ\b",
    r"\bk nhỉ\b",
    r"\bliệu\b",
    r"\bhay là do\b",
    r"\bnguyên nhân\b",
    r"\bcăn nguyên\b",
    r"\bhướng giải quyết\b",
    r"\bnên làm gì\b",
    r"\bnên xử lý thế nào\b",
    r"\bphải làm sao\b",
    r"\bxem có gì lạ\b",
    r"\bcó bất thường không\b",
    r"\bsao lại\b",
    r"\bsao thế\b",
    r"\bsao bữa nay\b",
    r"\bsao dạo này\b",
    r"\bsao cứ\b",
    r"\bsao không\b",
    r"\bsao k\b",
    r"\bsao chưa\b",
    r"\bsao nhìn\b",
    r"\bsao\b.*(?:\bv\b|\bvậy\b|\bthế\b|\bấy\b|\bhả\b)",
    r"\bsao\b.*\b(cứ|lại|bị|được|mất|rớt|lỗi)\b",
    r"\bk ổn định\b",
    r"\bkhông ổn định\b",
    r"\bchập chờn\b",
]

# Các cụm từ trạng thái / phó từ cần LOẠI TRỪ (tránh False-Positive)
EXCLUDE_ADVICE_PHRASES = [
    r"\bsao rồi\b",
    r"\bsao r\b",
    r"\bnhư thế nào rồi\b",
    r"\bra sao rồi\b",
    r"\bsao cho\b",  # ví dụ "sửa cái này sao cho nhanh"
]

IMPERATIVE_STARTS = [
    r"^\s*chạy\b",
    r"^\s*sửa\b",
    r"^\s*fix\b",
    r"^\s*làm đi\b",
    r"^\s*làm luôn\b",
    r"^\s*triển khai\b",
    r"^\s*restart\b",
    r"^\s*upload\b",
    r"^\s*adb\b",
    r"^\s*git\b",
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
        if re.search(r"\b(tại sao|vì sao|lý do gì|nguyên nhân gì|thế nào|ra sao|có nên|thấy sao)\b", msg_cleaned):
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


def consult_advisor(prompt: str, context: str = "") -> dict[str, Any]:
    """
    Truy vấn Advisor qua fallback chain 3 tầng có bảo vệ thời gian:
    Tổng ngân sách thời gian: tối đa ~35s
    Tầng 1: OmniRoute :20129 review / gpt-5.6-sol (Sol chính, 18s)
    Tầng 2: OmniRoute :20129 antigravity/gemini-3.7-flash-high (Sol fast fallback, 10s)
    Tầng 3: 9Router :20128 ag/gemini-2.5-flash (Cổng phụ độc lập, 7s)
    """
    clean_prompt = redact_secrets(prompt)
    clean_context = redact_secrets(context)

    full_prompt = clean_prompt
    if clean_context:
        full_prompt = f"Bối cảnh hiện trường:\n{clean_context}\n\nNhiệm vụ tư vấn / đánh giá:\n{clean_prompt}"

    system_instruction = (
        "Bạn là Advisor Sol độc lập của Taadaa Phone Farm. "
        "Hãy đưa ra đánh giá kiến trúc, phân tích nguyên nhân và phương án xử lý thẳng thắn, "
        "súc tích, có tính hành động cao, tuyệt đối không giáo điều hoặc nói chung chung."
    )

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": full_prompt},
    ]

    # --- Tầng 1: OmniRoute Sol Primary (Fail-fast 5s) ---
    omni_url = "http://127.0.0.1:20129/v1/chat/completions"
    omni_headers = {"Content-Type": "application/json", "Authorization": "Bearer dummy"}
    payload_t1 = {"model": "review", "messages": messages}
    ok, text = _call_stream_chat(omni_url, omni_headers, payload_t1, timeout_sec=5.0)
    if ok and len(text) > 20:
        return {
            "status": "success",
            "model": "Sol Web High (review)",
            "tier": 1,
            "advice": text,
            "formatted": f"--- Advisor (Sol / review) ---\n{text}",
        }

    # --- Tầng 2: OmniRoute Fast Fallback (Gemini High, 18s) ---
    payload_t2 = {"model": "antigravity/gemini-3.7-flash-high", "messages": messages}
    ok, text = _call_stream_chat(omni_url, omni_headers, payload_t2, timeout_sec=18.0)
    if ok and len(text) > 20:
        return {
            "status": "success",
            "model": "Sol High (gemini-3.7-flash-high fallback)",
            "tier": 2,
            "advice": text,
            "formatted": f"--- Advisor (gemini-3.7-flash-high fallback) ---\n{text}",
        }

    # --- Tầng 3: 9Router Port 20128 Backup (7s) ---
    nine_key = os.environ.get("NINEROUTER_API_KEY", "")
    if nine_key:
        nine_url = "http://127.0.0.1:20128/v1/chat/completions"
        nine_headers = {"Content-Type": "application/json", "Authorization": f"Bearer {nine_key}"}
        payload_t3 = {"model": "ag/gemini-2.5-flash", "messages": messages}
        ok, text = _call_stream_chat(nine_url, nine_headers, payload_t3, timeout_sec=7.0)
        if ok and len(text) > 20:
            return {
                "status": "success",
                "model": "Sol Backup (9Router :20128)",
                "tier": 3,
                "advice": text,
                "formatted": f"--- Advisor (9Router :20128 backup) ---\n{text}",
            }

    # --- Toàn bộ Tầng Thất Bại (Fail-Safe) ---
    err_msg = "Advisor: unavailable (upstream timeout / pool limits; primary answer shown)"
    return {
        "status": "unavailable",
        "model": "none",
        "tier": 0,
        "advice": "",
        "formatted": f"--- Advisor ---\n{err_msg}",
    }


def ensure_dual_answer(message: str, response: str, context: str = "") -> str:
    """
    Cơ chế bảo vệ cơ học (Mechanical Enforcement Gate):
    Nếu user message là Advice Intent mà phản hồi chưa có khối Advisor,
    hàm sẽ tự động kích hoạt Advisor và gắn khối kết quả vào cuối phản hồi.
    """
    if not classify_advice_intent(message):
        return response

    if "--- Advisor (" in response or "--- Advisor ---" in response:
        return response

    # Tự động gọi Advisor bổ sung
    adv_res = consult_advisor(message, context)
    return f"{response.rstrip()}\n\n{adv_res['formatted']}"


def main():
    parser = argparse.ArgumentParser(description="Query Hermes Advisor Sol")
    parser.add_argument("--query", "-q", required=True, help="Câu hỏi hoặc yêu cầu tư vấn")
    parser.add_argument("--context", "-c", default="", help="Bối cảnh hiện trường")
    parser.add_argument("--classify-only", action="store_true", help="Chỉ kiểm tra intent")
    parser.add_argument("--enforce", action="store_true", help="Chạy qua mechanical dual-answer gate")
    parser.add_argument("--response-text", default="", help="Phản hồi chính để kiểm tra enforce")
    args = parser.parse_args()

    if args.classify_only:
        is_advice = classify_advice_intent(args.query)
        print("ADVICE_INTENT" if is_advice else "IMPERATIVE_INTENT")
        sys.exit(0 if is_advice else 1)

    if args.enforce:
        output = ensure_dual_answer(args.query, args.response_text, args.context)
        print(output)
        sys.exit(0)

    result = consult_advisor(args.query, args.context)
    print(result["formatted"])


if __name__ == "__main__":
    main()
