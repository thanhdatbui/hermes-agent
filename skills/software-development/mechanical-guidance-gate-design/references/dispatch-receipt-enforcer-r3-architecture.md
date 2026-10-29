# Receipt Enforcer R3 Architecture & Mechanical Truth Gate

## 1. Problem Statement & Root Cause
- **LLM Completion Bias & Early Text Generation**: In a single assistant turn, explanation text and `tool_calls` are emitted in a single stream. The LLM states *"Em đã dispatch Worker..."* before the dispatch tool call even executes or before the Guard evaluates it.
- **False Claims on Guard Block**: When a Guard blocks `delegate_task` (e.g., `OUT OF REPO WHITELIST` or `CONTRACT VIOLATION`), the LLM falls victim to completion momentum: it proceeds with its pre-generated narrative of "running in background" rather than reporting the block and requesting user intervention.
- **No Moralizing / Anti-Paralysis Requirement**: Trying to solve this by prompt rules alone fails because the text is emitted before observations. Blocking or terminating the session causes whining and paralysis. The solution must be **mechanical post-turn truth labeling** that appends a visible verification banner if claims lack receipts.

## 2. Receipt Enforcer R3 Specifications (Claude CLI Verified)
Triển khai tại `gateway/receipt_enforcer.py` và hook tại `gateway/run.py` trước khi trả response ra chat:

```python
import re
import json
import unicodedata
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

DISPATCH_CLAIM_PATTERN = re.compile(
    r"\b(đã dispatch|da dispatch|đang xử lý ngầm|dang xu ly ngam|đang chạy ngầm|dang chay ngam|"
    r"đã giao worker|da giao worker|đã giao cho worker|da giao cho worker|"
    r"subagent đang chạy|subagent dang chay|đang để worker hoàn tất|dang de worker hoan tat|"
    r"running in background|dispatched worker|dispatched subagent)\b",
    re.IGNORECASE
)

VALID_STATUS_ALLOWLIST = {"dispatched", "started", "running", "queued", "ok", "completed"}

def _clean_text(text: str) -> str:
    if not text:
        return ""
    norm = unicodedata.normalize("NFKC", text)
    return re.sub(r"[\u200B-\u200D\uFEFF]", "", norm)

def _turn_messages(msgs: List[Any]) -> List[Dict[str, Any]]:
    if not isinstance(msgs, list):
        return []
    last_user = -1
    for i, m in enumerate(msgs):
        if isinstance(m, dict) and m.get("role") == "user":
            last_user = i
    if last_user >= 0:
        return [m for m in msgs[last_user + 1:] if isinstance(m, dict)]
    return [m for m in msgs if isinstance(m, dict)]

def enforce_dispatch_receipt(response: str, agent_messages: List[Dict[str, Any]]) -> str:
    try:
        if not response or not isinstance(response, str):
            return response

        cleaned_resp = _clean_text(response)
        if not DISPATCH_CLAIM_PATTERN.search(cleaned_resp):
            return response

        if "CHƯA CÓ WORKER NÀO CHẠY THẬT" in response:
            return response

        current_turn = _turn_messages(agent_messages)
        
        delegate_call_ids = set()
        for m in current_turn:
            if m.get("role") == "assistant":
                for tc in (m.get("tool_calls") or []):
                    if isinstance(tc, dict):
                        fn = tc.get("function") or {}
                        if fn.get("name") == "delegate_task":
                            cid = tc.get("id") or tc.get("call_id")
                            if cid:
                                delegate_call_ids.add(str(cid))

        if not delegate_call_ids:
            banner = (
                f"\n\n⚠️ **[HỆ THỐNG CẢNH BÁO — CHƯA CÓ WORKER NÀO CHẠY THẬT]**\n"
                f"*Lý do:* Không tìm thấy lệnh gọi dispatch Worker nào trong lượt này.\n"
                f"*(Hệ thống cơ học tự động gắn nhãn này do phát hiện lời khẳng định không kèm biên lai hợp lệ).* "
            )
            return response + banner

        valid_receipt = False
        reject_reason = ""

        for m in current_turn:
            if m.get("role") != "tool":
                continue

            tool_call_id = str(m.get("tool_call_id") or "")
            if tool_call_id not in delegate_call_ids:
                continue

            content = str(m.get("content") or "").strip()

            if any(k in content for k in ["OUT OF REPO WHITELIST", "GUARD", "CONTRACT VIOLATION", "BLOCKED"]):
                reject_reason = "Lệnh dispatch bị Guard chặn (Contract/Whitelist Violation)"
                continue

            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    has_id = bool(data.get("delegation_id") or data.get("task_id"))
                    status = str(data.get("status") or "").lower()
                    if has_id and status in VALID_STATUS_ALLOWLIST:
                        valid_receipt = True
            except Exception:
                pass

        if not valid_receipt:
            reason_text = reject_reason if reject_reason else "Lệnh dispatch thất bại hoặc không nhận được task_id hợp lệ"
            banner = (
                f"\n\n⚠️ **[HỆ THỐNG CẢNH BÁO — CHƯA CÓ WORKER NÀO CHẠY THẬT]**\n"
                f"*Lý do:* {reason_text}.\n"
                f"*(Hệ thống cơ học tự động gắn nhãn này do phát hiện lời khẳng định không kèm biên lai hợp lệ).* "
            )
            return response + banner

        return response
    except Exception as e:
        logger.error("[RECEIPT_ENFORCER] Error: %s", e)
        return response
```

## 3. Key Invariants & Review Standards
- **P0.1 Exact Tool Call Matching**: Chỉ kiểm tra tool result có `tool_call_id` khớp với `delegate_task` của assistant trong turn. Tuyệt đối không cho phép tool `terminal` (echo json) hay `read_file` giả mạo receipt.
- **P0.2 Allowlist Status & Required Real ID**: Yêu cầu status nằm trong `dispatched`, `started`, `running`, `queued`, `ok`, `completed` và có ID thực tế (`delegation_id` / `task_id`).
- **P0.3 Guard Block Veto**: Bất kỳ tool result nào chứa chữ ký Guard block sẽ kích hoạt `reject_reason` và ngăn chặn giả mạo receipt.
- **Fail-Open & Non-Blocking**: Toàn bộ logic bọc trong `try/except`. Nếu lỗi kiểm tra, response gốc vẫn được bảo toàn gửi tới người dùng; không gây crash, không làm freeze phiên làm việc.
