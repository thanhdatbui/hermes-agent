# TikTok Account Tracker & Farm Monitoring Playbook

## Mục đích
Thu thập chỉ số công khai của danh sách tài khoản TikTok trên Phone Farm (UID, follower, following, like, video count, trạng thái LIVE/DIE, phát hiện cắn đề xuất) mà không cần login, không đụng thiết bị Android S7, không tốn quota API.

## Kiến trúc & Quy chuẩn
1. **Source of Truth tài khoản:**
   - Đọc từ `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` (các cột `May`, `Device ID`, `ID`, `Video Đã Đăng`).
2. **Cơ chế Scraping:**
   - Dùng User-Agent mobile Safari (`iPhone; CPU iPhone OS 16_6 like Mac OS X`).
   - Parse JSON trong thẻ `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">`.
3. **Bẫy SlardarWAF & Proxy Pool:**
   - BẮT BUỘC phân biệt giữa nick `NOT_FOUND` thật (`statusCode == 10221`) và WAF rate-limit (`SlardarWAF` không có hydration data).
   - Nạp dải proxy chuẩn của farm từ `D:/Taadaa/Tiktok-video/proxy_pool_67.txt` (dải 67 proxy của user). CẤM quét gom linh tinh các file cũ/cổng nội bộ gây đội số lượng.
   - Khi gặp WAF/timeout: retry xoay vòng qua proxy khác trong pool (tối đa 2 lần).
4. **Lưu trữ & Xuất báo cáo:**
   - Snapshot lưu SQLite tại `D:/Taadaa/data/tiktok_tracker.db`.
   - Báo cáo xuất ra file Excel OneDrive: `D:/OneDrive/TaadaaData/kibe/tiktok_stats_farm.xlsx`.
   - Cron job tự động 07:00 sáng hàng ngày (`daily-tiktok-farm-tracker`).
5. **Kỷ luật giao diện & Server hạ tầng:**
   - TUYỆT ĐỐI KHÔNG chèn route hay merge vào `server.py` của MikroTik (`:2310`).
   - Ưu tiên cập nhật file Excel trên OneDrive hoặc gửi bản tin qua Telegram.
