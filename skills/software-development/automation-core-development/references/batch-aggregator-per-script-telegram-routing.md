# Batch Aggregator Per-Script Telegram Routing Invariant

## Background & Root Cause
Trong `automation_core.batch_aggregator` (`D:/Taadaa/automation-core/src/automation_core/batch_aggregator.py`), khi các batch runner (như `run_parallel.ps1` của `register gmail` hay các batch runner của `Tiktok-video`, `tiktok-add-bao-mat-f2a`) hoàn thành và gọi `batch_aggregator ... --telegram`, nếu phát hiện lỗi lan rộng (systemic failure / high fleet error rate), module sẽ gửi cảnh báo Telegram.

Trước đây, `batch_aggregator` bị hardcode:
```python
token = _load_bot_token()
chat_id = DEFAULT_ALERT_CHAT_ID  # Cố định -5373649734 (Farm Alerts)
```
Hậu quả là các lỗi hệ thống của từng repo cụ thể (ví dụ: Reg Gmail bị lỗi phone verify hàng loạt, hoặc TikTok 2FA lỗi device lock) đều bị dồn nhầm về nhóm chung **Farm Alerts** (`-5373649734`) thay vì rơi vào đúng nhóm chuyên trách của repo (`Gmai reg` `-5139245637`, `Tiktok add 2fa` `-5468653590`).

## Required Contract
Trong `batch_aggregator.py`, tại tất cả các điểm phát sinh thông báo Telegram (Case 1: Multi-paths, Case 2: Sibling auto-merge, Case 3: Standalone single path):
BẮT BUỘC sử dụng hàm phân giải `_resolve_script_chat_id`:
```python
from automation_core.alerts import (
    DEFAULT_ALERT_CHAT_ID,
    _load_bot_token,
    _send_telegram_photo,
    _send_telegram_text,
    _resolve_script_chat_id,
)

token = _load_bot_token()
chat_id = _resolve_script_chat_id(script_name)
```
Chỉ fallback về `DEFAULT_ALERT_CHAT_ID` khi `script_name` không khớp bất kỳ profile quy trình nào trong `_SCRIPT_METADATA`.
