# TikTok Niche Desync Root Cause & Safe 3-5 Hashtag Architecture (2026-09-27)

## 1. Hiện Tượng & Nguyên Nhân Gốc Lệch Niche Toàn Farm (Root Cause)
- **Hiện tượng**: Nhiều tài khoản đăng video bị sai lệch hoàn toàn hashtag so với nội dung thực tế (ví dụ: video gái xinh selfie/hát hò gắn `#game #choigame`, video Tin 3 phút phóng sự/xã hội gắn `#nhac #singing #amnhac`, clip hài Xuân Hinh gắn `#gym #tapgym`).
- **Nguyên nhân cốt lõi**:
  1. Khi crawl video nguồn về `D:\video goc\<N>`, hệ thống nạp niche vào `D:\CodexRuntime\tiktok-video\state.db` (bảng `folders`) bằng cách gán tuần tự số folder theo chỉ mục các dòng trong `data/niches_pool.txt` (Folder 33 = dòng 33 `gym`, Folder 49 = dòng 49 `game`, Folder 75 = dòng 75 `trangdiem`), hoàn toàn không kiểm tra nội dung thực tế hay tên kênh.
  2. Bảng `videos` trong `state.db` thực tế đã lưu đúng `uploader` và `source_channel` (ví dụ: `Xuân Hinh Official`, `Tin 3 Phút`, `Mê Xe`, `Hoàng Minh - Phân Tích Sự Kiện`), nhưng bảng `folders` lại mang niche sai.
  3. Script sync (`sync_all_tik_keywords.py`) đồng bộ niche sai từ `state.db` vào cột `Keyword Video` và `Hashtag Pool` của các file `Tik1.xlsx` .. `Tik8.xlsx`.
  4. Tool upload (`run_post.py` -> `hashtag_selector.py`) bốc ngẫu nhiên từ `Hashtag Pool` của workbook, dẫn đến toàn bộ 3-5 hashtag trong bài đăng đều sai chủ đề.

## 2. Chiến Lược 2 Tầng Xử Lý Triệt Để

### Tầng 1: Kiến Trúc Hashtag An Toàn (Lớp Khiên Bảo Hiểm - Safe 3-5 Shield)
- **Quy tắc ngẫu nhiên 3-5 tag**:
  - Tỷ lệ số lượng: 3 tag (15%), 4 tag (55%), 5 tag (30%).
  - **Phân bổ tỷ trọng nội dung**:
    + **2 - 4 Hashtag quốc dân / Viral**: Bốc ngẫu nhiên từ pool chung (`#fyp #xuhuong #videohay #viral #trending #tiktokvietnam`).
    + **Tối đa 1 Hashtag Niche**: Chỉ bốc duy nhất 1 tag đại diện cho niche của kênh (ví dụ: `#tintuc` hoặc `#haihuoc` hoặc `#cahat`).
  - **Lợi ích**: Kể cả khi folder nguồn bị gán nhầm niche, video vẫn có 3-4 tag viral gánh chủ đạo, 1 tag niche lệch không làm biến dạng ngữ cảnh bài viết. Thuật toán AI TikTok 2026 (Visual recognition + Audio + OCR) vẫn quét và phân phối đúng tệp.

### Tầng 2: Chuẩn Hóa Niche Tận Gốc (Data Remapping)
- **Cấm chờ đến khi cắn đề xuất mới sửa**: Không chấp nhận để tài khoản đăng sai niche kéo dài.
- **Tận dụng metadata có sẵn trong DB**:
  - Đọc cột `uploader` và `source_channel` trong bảng `videos` của `state.db` để re-map lại niche tự động (ví dụ: uploader chứa `Hài`, `Xuân Hinh` -> `haihuoc`; chứa `Xe`, `Oto` -> `oto`; chứa `Tin`, `News`, `VTC` -> `tintuc`).
  - Với các folder chưa có metadata rõ ràng: trích xuất 1 frame đầu chạy WinRT OCR nhận diện watermark / text nhận diện.
  - Cập nhật lại cột `niche` trong `state.db` và chạy `sync_all_tik_keywords.py` để cập nhật lại toàn bộ `Tik1..Tik8.xlsx`.
