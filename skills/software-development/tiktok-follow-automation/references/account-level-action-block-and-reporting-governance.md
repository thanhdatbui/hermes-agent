# Quy Tắc Điều Phối: Account-Level Action Block & Kiến Trúc Báo Cáo Farm

## 1. Bản Chất Nhả Follow: Account-Level Action Restriction (Cấm Ngộ Nhận Né Anchor)

### Hiện tượng & Phản biện thực tế
- Khi bot chạy Mode 2 và bị nhả ở bước follow Anchor lớn: Một số nhận định sai lầm cho rằng "do Anchor quá lớn nên bị nhả, cần né Anchor để bấm nick con trong Following".
- **Thực tế chứng minh (Log M27, M42):** Khi nick đã bị TikTok nhả ở Anchor, nếu bỏ qua Anchor để vào tab Following bấm nick con, **nick con cũng bị nhả ngay ở lượt đầu tiên (100% fail)**!

### Bản chất kỹ thuật
1. **Khóa tính năng ở cấp tài khoản (Account-Level Block):**
   - Khi một tài khoản bị đưa vào diện nghi vấn (Cold account velocity spike, nick non Following < 10 nhưng đột ngột search và follow dồn dập), máy chủ TikTok kích hoạt cờ hạn chế quyền Follow.
   - Khi đã dính cờ này: Bấm Anchor nhả, bấm nick con nhả, bấm ngoài feed nhả, bấm tay trên điện thoại cũng nhả (Optimistic UI -> Backend silent drop/rollback).
   - Anchor chỉ là "vật tế thần đầu tiên" vì kịch bản dẫn bot vào trang của Anchor trước.
2. **Kỷ luật vận hành chuẩn:**
   - **CẤM TUYỆT ĐỐI viết code né tránh Anchor** cho nick non.
   - **Chưa đủ khỏe thì CẤM follow:** Nick non (Following < 10, chưa đủ 30 ngày hoặc < 10 video) bắt buộc khóa cứng ở chế độ **Dưỡng sinh thuần (Feed Session Only)** để lướt video, giữ dwell time, thả tim nuôi trust.
   - **Đã đủ điều kiện thì chạy luồng chuẩn:** Xem video -> Like -> Follow Anchor -> Xác minh Path B -> Mở tab Following cày nick con.

---

## 2. Kiến Trúc Báo Cáo: Telegram Control Tower vs DB Telemetry

### Nguyên tắc cốt lõi: Không biến Telegram thành Database
Đối với Farm quy mô lớn (160 -> 500+ máy), tuyệt đối không xả danh sách chi tiết hàng chục máy hay hàng trăm UID con vào chat Telegram gây trôi thông tin khẩn cấp.

### Phân định 2 tầng:
1. **Telegram = Alert + Control Tower:**
   - Chỉ báo cáo **KPI cấp cao và Exceptions**: Ca nào, tổng máy OK/Fail/Offline, % thành công, số lượt follow thật (đối soát web).
   - Khi kết quả bình thường / khớp 100%: Chỉ gửi duy nhất **1 dòng tóm tắt cấp cao** (ví dụ: `+ Đối soát TikTok Web (+124 Following thật - Khớp 100% so với script báo)`), không dump danh sách máy.
   - Khi có bất thường (Anomaly/Exception): Chỉ liệt kê **đúng những máy có vấn đề** (máy bị lệch số liệu, máy dính nhả/cúp cầu dao IP, máy mất kết nối USB/AP).
   - Đính kèm đường dẫn drill-down tới Dashboard cổng 1905.
2. **SQLite DB & Dashboard (`:1905`) = Telemetry & Forensics:**
   - Ghi nhận đầy đủ chi tiết sâu vào CSDL: `session_account_actions`, `daily_account_actions`, `snapshots`.
   - Lưu trữ danh sách từng UID con, thời gian dừng (dwell time), lịch sử fail streak, quá trình thăng tiến trần (`proven_safe_ceiling`, `active_ceiling`), chi tiết cúp cầu dao IP.
   - Truy vấn theo nhu cầu (Query on demand) khi cần điều tra bệnh án của từng máy.
