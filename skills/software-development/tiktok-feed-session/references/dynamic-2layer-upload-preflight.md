# Dynamic 2-Layer Upload Preflight (TikTok Feed & Post Automation)

## Bối cảnh & Nguyên lý (Áp dụng từ 2026-08-25)
Trước đây, trong `multi_machine_feed_session.py`, hook đăng video cuối phiên bị giới hạn bởi hardcode danh sách row (ví dụ: `if upload_row not in (1, 2): return skipped`). Điều này khiến các ca nuôi acc khác (như Ca chiều / Ca tối chạy Row 3, 4,...) bị bỏ qua việc đăng video dù đã có sẵn file `tik3.xlsx` và video MP4 đã render đầy đủ trong thư mục.

Hệ thống đã chuyển đổi sang cơ chế **Kiểm tra động 2 lớp (Dynamic 2-Layer Preflight)** độc lập hoàn toàn với số thứ tự Row.

---

## 2 Lớp Kiểm Tra Bắt Buộc (2-Layer Gate):

### Lớp 1: Kiểm tra Workbook Đăng Video (`resolve_tik_workbook`)
1. Xác định file workbook cấu hình đăng video theo số thứ tự hàng tài khoản (`account.account_row_index`):
   - Row 1 ➔ `Tik1.xlsx`
   - Row 2 ➔ `Tik2.xlsx`
   - Row 3 ➔ `tik3.xlsx`
   - Row N ➔ `TikN.xlsx`
2. Kiểm tra file `TikN.xlsx` có tồn tại trong thư mục `D:\OneDrive\TaadaaData\kibe` hay không.
3. Đọc dữ liệu dòng của máy mục tiêu:
   - Kiểm tra ô `account_id` (ID TikTok): Phải có và không được là `MISSING_ID` hoặc rỗng.
   - Kiểm tra ô `folder_video`: Phải có thư mục gán nguồn video.
4. **Kết quả nếu thiếu:** Tự động ghi `upload_result.json` trạng thái `status: skipped` với lý do `workbook_not_found`, `missing_account_id` hoặc `missing_video_folder`.

### Lớp 2: Kiểm tra File Video MP4 trên đĩa (`media_source_root`)
1. Xác định số thứ tự video cần đăng tiếp theo: `next_video = posted_count + 1`.
2. Kiểm tra đường dẫn video thực tế:
   ```python
   video_file = Path("D:/TIKTOK-videonuoinick") / folder_video / f"{next_video}.mp4"
   ```
3. Bắt buộc kiểm tra đồng thời:
   - `video_file.is_file() == True`
   - `video_file.stat().st_size > 0` (file hợp lệ, không phải file rỗng).
4. **Kết quả nếu thiếu:** Tự động ghi `upload_result.json` trạng thái `status: skipped` với lý do `video_not_rendered` (kèm đường dẫn `expected_video`).

---

## Kích hoạt Subprocess Đăng Video
Chỉ khi **vượt qua đồng thời cả 2 lớp trên**, tiến trình dọn RAM/ATX mới được kích hoạt và subprocess đăng video (`scripts.tiktok_workflow.run_post`) mới được spawn:
```bash
python -m scripts.tiktok_workflow.run_post --config <config_yaml> --workflow-workbook <tik_workbook> --machine <M> --no-dry-run
```
Sau đó, kết quả đăng bắt buộc phải trải qua cổng kiểm chứng nghiêm ngặt `report.json` (`post_verified == True`, `status == SUCCESS`) trước khi được xác nhận thành công.
