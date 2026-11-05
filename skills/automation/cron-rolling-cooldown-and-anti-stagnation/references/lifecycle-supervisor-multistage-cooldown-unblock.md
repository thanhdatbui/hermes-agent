# Multi-Stage Cooldown Unblock & Anti-Stagnation in Account Supervisors

## 1. Bối Cảnh & Điểm Nghẽn Hiện Trường
Trong các supervisor quản lý vòng đời tài khoản qua nhiều giai đoạn (Multi-stage Pipeline: ví dụ `HOTMAIL_LOGIN` ➔ `CHATGPT_REG` ➔ `CODEX_OAUTH` ➔ `WAIT_7D` ➔ `CHANGE_INFO` ➔ `DONE` trong `batch_gpm_5profiles_supervisor.py`):
- Khi tài khoản thất bại ở các giai đoạn sau (như `CHATGPT_REG` hoặc `CHANGE_INFO`), trạng thái được ghi là `BLOCKED` hoặc `FAILED`.
- Nếu logic giải phóng cooldown trong `select_candidates()` chỉ viết cứng cho stage đầu (`HOTMAIL_LOGIN`), các tài khoản ở các stage sau sẽ bị kẹt vĩnh viễn trong `BLOCKED`, gây ra hiện tượng tích tụ hàng trăm tài khoản rác (ví dụ hơn 500 nick BLOCKED trên Farm).

## 2. Cạm Bẫy `_failure_time` Kiểm Tra Quá Khắt Khe
- Hàm trích xuất thời điểm thất bại (`_failure_time`) nếu chỉ chấp nhận `last_result.stage == STAGE_DAU` sẽ trả về `None` khi tài khoản gặp lỗi ở các stage khác.
- Khi trả về `None`, điều kiện so sánh `(now - fail_time) >= COOLDOWN_SECONDS` luôn sai, khiến tài khoản không bao giờ đáo hạn cooldown.

## 3. Kiến Trúc Khắc Phục Chuẩn Hóa
1. **Bao phủ toàn bộ các stage có thể Retry:**
   Mọi stage có thể thử lại an toàn (không phải QUARANTINE do nhập sai pass quá số lần cho phép) đều phải có nhánh kiểm tra cooldown:
   ```python
   elif stage in {"CHATGPT_REG", "CHANGE_INFO"} and status in {"BLOCKED", "FAILED", "ERROR"}:
       lr = info.get("last_result")
       lr_at = lr.get("at") if isinstance(lr, dict) else None
       fail_time = parse_time(lr_at) or parse_time(info.get("updated_at"))
       eligible = fail_time is not None and now_dt is not None and (now_dt - fail_time).total_seconds() >= 2 * 86400
       if eligible:
           status = info["status"] = "PENDING"
           log_telemetry_event(f"{stage.lower()}_cooldown_unblock", {
               "key": key, "machine": info.get("machine"), "email": info.get("email"),
               "stage": stage,
               "detail": f"{stage} cooldown elapsed (48h)",
           })
   ```
2. **Fallback thời gian tin cậy:**
   Luôn ưu tiên `last_result.at`, và fallback về `updated_at` của record state nếu `last_result` thiếu timestamp.
3. **Phân định ranh giới QUARANTINE vs BLOCKED:**
   - `QUARANTINE`: Lỗi nghiêm trọng chết cứng (ví dụ `login_retry_count >= 3`, sai pass, checkpoint cần can thiệp tay) ➔ CẤM auto-unblock.
   - `BLOCKED`: Cooldown tạm thời (proxy die, network timeout, rate limit) ➔ BẮT BUỘC auto-unblock sau khi hết hạn cooldown (thường là 24h hoặc 48h).
