# 2FA Batch Concurrency: Workbook Lock Contention & Journal Recovery Protocol (14/10/2026)

## 1. Hiện tượng nghẽn Lock Workbook khi chạy 40 Workers đồng loạt

### Hiện tượng thực tế (Run aa82aaeb0334 ngày 14/10/2026)
- Báo cáo watchdog chuỗi sau ca trưa: `Farm Kibe (Máy 1-80): Hoàn tất 13 máy | Bỏ qua 7 | Lỗi 54`.
- Hiện trường thực tế kiểm tra:
  - 13 máy đầu ghi thành công vào file Excel `taikhoan_dat_v2_updated .xlsx` (có backup tương ứng từ 16:23 -> 16:26).
  - Có **29 tài khoản** nằm trong danh sách "Lỗi" thực tế **ĐÃ BẬT 2FA THÀNH CÔNG** trên app TikTok:
    - Secret đã được lưu an toàn trong file mã hóa DPAPI tại `C:\Users\Kibe\AppData\Local\codex_gmail_debug-tiktok-add-bao-mat-f2a\journals\`.
    - Trạng thái journal: `authenticator_confirmed`.
    - Secret đã được ghi log kiểm toán tại `C:\Users\Kibe\AppData\Local\tiktok-add-bao-mat-f2a\logs\2fa_audit.log`.
  - Nhưng trong file Excel, cột `2FA` của 29 tài khoản này vẫn là `None`.

### Nguyên nhân gốc rễ
1. **Tranh chấp File Lock trên OneDrive:** File `taikhoan_dat_v2_updated .xlsx` nằm trong thư mục OneDrive (`D:\OneDrive\TaadaaData\kibe\`). Khi openpyxl cập nhật file, cơ chế `atomic_workbook_update` tạo bản copy tạm và `os.replace`. Nếu OneDrive client đang sync dở hoặc nhiều tiến trình cùng tranh chấp `acquire_workbook_lock`, các tiến trình phía sau sẽ chạm ngưỡng timeout `WORKBOOK_LOCK_TIMEOUT_SECONDS = 120.0s`.
2. **Đồng pha hoàn tất OTP:** Khi chạy 40 workers song song, sau khoảng 5-8 phút mở app và điều hướng, hàng chục workers đồng loạt submit OTP và chuyển sang bước ghi Excel `write_2fa` cùng lúc (16:26 - 16:35), gây ùn tắc hàng đợi ghi file.
3. **Thứ tự nghiệp vụ trong `execute_phase_b`:**
   ```python
   operations.confirm_authenticator_stable()
   record = authenticator_confirmed(record)
   journal.transition(account_id, PhaseBState.OTP_SUBMITTED, PhaseBState.AUTHENTICATOR_CONFIRMED)
   operations.write_workbook(record, secret)  # <-- Văng WorkbookError ở đây
   record = written(record)
   journal.transition(account_id, PhaseBState.AUTHENTICATOR_CONFIRMED, PhaseBState.WRITTEN)
   ...
   journal.purge(account_id)
   ```
   Do bước ghi workbook văng `WorkbookError`, journal dừng lại ở trạng thái `authenticator_confirmed`, không được purge, và worker trả về exit code `1` (báo `failed`).

---

## 2. Quy trình cứu hộ không can thiệp thiết bị (Zero Touch Recovery)

**CẤM TUYỆT ĐỐI:** Không reset 2FA, không bấm tay trên máy, không chạy lại toàn bộ luồng live từ đầu gây xung đột tài khoản.

### Cơ chế tự phục hồi (`_resume`)
Trong `core/phase_b_runner.py`:
Khi runner phát hiện TikTok đã bật 2FA (`tiktok_2fa_enabled() == True`) VÀ tìm thấy journal cũ còn lưu:
```python
if enabled:
    existing = journal.load(account_id)
    return _resume(identity, journal, operations, existing)
```
Hàm `_resume` sẽ:
1. Đọc lại `secret` từ journal `authenticator_confirmed`.
2. Ghi bù vào Excel workbook `operations.write_workbook(record, secret)`.
3. Chuyển state journal sang `written` -> `email_disabled` -> `purge(account_id)`.
4. Trả về `PhaseBResult("success", "resumed")`.

### Biện pháp phòng ngừa nghẽn lock
1. **Hạ `max-workers` khi chạy batch:** Với thao tác ghi chung 1 file Excel nằm trên OneDrive, khuyến nghị `--max-workers 15` hoặc tối đa `20` thay vì `40` để rải đều thời gian hoàn tất OTP, giảm đỉnh tải tranh chấp lock.
2. **Khôi phục từng cụm nhỏ:** Khi có journal tồn đọng (`authenticator_confirmed`), chạy lệnh nhắm mục tiêu theo danh sách dòng:
   `python python_runner/run_batch_live_2fa.py --workbook-path "..." --rows <row1,row2,...> --max-workers 5 --live`
