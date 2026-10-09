# Quy Chuẩn Lịch Điều Phối Macro & Follow Chéo Nội Bộ (Farm Lifecycle)

## 1. Định Luật Bảo Toàn Follow Chéo Nội Bộ (Zero-Sum Graph Law)
- **Bản chất toán học:** Dù farm có 30 máy hay 160 máy (1.280 nick), tổng số lượt follow phát ra bằng tổng số lượt follow nhận về trong mạng lưới khép kín.
- **Tốc độ thực tế của 1 nick đơn lẻ:**
  - 1 nick chỉ gửi đi an toàn khoảng 250 - 350 follow/tháng (10-15 follow/phiên, 2 phiên/ngày chạy).
  - Để 1 nick nhận đủ 1.000 follower từ các nick khác trong dàn, bắt buộc cần:
    $$\frac{1.000 \text{ follow cần nhận}}{250-350 \text{ follow/tháng}} \approx \mathbf{3 \text{ đến } 4 \text{ THÁNG}}.$$
  - **Lưu ý sống còn:** Số lượng máy nhiều chỉ giải quyết bài toán **quy mô mẻ (batch concurrency)** — tức là sau 3-4 tháng thu hoạch 1 mẻ hàng trăm/hàng nghìn nick cùng lúc. Không thể đốt cháy giai đoạn của 1 nick đơn lẻ nếu chỉ dùng follow chéo nội bộ.

## 2. Chu Kỳ Xoay Ca 6 Ngày (4 Acc/Ngày + Ngày Dưỡng Sinh Rửa Trust)
Để tối ưu hóa nhịp nuôi, mỗi ngày hệ thống chỉ kích hoạt đúng 4 tài khoản trên mỗi thiết bị (thay vì dồn dập toàn bộ 8 acc), kết hợp ngày dưỡng sinh nghỉ follow để rửa trust score và phá vỡ chữ ký bot:

- **Công thức tính mốc:**
  ```python
  day_cycle = (now.date() - date(2026, 9, 1)).days % 6
  ```
- **Phân bổ 2 nhóm tài khoản theo 4 Ca trong ngày:**
  - **Nhóm Lẻ (Row 1, 3, 5, 7):** Ca 1 (6h/8h) chạy Row 1; Ca 2 (12h/14h) chạy Row 3; Ca 3 (18h/20h) chạy Row 5; Ca 4 (0h/1h30) chạy Row 7.
  - **Nhóm Chẵn (Row 2, 4, 6, 8):** Ca 1 (6h/8h) chạy Row 2; Ca 2 (12h/14h) chạy Row 4; Ca 3 (18h/20h) chạy Row 6; Ca 4 (0h/1h30) chạy Row 8.

- **Lịch trình chi tiết 6 ngày trong chu kỳ:**
  - **Day 0:** Nhóm Lẻ (Row 1, 3, 5, 7) — **Cày Follow + Up video** (`is_rest_day = False`).
  - **Day 1:** Nhóm Chẵn (Row 2, 4, 6, 8) — **Cày Follow + Up video** (`is_rest_day = False`).
  - **Day 2:** Nhóm Lẻ (Row 1, 3, 5, 7) — **DƯỠNG SINH RỬA TRUST** (`is_rest_day = True`: Chỉ lướt feed giải trí, **TUYỆT ĐỐI 0 FOLLOW, 0 UP VIDEO**).
  - **Day 3:** Nhóm Chẵn (Row 2, 4, 6, 8) — **Cày Follow + Up video** (`is_rest_day = False`).
  - **Day 4:** Nhóm Lẻ (Row 1, 3, 5, 7) — **Cày Follow + Up video** (`is_rest_day = False`).
  - **Day 5:** Nhóm Chẵn (Row 2, 4, 6, 8) — **DƯỠNG SINH RỬA TRUST** (`is_rest_day = True`: Chỉ lướt feed giải trí, **TUYỆT ĐỐI 0 FOLLOW, 0 UP VIDEO**).

### Giá trị kỹ thuật của "Ngày Dưỡng Sinh" (Rest Day / Pure Feed):
- Mỗi nhóm acc chạy 2 ngày cày xen kẽ 1 ngày dưỡng sinh thuần túy, đảm bảo acc có thời gian xả điểm nghi vấn (anomaly score) và không bị tích tụ tần suất follow liên tục.
- Toàn farm luôn duy trì tải ổn định (mỗi ngày đúng 4 ca x 1 row/ca), không gây đột biến băng thông IP/Proxy.
- **Cơ chế kỹ thuật chặn Follow & Up ngày dưỡng sinh:**
  - `tiktok_runner.py`: Khi `is_rest_day == True`, không truyền flag `-AllowUploadHook` và set env `TAADAA_REST_DAY_NO_FOLLOW=1`.
  - `multi_machine_feed_session.py`: `_run_follow_hook()` kiểm tra env `TAADAA_REST_DAY_NO_FOLLOW == "1"`, lập tức bỏ qua an toàn với reason `"rest-day-follow-disabled-pure-feed"`.

## 3. Ngưỡng Budget Follow Chuẩn: 10 - 20 Follow / Phiên
- **Cấu hình chuẩn trong `tiktok-follow`:**
  - `budget_per_session_min`: **10**
  - `budget_per_session_max`: **20**
  - `budget_per_session`: **20**
  - `budget_per_day`: **40** (2 phiên follow/ngày cày $\times$ tối đa 20 follow/phiên = 40 follow/ngày).
- Khi acc vừa mãn hạn cooldown, runner vẫn giữ cơ chế khởi động nhẹ (warmup 3-5 follow) trước khi phục hồi về dải budget 10-20.

## 3. Giai Đoạn Nuôi Móng 10 Video (Foundation Gate)
- Acc mới tạo (0 - 30 ngày): CẤM vội vàng đi follow chéo.
- Bắt buộc ngâm nuôi, lướt feed tự nhiên và đăng đủ $\ge 10$ video (khung giờ vàng 9h, 16h, tối muộn).
- Sau khi acc đã có $\ge 10$ video và trust score vững chắc mới đưa vào chu kỳ follow 3 ngày.

## 4. Cơ Chế Tự Động Bật Lại Khi Hết Hạn Phạt Nhả (Auto-Unblock)
- Hệ thống đã tích hợp sẵn cơ chế kiểm tra `is_account_in_follow_cooldown()` dựa trên timestamp UTC `cooldown_until_at` và `cooldown_until_date`.
- **Khi mãn hạn cooldown:**
  1. `FollowState` tự động reset `follow_failed = False` và dọn sạch các trường timestamp hết hạn.
  2. `feed_swipe_smoke.py` tự động mở lại follow video ở tab Đề xuất (For You) theo tỷ lệ `_deep_follow_rate` (5%).
  3. Popup gợi ý kết nối (`follow_back_suggestion`): Tự động chuyển từ hành vi né phạt (bấm "Không quan tâm") sang hành vi nhận kết nối (bấm "Follow lại").
