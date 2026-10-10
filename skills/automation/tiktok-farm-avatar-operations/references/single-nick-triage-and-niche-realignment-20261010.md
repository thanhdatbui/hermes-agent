# Single-Nick Profile Triage & Niche Realignment (2026-10-10)

## Context & Scenario
Khi Operator gửi ảnh màn hình Profile TikTok từ điện thoại cá nhân (ví dụ: `@.thy.v5` "Thúy Vũ" Máy 19 Tik 4 Kibe) kèm lệnh ngắn gọn: *"Chuẩn hoá ava hashtag nick này"*:
Kênh thường dính combo 3 lớp lệch hệ thống:
1. **Lệch 2 không gian số**: `Folder Video` (render thực tế, ví dụ `148`) khác với `video gốc` (ví dụ `259`). Bot upload đăng bài theo `Folder Video`, nhưng tool cũ lại bốc video thô của máy khác theo `video gốc`.
2. **Lệch Niche & Hashtag Pool**: Cột `Keyword Video` trong `Tik<N>.xlsx` ghi nhãn cũ/khó viral (ví dụ `Ngoại ngữ`), hashtag lệch hoàn toàn với nội dung video thực tế đang đăng (ví dụ loạt vlog/clip nữ sinh THPT Lê Quý Đôn).
3. **Lệch Avatar trên App**: Avatar trên app là ảnh từ thời reg nick hoặc cắt trúng clip mẹ & bé sơ sinh dính chữ đỏ lẹm, hoàn toàn sai nhân khẩu học và vibe của kênh.

---

## Canonical 5-Step Resolution Workflow

### Bước 1: Định danh O(1) Máy, Slot Tik & Folder Video
Truy vấn trực tiếp trong `D:/Taadaa/data/tiktok_tracker.db`:
```python
# Tra cứu máy và slot
SELECT username, may, tik FROM account_mapping WHERE username = '<handle>';
# Tra cứu folder và trạng thái queue
SELECT folder_video, video_goc, status FROM avatar_replace_queue WHERE username = '<handle>';
```
Xác định chính xác: Số Máy (ví dụ `19`), Slot Tik (ví dụ `4`), và `Folder Video` thực tế (ví dụ `148`).

---

### Bước 2: Khám nghiệm Video Thực tế & Trích xuất Avatar Chuẩn Niche
- **Quy tắc bất biến**: Trích xuất avatar 100% từ video thành phẩm trong `D:/TIKTOK-videonuoinick/<Folder Video>/` (thư mục đang thực tế đăng bài), CẤM TUYỆT ĐỐI bốc theo `video gốc`.
- Quét các video đại diện (ví dụ `6.mp4`, `1.mp4`, `3.mp4`) để tìm frame cận cảnh / trung cận rõ mặt nhân vật chính của kênh:
  - Loại bỏ các frame dính phụ đề vietsub hoặc text banner.
  - Dùng lưới tọa độ và Vision API (qua 9Router `http://127.0.0.1:20128/v1/chat/completions`, model `ag/gemini-3.7-flash-high`) đo chính xác đỉnh tóc, mắt, cằm.
  - Cắt cúp khung vuông 512x512 có khoảng thở đỉnh đầu (headroom 5-10%), đường mắt nằm ở 1/3 trên của hình tròn, và cằm có khoảng nâng đỡ tự nhiên.
  - Yêu cầu Vision API thẩm định circular mask đạt điểm $\ge 8.5/10$ (ví dụ đạt `9.2/10`).

---

### Bước 3: Đồng bộ File Ảnh Nguyên Tử 2 Đầu Kho
- Sao lưu file cũ thành `.bak`.
- Ghi đè nguyên tử qua `.tmp.jpg` $\to$ `.replace()` vào cả 2 đầu kho:
  1. `D:/TIKTOK-videonuoinick/<Folder Video>/avatar.jpg`
  2. `D:/video goc/<Folder Video>/avatar.jpg`

---

### Bước 4: Chuẩn hoá 4 Tầng Dữ liệu & TỰ ĐỘNG KHÓA BẢO VỆ THỦ CÔNG
1. **Tự động Khóa Avatar Thủ công (Anti-Mass Regeneration Guard):**
   - BẮT BUỘC tự động ghi `Folder Video` và `video gốc` vào cả 2 file registry:
     * `D:/Taadaa/Tiktok-video/data/manual_avatar_protected_folders.json`
     * `D:/Taadaa/data/manual_avatar_protected_folders.json`
   - BẮT BUỘC tạo file marker vật lý `.manual_avatar_locked` tại cả 2 đầu kho:
     * `D:/TIKTOK-videonuoinick/<Folder Video>/.manual_avatar_locked`
     * `D:/video goc/<video gốc>/.manual_avatar_locked`
   - CẤM TUYỆT ĐỐI chờ Operator phải nhắc lệnh khóa; bất kỳ nick nào Operator đã yêu cầu đổi/chọn ava qua chat đều BẮT BUỘC PHẢI TỰ ĐỘNG KHÓA NGAY LẬP TỨC.
2. **Workbook `Tik<N>.xlsx`**:
   - Khóa cứng `video gốc = Folder Video` (hoặc số folder video gốc thật tương ứng).
   - Cập nhật `Keyword Video` chuẩn 1 trong 12 Niche Hot (ví dụ `Học sinh`).
   - Cập nhật `Hashtag Pool` khớp chính xác nội dung video.
   - Đặt cột `Avatar` = `OK` (khi đã up xong) hoặc `PENDING` (khi chờ runner).
3. **SQLite `tiktok_tracker.db` (`avatar_replace_queue`)**:
   - Cập nhật `video_goc = Folder Video`, `status = 'DONE'` (nếu đã up xong) hoặc `'PENDING'` (nếu chờ up), `last_error = NULL`, `updated_at = datetime('now', 'localtime')`.
4. **`state.db` (Cả 2 bản C: và D:)**:
   - `UPDATE folders SET niche='<niche>' WHERE folder_num=<Folder Video>;`

---

### Bước 5: Bằng chứng Trực quan Gate 6 & Kích hoạt Runner
1. **Dựng ảnh Composite 3 Panel**:
   - Panel 1: Avatar cũ trên nick (crop từ screenshot của User, chỉ rõ điểm lệch ngách).
   - Panel 2: Avatar mới chuẩn ngách (khung vuông 512x512 nét).
   - Panel 3: Khung tròn TikTok giả lập (circular preview đạt score cao).
   - Gọi Vision API soi mắt xác nhận cả 3 panel hiển thị rõ ràng, không lỗi hiển thị trước khi đính kèm `MEDIA:`.
2. **Kích hoạt Standalone Avatar Runner**:
   - Truyền biến môi trường: `TIKTOK_VIDEO_AUTOMATION_CORE_VERSION=0.4.45`.
   - Chạy nền với event-driven wakeup:
     ```powershell
     powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 -Tik <Tik> -MaxParallel 1 -HostConfigPath D:\Taadaa\machine-config\kibe.yaml -ForceAvatarMachineList "<May>"
     ```
