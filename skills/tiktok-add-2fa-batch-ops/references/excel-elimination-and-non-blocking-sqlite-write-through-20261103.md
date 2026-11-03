# Triage: Excel Elimination in Credential Write-Through (tiktok-add-bao-mat-f2a)

## 1. Ngữ cảnh & Căn nguyên sự cố
- Khi toàn bộ farm chuyển dịch sang SQLite SSOT (`D:/Taadaa/data/farm_master.db`), file Excel legacy `D:\OneDrive\Tiktok_Reg\taikhoan_dat_v2_updated .xlsx` đã bị gỡ bỏ hoặc chuyển vào kho lưu trữ OneDrive không còn hiện diện trên đĩa.
- Dù runner mẹ (`run_batch_live_2fa.py`) đã freeze targets từ SQLite và `_verification()` đã kiểm tra trực tiếp SQLite SSOT, nhưng trong `python_runner/core/workbook.py`:
  - Hàm `_write_cell()` vẫn giữ kiến trúc cũ: **Bắt buộc mở file Excel trước bằng `openpyxl.load_workbook()`** để ghi cell rồi mới chạy khối `try...except` cập nhật SQLite ở bước 2.
  - Hậu quả: Khi `path.exists() == False` hoặc file rỗng/lỗi zip, `openpyxl` ném `zipfile.BadZipFile` hoặc `FileNotFoundError` $\rightarrow$ quật ngã toàn bộ tiến trình ghi credentials, 2FA secret không lưu được và worker văng lỗi crash.

## 2. Giải pháp cơ giới hóa bền vững (Commit e6acad5)
- **Đảo ngược thứ tự ưu tiên (SSOT First):**
  1. Cập nhật thẳng vào bảng `tiktok_accounts` trong `D:/Taadaa/data/farm_master.db` trước tiên thông qua `farm_db.update_tiktok_credentials`.
  2. Kiểm tra `if not path.exists(): return backup` $\rightarrow$ Nếu file Excel legacy không còn trên đĩa, hàm ghi nhận kết thúc thành công 100% dựa trên SQLite SSOT mà không thực hiện I/O file Excel.
  3. Bọc khối `_shared.single_writer_workbook_update` trong `try...except (OSError, openpyxl.utils.exceptions.InvalidFileException, zipfile.BadZipFile): return backup` để chống sập worker khi Excel dính lock hoặc file hỏng.

## 3. Quy tắc kiểm chứng & Invariant
- **Invariant:** Tuyệt đối không để thiếu file Excel legacy làm chặn đứng (blocking) luồng ghi credentials khi database SQLite SSOT đã nhận dữ liệu thành công.
- **Verification probe:** Chạy unit probe giả lập gọi `_write_cell()` với đường dẫn Excel không tồn tại: hàm phải return backup path hợp lệ và cập nhật SQLite thành công trong < 1 giây.
