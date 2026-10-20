# GatewayRunner Missing `_clear_conversation_scope` RCA (20/10/2026)

## 1. Hiện Tượng (Symptom)
Khi người dùng gửi lệnh `/reset` hoặc `/new` trên Telegram, Gateway văng lỗi:
```text
Sorry, I encountered an error (AttributeError).
'GatewayRunner' object has no attribute '_clear_conversation_scope'
Try again or use /reset to start a fresh session.
```

## 2. Nguyên Nhân Kỹ Thuật (Root Cause)
1. Trong `gateway/slash_commands.py`, các lệnh `/reset`, `/new` (dòng 184) và `/resume` (dòng 4483) gọi:
   ```python
   self._clear_conversation_scope(session_key, reason="session_reset")
   ```
2. Mục đích của lệnh gọi này là funnel dọn dẹp toàn bộ biến per-session ở phạm vi hội thoại (model override, reasoning override, ephemeral pins, state cache) khi xoay phiên.
3. Tuy nhiên, class `GatewayRunner` (trong `gateway/run.py`) và mixin `GatewaySlashCommandsMixin` chưa được khai báo phương thức `_clear_conversation_scope`.
4. Khi người dùng bấm `/reset` để làm mới phiên, lệnh gặp `AttributeError` ngay lập tức và gửi thông báo lỗi về Telegram thay vì xoay phiên thành công.

## 3. Khắc Phục Tạm Thời Cho Người Dùng
- **Dùng `/clear` thay vì `/reset`:** Lệnh `/clear` chỉ dọn dẹp transcript/lịch sử tin nhắn của phiên hiện tại mà không gọi qua `_clear_conversation_scope`, tránh được lỗi crash trên.
- **Bản vá kiến trúc:** Khai báo phương thức `_clear_conversation_scope(self, session_key: str, reason: str = "unspecified")` trên `GatewayRunner` hoặc `GatewaySlashCommandsMixin` để dọn dẹp an toàn các dict state (`_session_model_overrides`, `_session_reasoning_overrides`, `_clear_session_boundary_security_state`) khi upstream cập nhật.
