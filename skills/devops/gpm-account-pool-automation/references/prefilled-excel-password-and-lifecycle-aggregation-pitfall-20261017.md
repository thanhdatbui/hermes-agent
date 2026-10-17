# Pre-filled Excel Passwords & Lifecycle Aggregation Invariants (2026-10-17)

## 1. Hiện tượng & Bản chất Lỗi (The Pre-filled Password Mirage)
Trong báo cáo định kỳ vòng đời Hotmail ➔ GPM ➔ ChatGPT (`cron_hotmail_gpm_lifecycle_6h_report.py`), số liệu đăng ký thành công ChatGPT bị phồng ảo nghiêm trọng:
- Toàn farm báo cáo **866/1035 (83.7%)** tài khoản đã Reg ChatGPT thành công.
- Trong đó Farm Kibe (M1-80) báo **392/409** nick đã reg ChatGPT, trong khi chỉ mới có **86/409** nick đăng nhập Hotmail thành công.

### Root Cause:
Trong file Excel nguồn (`taikhoan_dat_v2_updated .xlsx`), cột `PASS CHATGPT` được sinh ngẫu nhiên và điền sẵn mật khẩu dự kiến ngay từ khâu cấp phát tài khoản (provisioning).
Script tổng hợp cũ kiểm tra:
```python
# SAI: Cột pass chatgpt đã có sẵn từ Excel dù chưa hề chạy tool reg!
has_chatgpt = _has_valid_timestamp(raw, "chatgpt_registered_at", key, _flag) or bool(raw.get("chatgpt_password"))
```
Điều này dẫn đến 306 nick Kibe còn kẹt ở `HOTMAIL_LOGIN` (chưa từng chạy reg ChatGPT) vẫn bị đếm là đã đăng ký thành công.

---

## 2. Quy tắc Bất biến khi Tính Toán Chỉ số Vòng đời (Lifecycle Counting Invariant)

1. **Timestamp là Bằng chứng Xác thực Duy nhất:**
   Chỉ công nhận tài khoản đã đăng ký ChatGPT khi trường `chatgpt_registered_at` có giá trị timestamp ISO hợp lệ (`_has_valid_timestamp`).
2. **Suy luận Trạng thái DONE (Full Lifecycle Completed):**
   Tài khoản đã hoàn tất toàn bộ chu kỳ đổi pass & bảo mật (`bucket == STAGE_DONE`) được suy luận là đã đăng ký ChatGPT thành công, vì để đạt `DONE`, tài khoản bắt buộc phải đi qua các bước trước đó trong state machine.
3. **Chuẩn hóa hàm Helper `_is_chatgpt_registered`:**
   ```python
   def _is_chatgpt_registered(rec: dict[str, Any]) -> bool:
       """Xác định tài khoản đã đăng ký ChatGPT thành công (has_chatgpt hoặc đã hoàn tất chu kỳ DONE)."""
       return rec.get("stage") not in REGISTRATION_VOID_STAGES and (
           bool(rec.get("has_chatgpt")) or rec.get("bucket") == STAGE_DONE
       )
   ```
4. **Loại trừ Trạng thái Hủy (Registration Void):**
   Nếu `stage` thuộc `REGISTRATION_VOID_STAGES` (`{"BLOCKED", "FAILED"}`), tài khoản bị xem là hỏng ở bước đăng ký và tuyệt đối không được tính vào `chatgpt_ok`.

---

## 3. Strike 3 Reviewer Hand-off & Foreground Timeout Trap

Khi Closeout Gate (`closeout_gate.py`) trượt 3 lần (Strike 3) và chuyển giao quyền sửa code cho Claude CLI (`claude_worker.py --role worker`):
- **Cạm bẫy:** Chạy `claude_worker.py` trong foreground với timeout 55-60s sẽ bị `GUARD_FOREGROUND_TIMEOUT_EXCEEDED` hoặc timeout exit 124, vì Claude CLI cần tối thiểu 120-180s để đọc context, phân tích diff, gọi tool patch và chạy pytest toàn bộ test suite.
- **Kỷ luật điều phối:** BẮT BUỘC dispatch `claude_worker.py` trong tiến trình nền với:
  ```python
  terminal(command="python D:/Taadaa/tools/claude_worker.py ...", background=True, notify_on_complete=True, timeout=300)
  ```
  Sau khi phát lệnh nền, Coordinator trả lời người dùng và nhả context để harness tự động đánh thức khi worker kết thúc.
