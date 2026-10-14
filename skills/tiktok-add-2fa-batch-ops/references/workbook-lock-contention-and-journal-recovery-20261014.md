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
1. **Hạ `max-workers` khi chạy batch:** Với thao tác ghi chung 1 file Excel nằm trên OneDrive, BẮT BUỘC đặt `--max-workers 15` (hoặc tối đa `20`) thay vì `40` để rải đều thời gian hoàn tất OTP, triệt tiêu đỉnh tải tranh chấp lock.
2. **Quy trình Write-Through tức thì (Direct Journal Flush) — CẤM NGÂM CHỜ:**
   Khi kết thúc ca batch mà có nick dính lỗi do nghẽn lock Excel (nhưng OTP đã confirm trên TikTok và secret đã lưu journal DPAPI), Coordinator BẮT BUỘC chạy ngay script xả journal vào Excel thay vì bắt user chờ ca sau:
   ```bash
   python D:/Taadaa/tools/recover_journal_2fa_to_excel.py --apply
   ```
   * *Ưu điểm:* Mở file Excel đúng 1 lần duy nhất, ghi n record đồng thời trong <15s, 0% rủi ro nghẽn lock, zero touch (không chạm ADB, không cần device lock, không sợ đụng ca nuôi).
   * *Hậu kiểm:* Script tự động đối soát identity (Máy, ID), verify committed cell và purge journal tương ứng.
3. **Khi nào mới dùng `--rows ... --live`:** Chỉ dùng khi nick bị kẹt ở bước trước đó (`otp_submitted` hoặc `captured` mà chưa confirm được authenticator). Khi journal đã ở trạng thái `authenticator_confirmed`, CẤM bật lại `--live` làm phiền thiết bị.

---

## 3. Kiến Trúc Vá Triệt Để 2 Tầng: In-Place Retry & Post-Batch Journal Drain (15/10/2026)

### Tầng 1: Tự động Retry tại chỗ khi ghi Excel (`_write_cell`)
- Khi worker hoàn tất OTP, `write_2fa` gọi `_write_cell`.
- Thay vì văng lỗi `WorkbookError` ngay lập tức khi chạm `BLOCKED_TIMEOUT_WORKBOOK_LOCK` hoặc `WORKBOOK_REPLACE_FAILED`, `_write_cell` được bọc vòng lặp retry 5 lần:
  * Khoảng chờ ngẫu nhiên có jitter: `sleep_func(random.uniform(1.5, 4.0) * (attempt + 1))`
  * Cho phép hàng đợi ghi file tự giải phóng thay vì làm fail worker.

### Tầng 2: Tự động gom ghi bù cuối Batch (`_drain_pending_journals`)
- Tại hàm `main()` của `run_batch_live_2fa.py`, ngay sau khi tất cả worker hoàn tất:
  * Quét các target có trạng thái `failed`.
  * Nếu phát hiện journal ở trạng thái `AUTHENTICATOR_CONFIRMED`, runner mở file Excel đúng 1 lần, ghi đồng loạt tất cả các secret còn thiếu vào Cột 5 (`2FA`), verify lại và purge journal.
  * Cập nhật kết quả các target đó sang `success` (`RECONCILED_FROM_JOURNAL`).
  * Tuyệt đối không để secret tồn đọng trong journal bắt user phải chờ sang các ca sau.

### Kỷ luật Watchdog No-Agent Exit Code
- Với cronjob chạy ngầm (`no_agent: true`), việc có một số máy fail/skip trong cụm 160 máy là trạng thái vận hành bình thường (`partial_failure`).
- CẤM script watchdog trả về `return 1` khi `fail > 0` vì sẽ làm Hermes kích hoạt báo động đỏ sập cron giả tạo (`Cron failed: Script exited with code 1`). Chỉ trả về non-zero khi script crash hệ thống không thể chạy tiếp.
