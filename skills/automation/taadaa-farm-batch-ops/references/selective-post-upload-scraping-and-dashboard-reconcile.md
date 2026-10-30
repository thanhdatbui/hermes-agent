# Selective Post-Upload Scraping & Dashboard Reconcile Protocol (2026-10-30)

## 1. Vấn Đề Thực Tế & Nhận Định Sai Lệch Thường Gặp
- **Hiện tượng**: User kiểm tra Dashboard web (`port 1905`) thấy số video của các nick vừa đăng ca tối bị lệch (ví dụ Ledger báo 15 mà Dashboard chỉ hiển thị 14).
- **Phản xạ sai lầm của Agent / User**:
  1. Nghi ngờ script upload bị lỗi logic đếm video hoặc báo khống thành công.
  2. Nghi ngờ crawler web bị lỗi hoặc TikTok chặn không nhảy số.
  3. Đề xuất cào "All Farm" (toàn bộ 1.268 nick) sau ca để cập nhật.
- **Bằng chứng & Sự thật hiện trường**:
  1. Script upload đã hoàn thành và đăng video thật 100% lên kênh (`report.json` và live web TikTok trả về đúng video mới).
  2. Dashboard hiển thị lệch đơn giản là vì **chu kỳ cào All Farm (`cron_tiktok_daily_tracker.py`) chỉ chạy 1 lần/ngày lúc 10:00 sáng**, trong khi ca upload diễn ra vào 18h-20h tối.
  3. Cào web TikTok có **độ trễ CDN cache từ 30 đến 60 phút** sau khi app bấm Đăng, do đó TUYỆT ĐỐI KHÔNG DÙNG CÀO WEB để verify real-time ngay trong luồng upload (sẽ làm nghẽn máy hoặc dính SlardarWAF).

---

## 2. Kiến Trúc Xác Minh 2 Tầng Chuẩn Hóa
1. **Tầng 1 (In-App Verification - Thời gian thực):**
   - Xác nhận nút *Đăng* biến mất + thanh upload 100%.
   - Bắt màn hình Playback / Promotion của video vừa đăng (`_verify_current_post_surface`).
   - Ghi nhận `status: success` và `video_number` vào `shift_upload_history.json`.
   - Nhả máy ngay cho ca tiếp theo (không bắt ADB chờ đợi).
2. **Tầng 2 (Post-Session Audit - Chọn lọc sau ca):**
   - Không cào All Farm 1.268 nick (gây lãng phí proxy và rủi ro WAF).
   - Chỉ cào **chọn lọc 60 - 120 nick đã upload success** của ca đó (`post_upload_scraper.py`).
   - Thời điểm chạy tối ưu: Sau ca upload 45 phút (`45 10,16,20 * * *`).

---

## 3. Công Cụ & Lệnh Vận Hành Canonical
- **Script cào chọn lọc & audit:** `D:/Taadaa/tools/post_upload_scraper.py`
  - Chạy thủ công đối soát ca:
    ```bash
    python D:/Taadaa/tools/post_upload_scraper.py --date 2026-10-29 --row 5
    ```
  - Tự động cào qua pool 67 proxy và cập nhật snapshot mới vào `D:/Taadaa/data/tiktok_tracker.db` trong ~15 giây.
  - Dashboard web tự động bắt snapshot mới nhất qua API `/api/data` không cần khởi động lại.
- **Cronjob định kỳ:** `post-upload-auto-audit-sync` (script `cron_post_upload_sync.py`, schedule `45 10,16,20 * * *`).

---

## 4. Kỷ Luật Lịch Ca Farm & Silent Watchdog Contract
- **Không có ca upload nửa đêm:** Farm chỉ chạy upload ban ngày/chiều/tối (mốc cào đối soát tương ứng là 10:45, 16:45, 20:45); CẤM TUYỆT ĐỐI cài đặt mốc 0h (`0`) vào cron schedule vì farm không chạy ca đêm.
- **Empty Shift Schema Parity & Silent Watchdog:**
  - Khi không có nick nào upload thành công trong ca (`accounts == []`), `post_upload_scraper.py` bắt buộc trả về payload chuẩn hóa đầy đủ keys (`date`, `row`, `total: 0`, `confirmed_match: 0`, `delayed_or_anomaly: 0`, `anomalies: []`) để tránh crash `KeyError: 'date'`.
  - Khi `total == 0`: Script bắt buộc thoát êm với exit code `0` và giữ `stdout` hoàn toàn rỗng để cronjob `no_agent=True` giữ trạng thái SILENT, tuyệt đối không gửi báo cáo rác lên Telegram.
