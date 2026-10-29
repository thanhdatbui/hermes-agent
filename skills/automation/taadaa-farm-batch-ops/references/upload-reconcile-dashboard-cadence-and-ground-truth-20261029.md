# Đối Soát Video Upload vs TikTok Dashboard: Bẫy Lệch Nhịp Snapshot Cadence (2026-10-29)

## 1. Hiện Tượng & Nghi Vấn Thường Gặp
- **Triệu chứng**: Khi kiểm tra Dashboard web (`http://127.0.0.1:1905/`), nhiều tài khoản vừa chạy upload xong trong ngày nhưng số lượng video trên Dashboard lại hiển thị thấp hơn so với `shift_upload_history.json` (ví dụ: Ledger ghi nhận đã đăng video 15, nhưng Dashboard vẫn báo 14).
- **Phản ứng sai lầm**:
  - Vội vàng kết luận script upload bị lỗi hoặc upload thất bại ngầm.
  - Vội vàng nghi ngờ web TikTok bị lỗi cache / chặn.
  - Chuyển cơ chế verify video ngay trong lúc upload sang cào web/dashboard trực tiếp.

---

## 2. Bản Chất Nguyên Nhân Gốc Rễ (Root Cause)
1. **Lệch pha chu kỳ Snapshot (Snapshot Cadence Mismatch):**
   - Cronjob cào toàn farm (`cron_tiktok_daily_tracker.py`) chạy vào **10:00 sáng hàng ngày**.
   - Các ca upload diễn ra theo lịch (ví dụ Ca 5 chạy lúc **18:00 - 20:00 tối**).
   - Đến tối, dữ liệu trên Dashboard vẫn là snapshot của lúc **10:03 sáng** (chưa tới chu kỳ cào tiếp theo của sáng hôm sau).
2. **Ground Truth thực tế:**
   - Khi kiểm tra Live trực tiếp trên web TikTok (`https://www.tiktok.com/@<username>`) bằng Mobile User-Agent vào ban đêm, số video đã nhảy đủ (ví dụ: video 15 đã xuất hiện).
   - Do đó, cả script upload và TikTok đều chuẩn xác, chỉ là dữ liệu Dashboard đang phản ánh trạng thái trước giờ upload.

---

## 3. Quy Trình Đối Soát Chuẩn O(1) Bằng Script
Sử dụng công cụ đối soát chéo độc lập:
`D:/Taadaa/tools/audit_upload_dashboard_reconcile.py`

```bash
# Đối soát toàn bộ ca của một ngày cụ thể (mặc định hôm nay):
python D:/Taadaa/tools/audit_upload_dashboard_reconcile.py --date 2026-10-29 --row 5
```

### Nguyên tắc diễn giải kết quả:
- **`timestamp` của snapshot trên Dashboard < `timestamp` upload trong ca:** Sự chênh lệch 1 video là **hoàn toàn bình thường** (chờ lượt cào snapshot tiếp theo).
- **`timestamp` của snapshot > `timestamp` upload + 2 giờ mà số video vẫn thấp hơn:** Kích hoạt nghi vấn kiểm duyệt/ẩn video (Shadowban hoặc Vi phạm chính sách).
- **Tuyệt đối không dùng web scraper cào trực tiếp làm realtime verify trong upload flow** vì:
  1. Gây bẫy SlardarWAF / cháy 67 proxy khi hàng chục máy cùng cào.
  2. Bị độ trễ CDN Public Web TikTok (thường trễ 15m - 2h so với in-app).
