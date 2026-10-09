# Natural Feed Follow: Watch Time Gate Chống Nhả Follow & Báo Cáo Watchdog Ca Nuôi Acc

## 1. Bản chất & Phân tách 2 Cơ chế Follow trong Farm

Hệ thống nuôi TikTok của farm có 2 luồng follow hoàn toàn độc lập về ngữ nghĩa và thời điểm:

| Đặc tính | Follow Chéo / Follow Hook (`_run_follow_hook`) | Follow Tự Nhiên Khi Lướt Feed (`_maybe_follow_video`) |
| :--- | :--- | :--- |
| **Vị trí code** | `multi_machine_feed_session.py` (cuối ca lướt) | `feed_swipe_smoke.py` (trong khi quẹt For You) |
| **Cơ chế thực thi** | Gọi process con `follow_runner.run_follow` (Mode 1 / Mode 2) | ADB tap trực tiếp nút Follow trên view For You / Deep Inspect |
| **Cổng chặn (Gate)** | Cổng cứng: `video_count >= 10` (chặn nick clone lộ cụm) | Watch Time Gate (ngâm xem video ≥ 8-12s) |
| **Mục đích** | Bơm follow chéo có kiểm soát giữa các dàn máy | Tạo hành vi người dùng thật, mồi thuật toán FYP theo niche |

---

## 2. Hiện tượng Silent Action Block (Nhả Follow) & Watch Time Gate

### Nguyên nhân bị TikTok âm thầm hủy (nhả) follow:
- Khi nick đang lướt Feed, nếu script quẹt trúng video và tap vào nút Follow chỉ sau 1–2 giây mà không có thời gian dừng xem (dwell time):
  - AI của TikTok nhận diện đây là hành vi tự động hóa (botting).
  - TikTok không báo lỗi trên màn hình mà **âm thầm hủy lượt follow trên server** (sau vài giây nút Follow đỏ lại, hoặc số Following không tăng).
- Nick mới dưới 14 ngày tuổi hoặc tài khoản chưa tích lũy đủ watch-time trên thiết bị càng dễ bị dính cơ chế này.

### Giải pháp kỹ thuật: Watch Time Gate
Trước khi tap nút Follow trong `_maybe_follow_video`:
```python
if random.randint(1, 100) > int(follow_rate_percent):
    return False

# Watch Time Gate: Ngâm video tối thiểu 8-12s trước khi tương tác follow
# Đảm bảo TikTok ghi nhận watch-time đủ độ trust, tránh hành vi bot bấm vội bị server revert
watch_dwell_s = random.uniform(8.0, 12.0)
time.sleep(watch_dwell_s)

xml_text = _capture_xml_text(ctx, "follow_video")
```
- **Hiệu quả:** Server TikTok ghi nhận nick đã nán lại xem hết hoặc gần hết video trước khi quyết định follow ➔ Action được lưu trữ vĩnh viễn trên server, không bị revert.
- **Tần suất tự nhiên:** Tỷ lệ follow tự nhiên giữ ở mức 5% trên For You và 20% khi Deep Inspect. Trung bình 1 session 18–22 video chỉ follow khoảng 1–2 nick, tích lũy tự nhiên qua nhiều ngày.

---

## 3. Cập nhật Báo Cáo Watchdog Nuôi Acc (`feed_session_watchdog.py`)

Để người vận hành theo dõi rõ rệt hiệu quả của Follow Tự Nhiên mà không bị nhầm lẫn với Follow Chéo:

1. **Trích xuất dữ liệu:**
   - Trong `parse_run_all`, đọc `follow_counts` (`for-you`, `following`, `friends`) từ `summary.txt` của từng máy.
   - Gộp vào payload máy thông qua `merge_machine_result` với key `natural_follows`.
2. **Tổng hợp chỉ số theo Ca:**
   - `tot_fy_nat_follows`: Tổng follow tự nhiên trên tab Đề xuất (For You).
   - `tot_fr_nat_follows`: Tổng follow tự nhiên trên tab Bạn bè (Friends).
   - `tot_nat_follows`: Tổng số lượt follow tự nhiên toàn ca.
   - `tot_nat_follow_rate`: Tỷ lệ follow tự nhiên trên tổng số video quẹt (`tot_nat_follows / tot_swipes * 100%`).
3. **Format hiển thị trong Báo cáo Telegram:**
   Nằm ngay dưới dòng thống kê Thả tim / Đọc comment:
   ```text
   🏢 【FARM KIBE】
   • Tổng máy xử lý: 80 máy
   • Lướt Feed:
     + Success (78): M1, M2...
     + Fail (2): M30, M54
     + Trống slot/chưa có nick (0): Không có
     + Thả tim: 142 tim / 1,440 video (9.9%) [Đề xuất: 120 (10.1%) | Bạn bè: 22 (8.8%)]
     + Follow tự nhiên: 24 lượt / 1,440 video (1.7%) [Đề xuất: 20 | Bạn bè: 4]
     + Đọc comment: 310 lượt / 1,440 video (21.5%)
   ```
   Tách bạch hoàn toàn với mục `• Follow chéo (X lượt follow) [Module 2 (Anchor): Y | Module 1 (Bù): Z]` ở phía dưới.
