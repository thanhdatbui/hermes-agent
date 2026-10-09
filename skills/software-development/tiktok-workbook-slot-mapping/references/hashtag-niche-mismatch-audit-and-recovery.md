# Hashtag & Niche Mismatch Audit and Recovery Playbook

## 1. Triệu chứng & Bản chất lỗi
- **Hiện tượng**: Video đăng lên TikTok bị gắn sai hashtag hoàn toàn so với nội dung thực tế (ví dụ: video phóng sự / Tin 3 phút nhưng gắn hashtag `#nhacvietnam #singing #amnhac`; video selfie hát hò nhưng gắn `#game #gaming #choigame`).
- **Bản chất kỹ thuật**:
  1. Script đăng bài (`run_post.py` -> `hashtag_selector.py`) không phân tích nội dung video lúc upload mà đọc trực tiếp 2 cột **`Keyword Video`** và **`Hashtag Pool`** từ file `Tik*.xlsx`.
  2. Các cột này được đồng bộ từ bảng `folders` trong `D:\CodexRuntime\tiktok-video\state.db` qua `sync_all_tik_keywords.py`.
  3. Khi cào video hoặc khởi tạo ban đầu, `niche` trong `state.db` bị gán nhầm (do map cứng theo thứ tự dòng của `niches_pool.txt` hoặc nguồn tải bị tráo đổi nội dung).

## 2. Quy trình xử lý chuẩn (Audit & Remediation)

### Bước 1: Bảo toàn video đã đăng (Anti-Panic Rule)
- **CẤM XÓA HOẶC ẨN VIDEO ĐANG CẮN VIEW**: Nếu video đã đăng đạt tương tác cao (hàng nghìn đến chục nghìn like/view), giữ nguyên 100%.
- Thuật toán TikTok đề xuất dựa vào retention rate và âm thanh là chính; xóa video nhiều like sẽ làm tụt Trust Score và bóp reach toàn kênh.

### Bước 2: Truy vết ngược 3 cấp (DB -> Excel -> Script)
1. **Tìm thông tin nick trong Excel**: Tra cứu username trong `Tik1.xlsx` .. `Tik8.xlsx` để lấy `Máy`, `Folder Video` (thư mục render `D:\TIKTOK-videonuoinick\<Folder>`) và `video gốc` (thư mục nguồn `D:\video goc\<Folder>`).
2. **Kiểm tra nội dung thực tế**:
   - Trích xuất 1-2 frame bằng ffmpeg: `ffmpeg -ss 00:00:03 -i D:\video goc\<Folder>\1.mp4 -vframes 1 frame.jpg`.
   - Chạy WinRT OCR (`scripts/winrt_ocr.py`) để đọc logo, tiêu đề, chữ hiển thị trong video.
3. **Đối soát `state.db`**:
   - Truy vấn SQLite: `SELECT folder_num, niche, source_url FROM folders WHERE folder_num = <video_goc>`.
   - So sánh `niche` trong DB với nội dung thực tế của video.

### Bước 3: Sửa đồng bộ (DB & Workbook)
1. **Sửa `state.db` trước**: Cập nhật `niche` của `folder_num` về đúng slug (ví dụ: `tintuc`, `cahat`, `thoitrang`). Tránh để cron `sync_all_tik_keywords.py` chạy lại ghi đè ngược giá trị sai.
2. **Cập nhật `Tik*.xlsx`**:
   - Sửa cột `Keyword Video` và `Hashtag Pool` ở sheet `TaiKhoan`.
   - Cập nhật tương ứng ở sheet `Hashtag theo Folder`.
   - Dùng `atomic_workbook_update` để chống hỏng file.

### Bước 4: Batch Audit toàn Farm bằng Frame OCR
- Chạy script kiểm tra định kỳ quét `D:\video goc\<N>`: trích xuất frame tại giây thứ 5, chạy OCR tìm các từ khóa nhận diện nhanh (như logo đài truyền hình, watermark báo, gameplay overlay) để đối chiếu tự động với cột `niche` trong `state.db`.
