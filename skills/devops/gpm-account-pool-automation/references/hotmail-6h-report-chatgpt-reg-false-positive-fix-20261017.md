# Hotmail 6H Lifecycle Report ChatGPT Registration False Positive Fix (2026-10-17)

## 1. Bản chất Lỗi Báo Cáo Ảo (+304 tài khoản)
Trong script báo cáo định kỳ 6h `cron_hotmail_gpm_lifecycle_6h_report.py`, chỉ số `chatgpt_ok` bị tăng khống từ **86** lên **392** tài khoản trên Farm Kibe:
- **Nguyên nhân**: Script dùng biểu thức:
  ```python
  has_chatgpt = _has_valid_timestamp(raw, "chatgpt_registered_at", key, _flag) or bool(raw.get("chatgpt_password"))
  ```
- File Excel gốc `taikhoan_dat_v2_updated .xlsx` có cột `PASS CHATGPT` đã được điền sẵn mật khẩu dự kiến cho 392 tài khoản Kibe ngay từ lúc import vào state JSON, dù tài khoản mới chỉ ở bước `HOTMAIL_LOGIN` chưa hề đăng ký ChatGPT.

## 2. Giải pháp Chuẩn Hóa
1. **Loại bỏ fallback `bool(raw.get("chatgpt_password"))`**:
   - Chỉ công nhận tài khoản đã đăng ký ChatGPT khi có timestamp thực tế hợp lệ `chatgpt_registered_at`, hoặc đã hoàn tất chu kỳ bảo mật `DONE`.
2. **Helper cô lập logic `_is_chatgpt_registered(rec)`**:
   ```python
   def _is_chatgpt_registered(rec: dict[str, Any]) -> bool:
       return rec.get("stage") not in REGISTRATION_VOID_STAGES and (
           bool(rec.get("has_chatgpt")) or rec.get("bucket") == STAGE_DONE
       )
   ```
3. **Telemetry phát hiện lệch chuẩn `done_without_chatgpt`**:
   - Phát cảnh báo telemetry `DONE_WITHOUT_CHATGPT_REG` khi tài khoản ở `bucket == STAGE_DONE` nhưng không có timestamp `chatgpt_registered_at` để truy nguyên dữ liệu.
