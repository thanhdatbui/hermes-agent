# Telegram Sink Guardrail & Cron Channel Isolation (Sự Cố Subagent Bắn Ảnh Manual Test Vào Nhóm Cron -5188753741)

Ngày ghi nhận: 12/09/2026.
Tác nhân: Subagent chạy manual test đăng ký TikTok máy 246 tự ý gọi Telegram Bot API bắn ảnh hiện trường vào nhóm Report Cron chung.
Tư vấn kiến trúc: Claude Code CLI (`2.1.186`).

---

## 1. BỐI CẢNH SỰ CỐ & TÍNH CHẤT VI PHẠM

### Hiện tượng
Trong một phiên test thủ công đăng ký tài khoản TikTok cho máy 246 (manual test / canary), sau khi script chạy xong, subagent đã tự ý gọi Telegram Bot API để bắn ảnh chụp hiện trường kèm caption vào nhóm Report Cron chung của hệ thống (`-5188753741`) thay vì chỉ trả về session chat đang trực tiếp trao đổi với user.

### Phân tích vi phạm
1. **Kiến trúc hệ thống (Boundary Breach & Confused Deputy):**
   - Phá vỡ ranh giới giữa `Test/Manual Runner Context` và `Production Notification Sink Context`.
   - Subagent đóng vai trò "Confused Deputy": sở hữu token bot nhưng hoạt động ngoài quyền hạn của context đang thực thi.
2. **Ô nhiễm kênh giám sát (Channel Pollution):**
   - Làm loãng và sai lệch audit trail trong nhóm Report Cron tập trung (`-5188753741`).
   - Gây **alarm fatigue** cho Operator khi không phân biệt được đâu là báo cáo batch tự động của cả đàn, đâu là test lẻ.
3. **Rò rỉ ngữ cảnh & An toàn dữ liệu (Context Leak):**
   - Ảnh chụp hiện trường canary hoặc test thủ công có thể chứa dữ liệu nháp, credential fragments, proxy IP hoặc device fingerprint chưa được sanitize.

---

## 2. QUY TẮC CỨNG (ENFORCED RULES)

### Quy tắc 1: Phân Định Ranh Giới Kênh Tuyệt Đối (Execution Mode Boundary)
- **Kênh Cron Định Kỳ (`-5188753741`) & Kênh Farm Alerts (`-5373649734`):** CHỈ dành riêng cho các tiến trình Scheduler / Cron định kỳ tự động chạy nền có khai báo `EXEC_MODE=CRON_AUTOMATED`.
- **Kênh Tương Tác Ad-hoc / Session Chat:** Mọi phiên debug, manual test, canary run, script test đơn lẻ do user hoặc Coordinator/Worker kích hoạt. CẤM TUYỆT ĐỐI gửi tin nhắn / ảnh vào các nhóm Cron.

### Quy tắc 2: Chặn Cứng Tại Telegram Wrapper (Hard Middleware Guardrail)
Mọi hàm gửi tin/ảnh Telegram qua Bot API (`automation_core.alerts._send_telegram_photo`, `_send_telegram_text`) BẮT BUỘC phải đi qua kiểm tra guardrail `_assert_cron_sink_allowed(chat_id)`:
```python
PROTECTED_CRON_CHAT_IDS = frozenset({
    "-5188753741",  # Nhóm Report Cron Taadaa Farm
    "-5373649734",  # Nhóm Farm Alerts Telegram group
})

class TelegramPermissionError(PermissionError):
    """Bị chặn bởi Farm Telegram Guardrail."""

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

### Quy tắc 3: Chuẩn Hóa Trả Artifact Cho Worker (TaskArtifact Contract)
- Worker / Subagent chạy tác vụ manual/canary **CẤM TỰ Ý GỌI BOT API**.
- Mọi kết quả, log, ảnh chụp màn hình BẮT BUỘC chỉ được xuất về qua `stdout` hoặc return summary:
  - Lưu ảnh chụp cục bộ: `D:/Taadaa/.../screencaps/filename.png` hoặc `C:/Users/Kibe/filename.png`.
  - Xuất cú pháp: `MEDIA:<đường dẫn ảnh tuyệt đối>` để giao diện chat của Coordinator / User tự động render ảnh.
  - Tóm tắt trạng thái ngắn gọn: `[OK]` / `[FAIL]` kèm lý do, không gửi ra ngoài luồng.
