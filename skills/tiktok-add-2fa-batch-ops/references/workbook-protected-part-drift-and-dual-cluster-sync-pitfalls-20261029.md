# Workbook Protected Part Drift & Dual-Cluster Sync Pitfalls (2026-10-29)

## 1. Hiện Tượng Thực Tế
- Batch 2FA trên Farm Admin (Máy 201-280) bị liệt 100% (Hoàn tất 0 | Lỗi 69).
- Sau khi kiểm tra hiện trường, thiết bị vật lý thực chất đã mở TikTok, lấy mã Secret 2FA và hoàn tất nạp OTP.
- Tuy nhiên ở bước cuối cùng khi ghi Secret vào file Excel, batch bị crash với lỗi:
  `automation_core.workbook.WorkbookError: WORKBOOK_PROTECTED_PART_DRIFT`
  hoặc:
  `automation_core.workbook.WorkbookError: BLOCKED_EXPECTED_WRITER_ID_MISSING:tiktok_tracking`

## 2. Nguyên Nhân Kỹ Thuật (Over-Engineering Pitfalls)
1. **Băm Hash SharedStrings trong File Nén Excel (`WORKBOOK_PROTECTED_PART_DRIFT`):**
   - Trong `automation_core/workbook.py`, hàm `protected_zip_parts()` kiểm tra tính toàn vẹn của workbook bằng cách hash SHA-256 các phần trong zip.
   - Khi bao gồm `xl/sharedstrings.xml`, bất kỳ thao tác ghi cell text mới nào (như chuỗi 32 ký tự Base32 Secret 2FA) đều làm thay đổi nội dung file `sharedstrings.xml`.
   - Kết quả: `automation-core` nhận định sai là cấu trúc Excel bị trôi và ném `WORKBOOK_PROTECTED_PART_DRIFT`, đánh sập toàn bộ runner.
   - **Cách sửa chuẩn:** Trong `protected_zip_parts()`, loại bỏ hoàn toàn `xl/sharedstrings.xml` khỏi danh sách kiểm tra (chỉ giữ drawings, charts, tables, media, relationships).

2. **Single-Writer Identity Security Theater (`assert_writer_identity`):**
   - Rào cản danh tính writer bắt buộc `expected_writer_id` và `declared_writer_id` khi cùng chạy trên một user Windows (`Admin`).
   - Thiếu biến môi trường dẫn đến `BLOCKED_EXPECTED_WRITER_ID_MISSING`.
   - **Cách sửa chuẩn:** Trong `python_runner/core/workbook.py`, bổ sung fallback mặc định `os.environ.get(...) or "tiktok_add_2fa"`.

3. **Cơ Chế Đồng Bộ Xuyên Host (Cross-Host Sync) Gây Treo Session:**
   - Dùng script SSH PowerShell cắt file Base64 thành các chunk nhỏ (1200-2500 chars) gọi lặp đi lặp lại qua SSH Windows làm nghẽn socket I/O, gây treo session và văng timeout.
   - **Cách sửa chuẩn:** Dùng thư mục đồng bộ OneDrive chung giữa 2 máy (`D:\OneDrive\TaadaaData\admin\`), copy 1 lần là máy Admin nhận ngay lập tức, sau đó gọi 1 lệnh PowerShell duy nhất để copy vào đích.

4. **Trích Xuất & Cứu Hộ Secret Từ Audit Log Khi Gặp Lỗi Ghi Workbook (Cross-Host Rescue):**
   - Khi điện thoại đã hoàn tất 2FA nhưng bước ghi workbook bị lỗi, Secret Key và timestamp luôn được ghi lại trong `2fa_audit.log` trên máy đích (`$LOCALAPPDATA/tiktok-add-bao-mat-f2a/logs/2fa_audit.log`).
   - Cần chạy regex trích xuất toàn bộ `(May, Row, Username, 2FA_Secret)` và backfill trực tiếp vào Master Excel để bảo tồn tài sản, tránh chạy lại làm hỏng trạng thái nick.
