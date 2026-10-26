# Case Study: Eliminating Blindspots in Taadaa Farm Cron Reports

## Context & Root Causes
Trong phiên làm việc đối soát các cron report trên farm, 4 điểm mù kỹ thuật đã được phát hiện và xử lý dứt điểm:

### 1. `cron_clear_tiktok_cache.py`: Mất kết nối ADB nhưng báo 100% thành công
- **Triệu chứng:** Khi có máy tuột cáp USB hoặc treo ADB, script chỉ quét qua các máy có trong `adb devices`, dẫn tới báo cáo ghi `Đã hoàn tất: 78/78 máy online`, hoàn toàn giấu nhẹm 2 máy bị rớt mạng.
- **Giải pháp:** Đối soát danh sách máy trong `Tik1.xlsx` với thiết bị online, lập mảng `c_offline` và in rõ `• Mất kết nối ADB (OFFLINE): 2 máy (M10, M30)`.

### 2. `cron_gmail_gpm_2fa_6h_report.py`: Acc văng cookie bị tính là "Đang ngâm"
- **Triệu chứng:** Phân loại chỉ kiểm tra `status == "success"`, toàn bộ các profile chưa xong bị tính vào `stats["soaking"]` ("Đang ngâm"). Các acc văng session Google (`NEEDS_LOGIN`) cũng bị tính là đang ngâm an toàn, tạo ảo giác acc đang chờ đủ ngày.
- **Giải pháp:** Xây dựng hàm `get_needs_login_profiles()` bóc tách riêng `NEEDS_LOGIN`, giữ nguyên tính tương thích cho `classify_profiles()`, đồng thời bổ sung khối cảnh báo `⚠️ Acc văng cookie (NEEDS_LOGIN): X profile` kèm danh sách email.

### 3. `cron_gpm_gmail_nurture_6h_report.py`: Trần nuôi báo 0/30 vì lệch key aggregator
- **Triệu chứng:** Runner nuôi acc ghi nhận timestamp `last_nurtured` cho từng profile nhưng không cập nhật đồng bộ key `_daily_stats["count"]`. Báo cáo đọc key này bị 0 dù thực tế đã nuôi đủ 30/30.
- **Giải pháp:** Viết hàm fallback `count_nurtured_today(state, now_ts)` duyệt qua mảng profile và đếm `date.fromtimestamp(last_nurtured) == today`.

### 4. `farm_render_download_watchdog.py`: Báo cáo dừng mà không rõ lý do
- **Triệu chứng:** Khi render dừng, chỉ in `Trạng thái render: ⚪ Đang dừng`.
- **Giải pháp:** Quét các slot Tik chưa đạt 80 folder (`ge45 < 80`) và kho video gốc chưa đạt 640 folder (`s45 < 640`), hiển thị số lượng thiếu hụt cụ thể và hướng dẫn khôi phục SSH Admin (`IP 192.168.110.119`).
