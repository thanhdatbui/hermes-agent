# Thiết Kế Hook Đăng Video Vào Phiên Cuối Ca Nuôi Acc (Feed Session → Upload Hook)

## Bối cảnh & Mục tiêu
- Mỗi ngày farm chạy 3 ca (Sáng ~06:00, Chiều ~12:30, Tối ~19:00).
- Mỗi ca nuôi 1 nick riêng biệt (3 nick/máy/ngày theo Parity Lane: Ngày chẵn Rows 2,4,6; Ngày lẻ Rows 1,3,5).
- Mỗi ca gồm 3 phiên feed (~60 phút/phiên + pair gap 35-60 phút).
- Mục tiêu: Ở **phiên cuối cùng (phiên 3)** của mỗi ca (trước khi máy nghỉ dài chuyển tiếp qua ca tiếp theo), tự động kích hoạt script đăng video cho nick đó.

---

## 1. Quyết Định Kiến Trúc Đã Được Audit (AG Opus APPROVED)

### A. Giữ nguyên verify nick (ACCOUNT_SWITCHER) trong upload
- **Không bỏ verify**: `ACCOUNT_SWITCHER` trong `Tiktok-video` đã có fast-path: nếu nick trên UI profile đã đúng `target_account`, nó chỉ mất 1-2s kiểm tra và skip ngay lập tức.
- **Chống rủi ro lệch nick**: Nếu phiên feed 3 bị crash, restart hoặc gặp system popup, TikTok có thể tự nhảy về default account. Không verify sẽ dẫn đến đăng nhầm video của nick này sang nick khác (lệch niche, sai hashtag, hỏng kênh).

### B. Ánh xạ Account Row ↔ Tik Workbook
- Cấu trúc mapping 1-1 theo 1-based physical slot index:
  - Row 1 → `Tik1.xlsx`
  - Row 2 → `Tik2.xlsx`
  - Row 3 → `tik3.xlsx` (chữ thường trên đĩa)
  - Row 4, 5, 6 → `Tik4.xlsx`, `Tik5.xlsx`, `Tik6.xlsx`
- Runner feed session (`multi_machine_feed_session.py` / cron entrypoint) đã có `account.account_row_index` (hoặc `entry["account_row"]`).
- Canonical helper resolve tên file workbook:
  ```python
  def tik_workbook_filename(row_index: int) -> str:
      KNOWN_NAMES = {1: "Tik1", 2: "Tik2", 3: "tik3", 4: "Tik4", 5: "Tik5", 6: "Tik6"}
      base = KNOWN_NAMES.get(row_index, f"Tik{row_index}")
      return f"{base}.xlsx"
  ```

---

## 2. Chuỗi Preflight Gate Trước Khi Gọi Upload (Fail-Open / Safe-Skip)

Trước khi kích hoạt subprocess upload, runner feed session thực hiện preflight an toàn tuần tự. Bất kỳ điều kiện nào không thỏa mãn đều ghi log và SKIP an toàn, KHÔNG làm fail hay chặn kết quả phiên feed:

1. **Session Gate**: Chỉ chạy khi `session_index == 3` (hoặc phiên cuối của ca) VÀ `final_status in {"success", "degraded"}`. Các phiên 1, 2 bỏ qua 100%.
2. **Sensitive Stop Gate**: Nếu phiên nuôi dừng do lỗi nhạy cảm (`login`, `otp`, `2fa`, `captcha`, `security`, `verify`, `banned`, `locked`, `suspended`) → `UPLOAD_SKIPPED: sensitive-skip`.
3. **Workbook Tik Gate**: Kiểm tra file `D:\OneDrive\TaadaaData\kibe\Tik{row_index}.xlsx` (hoặc `tik3.xlsx`) có tồn tại không. Nếu chưa tạo file Tik → `UPLOAD_SKIPPED: workbook_not_found`.
4. **Account ID Gate**: Đọc dòng của máy trong file Tik: nếu `ID` trống hoặc `MISSING_ID` → `UPLOAD_SKIPPED: missing_id`.
5. **Video Render Ready Gate (kèm integrity check)**:
   - Lấy `Folder Video` và `next_video = int(Video Đã Đăng) + 1`.
   - Đường dẫn target: `D:\TIKTOK-videonuoinick\<Folder Video>\<next_video>.mp4`.
   - File phải tồn tại, size > 10KB và không bị write-lock (FFmpeg không đang render dở).
   - Nếu thiếu folder, thiếu mp4 hoặc file đang render → `UPLOAD_SKIPPED: video_not_rendered`.
6. **Time Budget & Hard Timeout Gate**:
   - Chỉ kích hoạt upload nếu thời gian còn lại trước ca kế tiếp ≥ 30 phút.
   - Subprocess upload chạy với `timeout=900` (15 phút hard timeout) để chống treo tiến trình làm trễ ca tiếp theo.

---

## 3. Quy Tắc Cô Lập Subprocess, Báo Cáo 3 Phần & Parity Rollover

1. **Subprocess & Try-Catch Isolation**:
   - `_run_follow_hook` và `_run_upload_hook` nằm trong 2 khối `try...except` độc lập — nếu follow hook bị lỗi/timeout thì upload hook vẫn được kích hoạt bình thường.
   - Gọi `tiktok_workflow` qua subprocess tương tự follow hook:
     `python -m tiktok_workflow --config D:\Taadaa\Tiktok-video\config-machine-<M>.yaml --workflow-workbook <TikPath> --machine <M> --no-dry-run`
   - Kết quả upload được ghi vào `upload_result.json` trong child artifact directory của máy.
   - Upload thành công hay lỗi skip đều độc lập với trạng thái kết thúc của feed session.

2. **Cấu Trúc Báo Cáo 3 Phần Độc Lập**:
   Sau phiên cuối, log summary tổng hợp kết quả từng máy rõ ràng 3 khâu độc lập:
   - **Feed (Lướt nuôi)**: `SUCCESS` / `FAILED` (kèm số video đã lướt).
   - **Follow (Theo dõi)**: `SUCCESS` / `FAILED` / `SKIPPED` (kèm số nick đã follow).
   - **Upload (Đăng video)**: `SUCCESS` / `SKIPPED` (kèm lý do: `workbook_not_found`, `video_not_rendered`, `missing_id`...) / `FAILED`.

3. **Parity Date Snapshot**:
   - Parity date (chẵn/lẻ) phải được snapshot từ lúc bắt đầu ca nuôi, không tính lại bằng `datetime.now()` tại thời điểm chạy upload phiên 3 (tránh trường hợp phiên 3 chạy qua 00:00 nửa đêm làm flip parity sang ngày hôm sau dẫn đến trỏ nhầm row/file Tik).
