# RCA: AttributeError GatewayRunner._clear_conversation_scope on /reset or /new

## 1. Triệu Chứng Sự Cố
Người dùng gửi lệnh `/reset` hoặc `/new` trên Telegram, Gateway văng lỗi ngay lập tức:
```text
Sorry, I encountered an error (AttributeError).
'GatewayRunner' object has no attribute '_clear_conversation_scope'
Try again or use /reset to start a fresh session.
```
Nghịch lý: Khi lệnh `/reset` bị crash, handler ngoại lệ tự động in ra tin nhắn mẫu khuyên người dùng gõ `/reset`, khiến lệnh reset trở thành vòng lặp crash.

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **Lệch pha đồng bộ mã nguồn (Partial Sync Drift) giữa các module**:
   - Trong quá trình phát triển refactor god-file `gateway/run.py` sang `slash_commands.py` và `session_state.py`, code tại `gateway/slash_commands.py` (hàm `_handle_reset_command` và `_handle_resume_command`) gọi:
     ```python
     self._clear_conversation_scope(session_key, reason="session_reset")
     ```
   - Tuy nhiên, trong file `gateway/run.py` (hoặc mixin kế thừa), phương thức `_clear_conversation_scope` chưa từng được định nghĩa hoặc bị xóa mất trong đợt refactor, trong khi `SessionState.conversation.clear()` đã được thiết kế tại `gateway/session_state.py`.
2. **Nguyên nhân tại runtime**:
   - Trước khi Gateway restart, RAM có thể vẫn giữ code cũ hoặc chưa từng gọi `/reset` ở phiên hiện tại.
   - Khi file `gateway/run.py` được sync/chỉnh sửa (ví dụ đợt vá gửi link media Telegram ngày 13/10) nhưng không đi kèm bản cập nhật đồng bộ cho `_clear_conversation_scope`, một khi tiến trình nạp lại module từ disk, phương thức bị thiếu lộ diện gây crash.

## 3. Bản Vá Khắc Phục (Patch Contract)
Trên class `GatewayRunner` (trong `gateway/run.py`), bổ sung định nghĩa hàm `_clear_conversation_scope`:

```python
    def _clear_conversation_scope(self, session_key: str, reason: str = "") -> None:
        """Clear conversation-scoped state and session boundary security state."""
        if not session_key:
            return
        # 1. Clear conversation state in session_state container if available
        if hasattr(self, "_session_state"):
            try:
                self._session_state(session_key).conversation.clear()
            except Exception as e:
                logger.debug("Failed to clear ConversationState for %s: %s", session_key, e)

        # 2. Clear legacy in-memory overrides
        if hasattr(self, "_session_model_overrides") and isinstance(self._session_model_overrides, dict):
            self._session_model_overrides.pop(session_key, None)
        if hasattr(self, "_session_reasoning_overrides") and isinstance(self._session_reasoning_overrides, dict):
            self._session_reasoning_overrides.pop(session_key, None)

        # 3. Clear session security state (approvals, prompts, etc.)
        self._clear_session_boundary_security_state(session_key)
```

## 4. Cách Vận Hành Tạm Thời Cho User Khi Gặp Sự Cố
- Nếu `/reset` hoặc `/new` bị crash do lỗi code Gateway:
  1. **Tạo Topic mới (Telegram Topics)**: Telegram Group Topics tự map thành session ID mới tinh độc lập mà không cần gọi qua `/reset`.
  2. Dùng `/stop` để hủy tiến trình chạy dở dang.
  3. Không cố gõ lại `/reset` liên tục vì lệnh này chính là nguồn phát sinh lỗi.
