# Triage: Upload Video Verification vs TikTok Dashboard Crawler Desynchronization

## 1. Bản chất kiến trúc và Hiện tượng Lệch số Video
- **Hiện tượng**: User kiểm tra Dashboard web (`:1905`) thấy số video trên tài khoản (ví dụ `@chichi86830`, `@huynhim41`) thấp hơn 1 video so với ca upload vừa chạy thành công trong `shift_upload_history.json`.
- **Nguyên nhân cốt lõi**:
  1. **Lệch nhịp cào (Cadence Desynchronization)**: Cronjob cào All Farm (`cron_tiktok_daily_tracker.py`) chỉ chạy định kỳ lúc **10:00 sáng hàng ngày**. Trong khi đó, các ca upload diễn ra xuyên suốt trong ngày (Ca tối 18:00 - 20:00). Dữ liệu trên Dashboard là snapshot cũ lúc 10:03 sáng, trước thời điểm upload 8 tiếng.
  2. **Cào cuốn chiếu trong phiên Follow chỉ phục vụ nhóm máy tham gia phiên**: Cơ chế crawl trong luồng nuôi/follow chỉ quét các máy đang hoạt động trong batch đó, không quét các máy rảnh hoặc máy chỉ upload.
  3. **Độ trễ CDN Cache của Public Web TikTok**: Ngay cả khi vừa bấm Đăng thành công trên app điện thoại, CDN web của TikTok (`__UNIVERSAL_DATA_FOR_REHYDRATION__`) có độ trễ từ **15 phút đến 1-2 tiếng** mới cập nhật số video công khai ra ngoài web.

---

## 2. Quy tắc 2 Tầng: Upload Verification vs Post-Session Audit
- **CẤM TUYỆT ĐỐI**: Không đưa bước cào web vào làm chốt chặn xác minh thời gian thực (Real-time In-Session Verification) trong lúc máy đang upload.
  - Sẽ làm nghẽn máy (treo đợi CDN nhảy số 30m - 1h).
  - Gây nguy cơ kích hoạt SlardarWAF / cháy 67 proxy pool nếu hàng chục máy đồng loạt cào dồn dập.
- **MÔ HÌNH CHUẨN**:
  - **Tầng 1 (In-App Verification)**: Xác nhận hoàn tất upload trên máy điện thoại (nút Đăng biến mất, bắt màn hình playback/promotion `_verify_current_post_surface`). Ghi nhận ngay vào `shift_upload_history.json` và giải phóng máy cho ca tiếp theo.
  - **Tầng 2 (Post-Session Audit - Selective Crawl)**: Sau ca upload 45-60 phút, chỉ cào có chọn lọc **danh sách nick vừa upload thành công** trong ca (~60 - 120 nick) thay vì cào All Farm 1.268 nick. Cập nhật snapshot mới vào SQLite để Dashboard nhảy số ngay trong đêm.

---

## 3. Công cụ Đối soát Chéo O(1): `audit_upload_dashboard_reconcile.py`
- Đường dẫn canonical: `D:/Taadaa/tools/audit_upload_dashboard_reconcile.py`
- Lệnh chạy:
  ```bash
  python D:/Taadaa/tools/audit_upload_dashboard_reconcile.py --date <YYYY-MM-DD> --row <N>
  ```
- **Phân loại kết quả**:
  - `CONFIRMED_MATCH`: Số video trên Tracker DB >= Số video đã đăng trong Ledger.
  - `POSSIBLE_DELAY_OR_BLOCKED`: Video trên Tracker < Số video upload (nghi vấn trễ CDN nếu vừa đăng, hoặc video bị TikTok ẩn/shadowban/vi phạm nếu đã qua nhiều giờ).
  - `ACCOUNT_ABNORMAL`: Trạng thái nick không phải `LIVE` (bị khóa, checkpoint).
