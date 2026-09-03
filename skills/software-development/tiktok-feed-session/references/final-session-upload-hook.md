# Hook Upload Video tại Phiên Cuối Ca Nuôi Acc (Session 3)

## 1. Mục tiêu & Nguyên tắc kiến trúc
- **Thời điểm kích hoạt:** Chỉ chạy tại **phiên cuối cùng (phiên 3)** của mỗi ca nuôi acc, ngay sau khi hoàn tất lướt feed + follow. (Phiên 1 và 2 bỏ qua 100%).
- **Nguyên tắc cô lập & an toàn:**
  - Repo `Tiktok-video` (`tiktok_workflow`) giữ nguyên 100% không chỉnh sửa code.
  - Hook upload (`_run_upload_hook`) chạy qua subprocess (`python -m tiktok_workflow`), độc lập trong khối `try...except` riêng biệt so với follow hook (`_run_follow_hook`).
  - Lỗi/timeout của follow hook không ảnh hưởng upload hook; lỗi/skip của upload hook không làm fail kết quả nuôi acc.
  - Kết quả ghi vào `upload_result.json` trong thư mục artifact của máy.

## 2. Ánh xạ Ca Nuôi ↔ Workbook Tik
- Ca nuôi của máy tương ứng với `account_row_index` (1..6) trong `taikhoan_run_safe.xlsx`.
- Ánh xạ 1-1 với file Tik:
  - Row 1 -> `Tik1.xlsx`
  - Row 2 -> `Tik2.xlsx`
  - Row 3 -> `tik3.xlsx` *(lưu ý: chữ thường trên đĩa `D:\OneDrive\TaadaaData\kibe\`)*
  - Row 4, 5, 6 -> `Tik4.xlsx`, `Tik5.xlsx`, `Tik6.xlsx`
- Hàm resolve `resolve_tik_workbook(base_dir, row_index)` hỗ trợ fallback tìm case-insensitive qua `Path.glob()`.

## 3. Quy trình 5 tầng Preflight Gates (Safe Skip)
Trước khi đụng vào điện thoại, runner kiểm tra tuần tự trên ổ cứng PC:
1. **Gate 1 (Session Gate):** `_session_index == 3` (hoặc cờ `force_upload_hook`). Nếu `< 3` -> `skipped: not-final-session-<N>`.
2. **Gate 2 & 3 (Sensitive Stop Gate):** Nếu `stop_reason` của phiên nuôi chứa các từ nhạy cảm (`login`, `otp`, `2fa`, `captcha`, `security`, `verify`, `password`, `locked`, `banned`, `suspended`) -> `skipped: sensitive-skip`.
3. **Gate 4a (Workbook Gate):** Kiểm tra file `Tik{N}.xlsx` có tồn tại không. Chưa có -> `skipped: workbook_not_found`.
4. **Gate 4b (Account ID Gate):** Mở file Tik tìm dòng có `Máy == machine`:
   - Không tìm thấy máy -> `skipped: machine_not_in_workbook`.
   - `ID` TikTok trống / None / `MISSING_ID` -> `skipped: missing_account_id`.
   - `Folder Video` trống -> `skipped: missing_video_folder`.
5. **Gate 5 (Video Render Ready Gate):**
   - Đọc `Video Đã Đăng` (số nguyên, mặc định 0).
   - Tính số video tiếp theo: `next_video = int(posted_count) + 1`.
   - File video nguồn trên PC: `D:\TIKTOK-videonuoinick\<Folder Video>\<next_video>.mp4`.
   - Nếu file không tồn tại hoặc kích thước `0 bytes` (chưa render xong) -> `skipped: video_not_rendered`.

## 4. Thực thi Subprocess & Báo cáo
- **Lệnh thực thi:**
  ```bash
  python -m tiktok_workflow \
    --config "D:\Taadaa\Tiktok-video\config-machine-<May>.yaml" \
    --workflow-workbook "D:\OneDrive\TaadaaData\kibe\<TikN.xlsx>" \
    --machine "<May>" \
    --no-dry-run
  ```
- **Timeout:** 15 phút (900s) qua `subprocess.TimeoutExpired`.
- **Định dạng báo cáo 3 khâu rõ ràng:**
  - Lướt feed: `SUCCESS` / `FAILED`
  - Follow: `SUCCESS` / `FAILED` / `SKIPPED`
  - Upload video: `SUCCESS` / `SKIPPED (lý do)` / `FAILED`
