# Single Channel Per Folder Invariant & Historical Multi-Channel Triage

## Bối cảnh & Tình huống (17/09/2026)
Trong quá trình kiểm tra kho video tải về (`state.db`), phát hiện một số folder chứa video từ 2-3 kênh YouTube/TikTok khác nhau (hoặc các kênh Shorts lớn như `@KhánhVyOFFICIAL`, `@Thamdancesports`, `@AutoPro2008` xuất hiện ở nhiều folder). Điều này làm dấy lên nghi vấn:
1. Script download bị lỗi tải trùng nguồn / trùng video giữa các folder?
2. Tại sao 1 folder lại có video từ nhiều kênh khác nhau?

---

## 1. Bản chất kiến trúc và Quy tắc "1 Folder = 1 Kênh duy nhất" (User Rule)
- **Quy chuẩn cốt lõi của User**: Mỗi folder video (khoảng 45-65 video) phục vụ cho một tài khoản TikTok nuôi BẮT BUỘC phải lấy từ **DUY NHẤT 1 KÊNH NGUỒN**, có chủ thể, phong cách, giọng nói và nhận diện độc bản.
- **CẤM TUYỆT ĐỐI**: Không bao giờ nhồi ghép video từ 2-3 kênh khác nhau vào cùng 1 folder khi kênh ban đầu bị thiếu clip. Nếu kênh không đủ video tối thiểu (`min_videos`), phải chuyển kênh khác hoặc báo `insufficient_pool` để cào nguồn đạt chuẩn mới, KHÔNG được cộng dồn (stitch) nhiều kênh.

---

## 2. Vì sao có dữ liệu cũ chứa nhiều kênh trong 1 folder?
- **Dữ liệu lịch sử tháng 8 (17/08 - 24/08)**: Trước thời điểm User thắt chặt quy tắc, phiên bản sơ khai của script `download_by_niche.py` có logic: nếu 1 kênh chỉ cào được 15-20 video (dưới ngưỡng 45), vòng lặp tiếp tục bốc kênh tiếp theo trong niche để tải dồn cho đủ số lượng.
- **Hiện tượng "kênh xuất hiện ở nhiều folder"**:
  - Đối soát thực tế trên bảng `videos` của SQLite: **Tổng số video bị trùng lặp tuyệt đối giữa các folder là 0 (0 duplicate video)**.
  - Các kênh lớn (hàng trăm clip Shorts) trong đợt cũ bị bốc 20 clip vào Folder A, rồi bốc 25 clip khác vào Folder B. Dù file video không trùng nhau, nhưng **phong cách nội dung và avatar kênh gốc bị phân mảnh**, vi phạm nguyên tắc nhận diện thương hiệu của User.

---

## 3. Lỗ hổng kỹ thuật (Pitfall) cần lưu ý khi audit Downloader
Khi kiểm tra hàm lọc nguồn `eligible_sources` trong `download_by_niche.py`:
1. **Bẫy chỉ check bảng `folders`**:
   - Câu lệnh cũ: `SELECT COUNT(*) FROM folders WHERE source_channel=? AND status IN ('complete','complete_partial')`.
   - Lỗ hổng: Nếu một kênh được dùng làm kênh phụ (chỉ ghi vào bảng `videos` mà không cập nhật `folders.source_channel`), hoặc folder bị lưu `source_channel IS NULL` trong các đợt chạy dở, hàm `eligible_sources` sẽ đếm ra `0` và cho phép tái sử dụng kênh đó cho folder khác.
2. **Quy tắc kiểm tra khóa chặt (UNION check)**:
   - Khi audit hoặc vá code downloader, bắt buộc kiểm tra sự tồn tại của kênh trên **cả 2 bảng** (`folders` và `videos`):
     ```sql
     SELECT COUNT(DISTINCT folder) AS n FROM (
         SELECT folder_num AS folder FROM folders WHERE lower(source_channel) = lower(?) AND status IN ('complete','complete_partial')
         UNION
         SELECT folder FROM videos WHERE lower(source_channel) = lower(?) AND status = 'downloaded' AND folder IS NOT NULL
     )
     ```
3. **Phân biệt rạch ròi giữa Dữ liệu Cũ vs Code Mới**:
   - Trước khi vội vàng kết luận "code downloader đang bị lỗi tải trùng nguồn", Coordinator/Worker BẮT BUỘC phải kiểm tra trường `checked_at` / `completed_at`:
     - Nếu bản ghi sinh từ trước ngày 26/08: Đó là tàn dư của cơ chế cũ trước khi User sửa rule.
     - Kiểm tra `COUNT(video_id) HAVING COUNT(DISTINCT folder) > 1`: Nếu ra 0 tức là hệ thống hash Perceptual Hash / MD5 vẫn hoạt động hoàn hảo, không có clip nào bị duplicate trên farm.
