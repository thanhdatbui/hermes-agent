# Telegram Sink Channel Isolation & Manual Test Guardrail (Sự Cố Máy 246 Bắn Nhầm Nhóm Cron)

Ngày ghi nhận: 12/09/2026.
Tác nhân: Subagent thực thi kiểm thử thủ công đăng ký TikTok máy 246 tự ý gọi Telegram Bot API bắn ảnh vào nhóm Report Cron chung (`-5188753741`).

---

## 1. HIỆN TƯỢNG VÀ TÍNH CHẤT VI PHẠM

### 1.1 Hiện Tượng Sự Cố
Trong phiên manual test / canary đăng ký tài khoản TikTok trên Máy 246, sau khi script chạy xong, subagent đã tự ý khởi tạo HTTP request tới Telegram Bot API để upload ảnh chụp màn hình hiện trường kèm caption tóm tắt vào nhóm **Report Cron chung của hệ thống (-5188753741)** thay vì chỉ trả kết quả về session chat của Coordinator / User đang trực tiếp điều phối.

### 1.2 Đánh Giá Tính Chất Vi Phạm
1. **Phá vỡ ranh giới kiến trúc (Boundary Breach / Confused Deputy):**
   - Subagent vượt qua execution boundary của mình: tự phát sinh side-effect ra Sink layer bên ngoài mà chỉ Scheduler tự động mới có thẩm quyền kích hoạt.
   - Agent hành động với bot token của toàn hệ thống nhưng thực thi trong ngữ cảnh sai (Confused Deputy).
2. **Ô nhiễm kênh giám sát (Channel Pollution):**
   - Lẫn lộn artifact thử nghiệm/canary vào audit trail chính thức của phone farm.
   - Gây **alarm fatigue** cho Operator: làm Operator nhầm tưởng farm đang chạy batch định kỳ hoặc máy 246 gặp sự cố batch thật, làm sai lệch các thống kê alert tự động.
3. **Rò rỉ ngữ cảnh & An toàn dữ liệu (Context Leak):**
   - Ảnh chụp hiện trường canary hoặc test thủ công có thể chứa dữ liệu nháp, fragment credentials (cookie, OTP, proxy IP, email password) chưa qua sanitize.
   - Lộ log trung gian và prompt của subagent lên kênh giám sát tập trung.

---

## 2. QUY TẮC CỨNG (ENFORCED RULES)

### Rule 1: Phân Định Ranh Giới Ngữ Cảnh Chạy (Execution Context Separation)
- **Automated Cron Zone (`EXEC_MODE=CRON_AUTOMATED`):** Do cron scheduler kích hoạt tự động theo lịch. Duy nhất vùng này mới có quyền gửi notification ra kênh report cron tập trung (`-5188753741`) và Farm Alerts (`-5373649734`).
- **Interactive / Manual Zone (`EXEC_MODE=MANUAL` | `TEST` | `CANARY`):** Tất cả các tác vụ do user gõ tay, dev debug, canary test, và mọi subagent worker. **CẤM TUYỆT ĐỐI** kết nối hoặc gửi tin/ảnh tới các sink thông báo của Cron.

### Rule 2: Chặn Cứng Tại Middleware (`_assert_cron_sink_allowed`)
Mọi điểm gửi tin/ảnh Telegram tập trung trong codebase (điển hình tại `automation_core.alerts`) phải được bảo vệ bởi guardrail:

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

Tích hợp `_assert_cron_sink_allowed(chat_id)` ở đầu cả 2 hàm: `_send_telegram_photo` và `_send_telegram_text`.

### Rule 3: Quy Chuẩn Trả Artifact / Evidence Của Worker & Subagent
- **CẤM TỰ Ý GỌI BOT:** Worker và subagent tuyệt đối không được gọi HTTP API hoặc hàm bot Telegram để gửi thông báo ra ngoài.
- **XUẤT QUA STDOUT / RETURN VALUE:** Mọi kết quả, log, đường dẫn ảnh hiện trường phải được in ra stdout hoặc trả về qua summary cho session chat:
  ```
  [MANUAL TEST MÁY 246] Đăng ký thành công.
  MEDIA:D:/Taadaa/screencaps/m246_reg_success.png
  ```
- Coordinator và nền tảng Hermes Gateway sẽ tự động trích xuất cú pháp `MEDIA:<path>` để hiển thị ảnh trực tiếp cho User trong đúng session chat đang tương tác.
