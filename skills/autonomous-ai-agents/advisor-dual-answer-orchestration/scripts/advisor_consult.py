#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
advisor_consult.py
Module và CLI thực thi truy vấn Advisor Sol độc lập cho hệ thống Hermes Coordinator.
Tự động fallback đa tầng để chống timeout/waterfall, đảm bảo luôn có kết quả phản hồi < 35s.
"""

from __future__ import annotations

import concurrent.futures
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from typing import Any, Tuple


# Chỉ kích hoạt khi user gọi tên trực tiếp Advisor/Sol (100% strictly on-demand)
SUMMON_PATTERNS = [
    r"\b(?:gọi|hỏi|nhờ|kêu)\s+(?:sol|advisor)\b",
    r"\b(?:sol|advisor)\s+(?:thấy\s+sao|nghĩ\s+sao|review|lên\s+plan|cho\s+ý\s+kiến)\b",
    r"\bnhờ\s+(?:sol|advisor)\s+review\b",
    r"\bxin\s+ý\s+kiến\s+(?:sol|advisor)\b",
]

EXCLUDE_PATTERNS = [
    r"\b(?:tắt|dừng|stop|disable|hủy|bỏ|ngắt|cấm|đừng|không|k|chớ)\b.*?\b(?:advisor|sol)\b",
    r"\b(?:spam|lải\s+nhải|nói\s+nhiều)\b.*?\b(?:advisor|sol)\b",
    r"\b(?:advisor|sol)\b.*?\b(?:spam|lải\s+nhải|nhảm|lồn|cặc)\b",
    r"\b(?:advisor\s+sol|advisor|sol)\b.*?\b(?:t|tao|tôi|mình)\s+sửa\b",
    r"\b(?:tại\s+sao|vì\s+sao|sao|sao\s+k|sao\s+không)\b.*?\b(?:gọi|kêu|hỏi|dùng|có)\s+(?:sol|advisor)\b",
    r"\b(?:đéo|không|chẳng|chưa|k)\b.*?\b(?:thấy|muốn)\b.*?\b(?:gọi|kêu|hỏi)\s+(?:advisor|sol)\b",
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
    """Chỉ trả True khi tin nhắn gọi tên trực tiếp Advisor/Sol; câu hỏi chung và từ khóa heuristic trả False."""
    if not message or not isinstance(message, str) or not message.strip():
        return False
    msg_lower = " ".join(message.split()).lower()
    if any(re.search(p, msg_lower) for p in EXCLUDE_PATTERNS):
        return False
    return any(re.search(p, msg_lower) for p in SUMMON_PATTERNS)


def _call_stream_chat(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    first_token_timeout: float = 80.0,
    idle_token_timeout: float = 20.0,
    max_total_timeout: float = 140.0,
    timeout_sec: float | None = None,
) -> Tuple[bool, str]:
    """Gọi endpoint chat completion có hỗ trợ SSE streaming với Idle Streaming Timeout."""
    if timeout_sec is not None:
        first_token_timeout = timeout_sec
        max_total_timeout = timeout_sec

    t_start = time.time()
    t_last_activity = t_start
    has_started_streaming = False

    payload["stream"] = True
    payload["tools"] = []
    payload["tool_choice"] = "none"

    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data_bytes, headers=headers)
    text_chunks = []
    completed_cleanly = False

    try:
        # Socket timeout ban đầu chờ token đầu tiên
        with urllib.request.urlopen(req, timeout=first_token_timeout) as resp:
            for line in resp:
                now = time.time()
                if not has_started_streaming:
                    if now - t_start > first_token_timeout:
                        return False, f"First token deadline exceeded ({first_token_timeout}s)"
                else:
                    if now - t_last_activity > idle_token_timeout:
                        return False, f"Stream idle timeout exceeded ({idle_token_timeout}s)"

                if now - t_start > max_total_timeout:
                    return False, f"Total stream deadline exceeded ({max_total_timeout}s)"

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
                            has_started_streaming = True
                            t_last_activity = now
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


def _consult_inner(prompt: str, context: str = "") -> dict[str, Any]:
    cleaned_prompt = redact_secrets(prompt)
    cleaned_context = redact_secrets(context)

    messages = []
    system_text = (
        "Bạn là Advisor Sol, cố vấn chiến lược và kiến trúc hệ thống Taadaa Farm. "
        "Hãy phân tích sắc bén, khách quan, đưa ra giải pháp rõ ràng, súc tích."
    )
    messages.append({"role": "system", "content": system_text})
    if cleaned_context:
        user_content = f"[BỐI CẢNH HIỆN TRƯỜNG]\n{cleaned_context}\n\n[CÂU HỎI]\n{cleaned_prompt}"
        messages.append({"role": "user", "content": user_content})
    else:
        messages.append({"role": "user", "content": cleaned_prompt})

    omni_url = "http://127.0.0.1:20129/v1/chat/completions"
    omni_headers = {"Content-Type": "application/json", "Authorization": "Bearer dummy"}

    for target_model in ["gpt-web-sol", "review"]:
        payload = {"model": target_model, "messages": messages}
        ok, text_resp = _call_stream_chat(
            omni_url,
            omni_headers,
            payload,
            first_token_timeout=80.0,
            idle_token_timeout=20.0,
            max_total_timeout=140.0,
        )
        if ok and len(text_resp) > 20:
            return {
                "status": "success",
                "model": "Sol / review",
                "tier": 1,
                "advice": text_resp,
                "formatted": f"--- Advisor (Sol / review) ---\n{text_resp}",
            }

    err_msg = "Advisor: unavailable (Sol / review timeout hoặc pool limit; chỉ hiển thị câu trả lời Coordinator)"
    return {
        "status": "unavailable",
        "model": "none",
        "tier": 0,
        "advice": "",
        "formatted": f"--- Advisor ---\n{err_msg}",
    }


def consult_advisor(prompt: str, context: str = "", timeout_sec: float = 150.0) -> dict[str, Any]:
    """Truy vấn trực tiếp Advisor Sol (:20129 review) với Idle Streaming Timeout (wait=False)."""
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_consult_inner, prompt, context)
    try:
        return future.result(timeout=timeout_sec)
    except concurrent.futures.TimeoutError:
        executor.shutdown(wait=False, cancel_futures=True)
        err_msg = f"Advisor: unavailable (Sol / review wall-clock deadline exceeded >{timeout_sec}s; chỉ hiển thị câu trả lời Coordinator)"
        return {
            "status": "unavailable",
            "model": "none",
            "tier": 0,
            "advice": "",
            "formatted": f"--- Advisor ---\n{err_msg}",
        }
    except Exception as exc:
        executor.shutdown(wait=False, cancel_futures=True)
        err_msg = f"Advisor: unavailable ({exc}; chỉ hiển thị câu trả lời Coordinator)"
        return {
            "status": "unavailable",
            "model": "none",
            "tier": 0,
            "advice": "",
            "formatted": f"--- Advisor ---\n{err_msg}",
        }
    finally:
        try:
            executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass


def ensure_dual_answer(message: str, response: str, context: str = "") -> str:
    """
    Cơ chế bảo vệ cơ học (Mechanical Enforcement Gate):
    Nếu user message là Advice Intent mà phản hồi chưa có khối Advisor hợp lệ,
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
    parser = argparse.ArgumentParser(description="Query Hermes Advisor Sol", allow_abbrev=False)
    parser.add_argument("--query", "-q", required=True, help="Câu hỏi hoặc yêu cầu tư vấn")
    parser.add_argument("--context", "-c", default="", help="Bối cảnh hiện trường")
    parser.add_argument("--classify-only", action="store_true", help="Chỉ kiểm tra intent")
    parser.add_argument("--enforce", action="store_true", help="Chạy qua mechanical dual-answer gate")
    parser.add_argument("--response-text", default="", help="Phản hồi chính để kiểm tra enforce")
    args = parser.parse_args()

    if args.classify_only:
        is_advice = classify_advice_intent(args.query)
        print("ADVICE_INTENT" if is_advice else "IMPERATIVE_INTENT")
        sys.stdout.flush()
        os._exit(0 if is_advice else 1)

    if args.enforce:
        output = ensure_dual_answer(args.query, args.response_text, args.context)
        print(output)
        sys.stdout.flush()
        os._exit(0)

    result = consult_advisor(args.query, args.context)
    print(result["formatted"])
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
