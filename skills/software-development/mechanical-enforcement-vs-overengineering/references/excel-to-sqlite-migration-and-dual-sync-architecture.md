# Quy Chuẩn Migration Sổ Cái: Cắt Bỏ Dependency Excel Sang SQLite SSOT

## 1. Bối cảnh & Căn nguyên
- **Vấn đề cốt lõi:** Các workbook Excel (`Tik1.xlsx` .. `Tik8.xlsx`, `taikhoan_run_safe.xlsx`) nằm trong thư mục đồng bộ OneDrive thường xuyên gây ra lỗi Windows PermissionError (WinError 32) hoặc `RecallOnDataAccess` khi nhiều runner/watchdog chạy song song.
- **Quy chuẩn đích:** Thay thế 100% việc đọc/ghi trạng thái workflow trong runtime production sang bảng SQLite tập trung `tiktok_workflow_state` đặt tại local disk (`D:/Taadaa/data/farm_master.db`). Excel chỉ đóng vai trò xuất báo cáo (Reporting Only), cấm làm tắc nghẽn luồng thi công của bot.

## 2. Cấu trúc bảng `tiktok_workflow_state` trong `farm_master.db`
Bảng lưu trữ composite key `(machine_id, slot_no)` thay thế toàn bộ 13 cột của Sheet `TaiKhoan` trong các file `TikN.xlsx`:
- `machine_id` (INT), `slot_no` (INT): Khóa chính kép đại diện cho máy (1-80) và ca chạy (1-8).
- `device_serial` (TEXT), `username` (TEXT): Định danh thiết bị và nick TikTok.
- `folder_render` (INT), `folder_raw` (INT): Thư mục video render bot đăng và video gốc cào về.
- `niche_keyword` (TEXT), `hashtag_pool` (TEXT): Chủ đề ngách và hashtag tương ứng.
- `posted_count` (INT): Cursor tăng tiến số video đã đăng (Monotonic counter).
- `data_status` (TEXT), `render_status` (TEXT), `render_count` (INT), `avatar_status` (TEXT).
- `updated_at` (TEXT): Dấu thời gian ISO8601 cập nhật trạng thái.

## 3. Kiến Trúc DAL & Fallback Hai Chiều (Dual-Path Robustness)
- Trong giai đoạn chuyển tiếp, `account_source.py` được trang bị cơ chế:
  1. Thử đọc workbook Excel như bình thường. Nếu gặp lỗi lock file hoặc permission, tự động fallback sang đọc từ SQLite `tiktok_workflow_state` qua `_read_row_from_sqlite()`.
  2. Khi ghi nhận tiến độ (`update_video_number`, `update_avatar_status`): Ghi thành công vào Excel thì đồng bộ ngay vào SQLite; nếu Excel bị crash/lock không ghi được thì ghi trực tiếp vào SQLite để bảo toàn cursor, không làm đứt gãy tiến trình của state machine.
- Module truy xuất chuẩn hóa: `D:/Taadaa/tools/farm_sqlite_dal.py` cung cấp các hàm `get_slot_accounts(slot)`, `get_account_by_machine_and_slot(machine, slot)`, `update_workflow_cursor(machine, slot, video_num)`.

## 4. Kỷ Luật An Toàn Khi Chạy SQLite
- Bắt buộc bật `PRAGMA journal_mode=WAL;` và `PRAGMA busy_timeout=15000;` để hỗ trợ đa tiến trình truy cập đồng thời không bị lỗi `database is locked`.
- Cấm tuyệt đối đặt file SQLite active trong OneDrive.
