# Telegram Channel Isolation & Cron Sink Guardrail (Bảo Vệ Kênh Báo Cáo Farm)

Ngày ban hành: 12/09/2026.
Bối cảnh: Sau sự cố subagent worker tự ý gọi Telegram Bot API gửi ảnh test/canary thủ công máy 246 vào nhóm Report Cron Taadaa Farm (`-5188753741`), gây loãng kênh giám sát định kỳ.

---

## 1. PHÂN ĐỊNH RANH GIỚI KÊNH TUYỆT ĐỐI

- **Nhóm Cron Định Kỳ (`-5188753741`) & Nhóm Farm Alerts (`-5373649734`)**:
  - CHỈ dành riêng cho Scheduler/Batch runner tự động (`EXEC_MODE=CRON_AUTOMATED`).
  - CẤM TUYỆT ĐỐI mọi luồng test thủ công, debug, canary, ad-hoc trigger hoặc subagent worker bắn tin nhắn / hình ảnh vào các nhóm Cron này.

---

## 2. CƠ CHẾ CHẶN CỨNG (MIDDLEWARE / GUARDRAIL TẠI AUTOMATION-CORE)

Triển khai tại `automation_core.alerts` (`D:/Taadaa/automation-core/src/automation_core/alerts.py`):

```python
PROTECTED_CRON_CHAT_IDS = frozenset({
    "-5188753741",  # Nhóm Report Cron Taadaa Farm
    "-5373649734",  # Nhóm Farm Alerts Telegram group
})

class TelegramPermissionError(PermissionError):
    """Bị chặn bởi Farm Telegram Guardrail khi luồng thủ công/canary bắn vào nhóm Cron."""

def _assert_cron_sink_allowed(chat_id: str | int) -> None:
    s_chat_id = str(chat_id).strip()
    if s_chat_id in PROTECTED_CRON_CHAT_IDS:
        exec_mode = os.environ.get("EXEC_MODE", "").strip().upper()
        if exec_mode != "CRON_AUTOMATED" and os.environ.get("ALLOW_CRON_SINK_OVERRIDE") != "1":
            raise TelegramPermissionError(
                f"[GUARDRAIL BLOCKED] chat_id={s_chat_id} thuộc nhóm Cron/Farm Alerts bảo vệ nghiêm ngặt. "
                f"Execution mode hiện tại: '{exec_mode or 'UNDEFINED'}'. "
                f"CẤM TUYỆT ĐỐI tác vụ thủ công/canary/test/debug gửi tin/ảnh vào nhóm Cron! "
                f"Artifact chỉ được trả về stdout / session chat."
            )
```

- Được gọi tự động ở đầu cả `_send_telegram_photo()` và `_send_telegram_text()`.
- Bất kỳ lời gọi nào tới các chat ID bảo vệ mà thiếu `EXEC_MODE=CRON_AUTOMATED` (hoặc `ALLOW_CRON_SINK_OVERRIDE=1`) sẽ lập tức bị chặn đứng bằng `TelegramPermissionError`.
- CẤM bypass bằng cách đổi tên hàm hoặc tự ý gọi `curl` / `urllib` trực tiếp ra Telegram API.

---

## 3. QUY CHUẨN TRẢ EVIDENCE / ARTIFACT CHO WORKER & SUBAGENT

1. **Không Gọi Bot API**:
   - Subagent / Worker thực thi các tác vụ test, canary, sửa code, debug KHÔNG ĐƯỢC PHÉP gọi bất kỳ hàm gửi Telegram nào ra kênh ngoài.
2. **Trả Artifact Chuẩn**:
   - Mọi ảnh chụp màn hình máy farm, dump XML, log kết quả phải được lưu cục bộ (ví dụ: `C:/Users/Kibe/AppData/Local/hermes/session-artifacts/...` hoặc đường dẫn repo quy định).
   - Trả về qua output chat / return value với cú pháp `MEDIA:<đường_dẫn_ảnh>` để Coordinator / User tự xem xét trực tiếp trong session.
3. **Unit Test Xác Thực**:
   - Bộ test nằm tại `automation-core/tests/test_alerts.py`:
     + `test_telegram_guardrail_blocks_cron_chat_in_manual_or_default_mode`
     + `test_telegram_guardrail_allows_cron_chat_in_cron_automated_mode`
     + `test_telegram_guardrail_allows_non_protected_chat`
     + `test_send_telegram_photo_blocked_by_guardrail`
