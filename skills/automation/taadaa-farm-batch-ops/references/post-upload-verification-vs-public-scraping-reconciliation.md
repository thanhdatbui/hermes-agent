# Post-Upload Verification vs Public Scraping Reconciliation

## 1. Bản chất hai tầng xác minh video TikTok Farm

### Tầng 1: In-Session Verification (Thời gian thực ngay khi máy upload)
- **Mục đích**: Xác nhận việc submit video lên thiết bị có được app TikTok chấp nhận hay không trước khi xóa file đệm và cập nhật workbook.
- **Cơ chế tại chỗ**:
  1. Xác nhận nút "Đăng" (Post) biến mất và progress bar hoàn tất.
  2. Bắt playback surface của video vừa post (`_verify_current_post_surface`).
- **Hạn chế của việc đếm Profile Tile (`_verify_profile_post_increment` / `_count_profile_video_tiles_across_grid`)**:
  - **Processing Latency**: TikTok xử lý nén và kiểm duyệt video ngầm từ 15s - 45s trước khi xuất hiện trên grid trang cá nhân. Timeout 15s (3 lần x 5s) rất dễ gây false-negative (tưởng chưa đăng).
  - **Tải ADB / Hardware cũ (Samsung S7)**: Việc cuộn tới 6 lần, dump UI XML và crop screenshot perceptual hash tốn 25s - 40s/máy, dễ làm nghẽn socket ADB hoặc văng session.
  - **Deduplication rủi ro (`COMPAT-POST-VERIFY-005`)**: Khi grid có nhiều video (15-30+ clips), ghép viewport có thể lệch hoặc tính nhầm tile, dẫn đến việc `scan unreliable`.

### Tầng 2: Post-Session Audit (Đối soát sau ca)
- **Mục đích**: Kiểm tra video có thực sự hiển thị public, không bị vi phạm chính sách ngầm, shadowban hoặc kẹt duyệt.
- **Cơ chế**: Sử dụng dữ liệu cào public web (`D:/Taadaa/tools/tiktok_account_tracker.py` đọc thẻ `__UNIVERSAL_DATA_FOR_REHYDRATION__` và lưu SQLite `tiktok_tracker.db`).

## 2. Vì sao CẤM dùng Public Scraping trong In-Session Upload?
1. **Độ trễ CDN Cache (Cache Invalidation Lag)**:
   - TikTok Desktop/Mobile Web có cache từ 15 phút đến 1-2 tiếng so với app mobile. Vừa post xong mà gọi cào web ngay thì `videoCount` chắc chắn chưa nhảy số $\rightarrow$ báo fail 100%.
2. **Nguy cơ SlardarWAF & Cháy Proxy Pool**:
   - Dàn máy chạy 80 máy đồng loạt. Nếu mỗi máy upload xong đều gửi request cào web sẽ kích hoạt SlardarWAF, dẫn đến nghẽn và cháy dải 67 proxy.

## 3. Kiến trúc chuẩn khuyến nghị
- **Trong phiên upload**: Dựa vào In-app markers + playback surface để đóng tiến trình và trả lock máy.
- **Sau phiên (sau 1-2 giờ)**: Chạy cronjob đối soát giữa `shift_upload_history.json` (status=SUCCESS) và `tiktok_tracker.db` (videoCount tăng). Nếu lệch $\rightarrow$ gửi alert nghi vấn kiểm duyệt/shadowban.
