# Farm Scheduling & Cooldown Recovery Rules (Cập nhật 2026-09-15)

## 1. Giải mã mô hình Phone Farm quy mô lớn (Case ông Khoa 160 máy)
- **Quy tắc cứng:** Phải đăng đủ >= 10 video mới được bắt đầu đi follow. Chưa đủ thì 100% chỉ lướt feed nuôi gốc.
- **Phép tính vòng đời thật:**
  - 1 nick 1 tháng đi follow được ~250 lượt.
  - Follow chéo nội bộ giữa toàn bộ dàn: Để đạt mốc 1.000 follow, bắt buộc mất **đúng 4 tháng** (1000 / 250 = 4).
  - Cộng thêm 30–40 ngày đầu nuôi gốc và up đủ 10 video mồi.
  - => **Tổng thời gian cho 1 lứa đạt chuẩn 1k follow an toàn tuyệt đối là 5 đến 5.5 tháng.**
- **Vì sao bên ổng nhả follow chỉ 2 ngày là được thả?**
  - Vì ổng áp dụng chu kỳ 4 ngày (1,3,5 -> 2,4,6 -> 7,8 -> Nghỉ 100%). Mỗi slot được nghỉ 3 ngày liên tiếp (72h).
  - Có 1 ngày toàn farm hoàn toàn không đụng vào nút follow, chỉ lướt feed giải trí.
  - Khi chớm bị nhả follow: dừng ngay lập tức trong phiên (fail-fast), chỉ lướt nuôi bù => án phạt chỉ ở mức Tier 1, sau 48h là tự động hết cờ phạt.

## 2. Chu kỳ Vận Hành Vĩ Mô 6 Ngày Chuẩn Hóa của Taadaa Farm (4 acc/ngày)
- **Phân bổ 4 Ca/ngày:**
  - Ca 1 (Sáng): 06:00 - 12:00 (Session 1: 06:00 feed only, Session 2: 08:00 feed + up)
  - Ca 2 (Trưa/Chiều): 12:00 - 18:00 (Session 1: 12:00 feed only, Session 2: 14:00 feed + up)
  - Ca 3 (Tối): 18:00 - 00:00 (Session 1: 18:00 feed only, Session 2: 20:00 feed + up)
  - Ca 4 (Đêm): 00:00 - 06:00 (Session 1: 00:00 feed only, Session 2: 01:30 feed + up)
- **Bảng xoay tua 6 ngày (Epoch: 2026-09-01):**
  - **Ngày 0 & 4:** Row 1, 3, 5, 7 (Cày Follow + Up video) - `is_rest_day = False`
  - **Ngày 1 & 3:** Row 2, 4, 6, 8 (Cày Follow + Up video) - `is_rest_day = False`
  - **Ngày 2:** Row 1, 3, 5, 7 (DƯỠNG SINH RỬA TRUST - 100% CHỈ LƯỚT FEED, 0 FOLLOW, 0 UPLOAD) - `is_rest_day = True`
  - **Ngày 5:** Row 2, 4, 6, 8 (DƯỠNG SINH RỬA TRUST - 100% CHỈ LƯỚT FEED, 0 FOLLOW, 0 UPLOAD) - `is_rest_day = True`
- **Ý nghĩa sống còn của Ngày Nghỉ Dưỡng Sinh:**
  - Từng nick đơn lẻ: Được nghỉ hành vi follow trọn vẹn 48h (1 ngày không đụng app + 1 ngày chỉ vào app xem video giải trí).
  - Toàn farm: Lưu lượng ngày nào cũng phẳng (vẫn chạy 4 ca), không có ngày đột biến hay ngày về 0 (loại bỏ hoàn toàn Network Heartbeat Signature bị Sol cảnh báo).

## 3. Ngân Sách Follow & Tỷ Lệ Tương Tác Chuẩn (10–20 lượt/phiên)
- **Hạn mức phiên:**
  - `budget_per_session_min = 10`
  - `budget_per_session_max = 20`
  - `budget_per_session = 20`
  - `budget_per_day = 40` (cho 2 phiên)
- **Tỷ lệ:** 2 phiên follow / 1 lần đăng video (giữ bản chất creator).
- **Tốc độ:** Rút ngắn thời gian chạm mốc 1k follow xuống còn ~2.5 đến 3 tháng (thay vì 4 tháng của ông Khoa), trong khi độ an toàn vẫn giữ nguyên nhờ ngày nghỉ dưỡng sinh.

## 4. Cơ Chế State Machine Cooldown & Auto-Sync Expiry (Sol chấm 9.3/10)
- **Chuẩn hóa 100% UTC:** So sánh tuyệt đối qua `datetime.now(timezone.utc)` và `until_dt.astimezone(timezone.utc)`, triệt tiêu lỗi lệch ngày giữa giờ máy Windows local và server.
- **Auto-Sync Expiry (Diệt triệt để Zombie State):**
  - Khi `now_utc >= until_dt`: Hàm `is_account_in_follow_cooldown()` tự động dọn sạch `"follow_failed": False`, xóa các trường `cooldown_until_*`, reset `fail_streak = 0` và atomic replace file JSON (`.json.tmp` -> `os.replace`).
  - Hết hạn là tự động mở lại cờ follow khi lướt feed và chuyển sang bấm "Follow lại" ở popup.
- **Cách ly tuyệt đối cấp Row (Row Isolation):**
  - Bỏ hoàn toàn fallback `follow_state_{machine}.json`.
  - Chỉ match chính xác `follow_state_{machine}_row_{row}.json`. Máy bị 1 nick phạt thì 7 nick còn lại hoàn toàn không bị ảnh hưởng.
- **Quy tắc Clear Cache:**
  - Tuyệt đối không clear cache trước mỗi lần switch nick (lộ signature bot lặp lại).
  - Chỉ dọn dẹp cache cuốn chiếu / định kỳ qua cron cuối ngày để giải phóng dung lượng ổ cứng Samsung S7.
