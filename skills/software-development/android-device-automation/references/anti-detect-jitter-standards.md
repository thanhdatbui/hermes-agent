# Anti-detect Jitter Standards (UI Pixel, Timing & Scheduling)

## 1. UI Pixel Jitter (Tap & Swipe)

### Chuẩn tọa độ tap/swipe chống bot
Bot không có jitter sẽ tap vào đúng 1 pixel cố định (ví dụ `(540, 1788)`) hàng trăm lần -> TikTok / Google dễ dàng nhận diện automation qua thống kê phân phối touch.

- **Biến thiên tọa độ:** Offset ngẫu nhiên $\pm 1..6\text{px}$ quanh tâm element hoặc điểm bắt đầu/kết thúc swipe.
- **Boundary Clamp:** Bắt buộc có clamp tọa độ `max(lo, min(hi, val))` (ví dụ `[0, 2400]`) để không bị tràn viền màn hình hoặc văng tọa độ âm gây lỗi ADB.
- **Tránh "Donut Pattern":** Dùng `random.randint(min_offset, max_offset)` với `min_offset=0` hoặc `1` (thay vì `min_offset=4` làm rỗng tâm 0..3px).

```python
def _jitter(coord: int, min_offset: int = 1, max_offset: int = 6, lo: int = 0, hi: int = 2400) -> int:
    """Random offset ±min_offset..max_offset px có boundary clamp — chống detect automation."""
    offset = random.choice((-1, 1)) * random.randint(min_offset, max_offset)
    return max(lo, min(hi, coord + offset))
```

## 2. Timing Jitter (Pre-tap & Post-action delays)

- **Pre-tap delay:** Đệm ngẫu nhiên `time.sleep(random.uniform(0.05, 0.2))` trước khi gửi lệnh tap để mô phỏng độ trễ đặt ngón tay.
- **Post-action wait:** Nghỉ `time.sleep(random.uniform(1.2, 2.5))` sau thao tác tap/chuyển trang để tránh nhịp bấm máy móc (machine-gun tapping).
- **Feed watch time:** Đa dạng hóa thời gian xem video (ngẫu nhiên 3..12s, thỉnh thoảng 15..30s xem lâu).

## 3. Inter-Device Launch Stagger & Queueing (Khởi động phân tán trên Farm 80–200 máy)

Khi khởi động batch trên nhiều máy (ví dụ 80 máy cùng chạy feed session), tuyệt đối **không spawn đồng loạt** mà phải có cơ chế Stagger 2 lớp:
1. **Randomize Machine Order:** Đảo lộn thứ tự danh sách máy ngẫu nhiên (`--randomize-machine-order`), tránh tuần tự máy 1 -> 80 trên subnet mạng.
2. **Launch Stagger Delay (2s..8s):** Mỗi máy được delay ngẫu nhiên `2000ms..8000ms` (`--machine-start-stagger-ms 2000,8000`) trước khi spawn luồng/tiến trình của máy tiếp theo (`time.sleep(delay_ms / 1000.0)`).
   - Với 80 máy: Tổng khung thời gian dàn trải khởi động là `80 × avg(5s) = ~400s ≈ 6.7 phút`.
   - Kết hợp với thời gian cold-start TikTok (3–8s) -> Giảm **97%–99%** rủi ro xung đột / burst connection lên server mạng.

## 4. Scheduling Jitter (Cron & Macro Batch timing)

### Rủi ro gom cụm (Cluster Burst) trên farm lớn
Khi chạy trên 80–200 máy, việc đặt giờ chạy cố định (`row_slots = {1: '06:00', ...}`) hoặc dùng danh sách jitter rời rạc (`JITTER_MINUTES = (-20, -15, 15, 20)`) sẽ khiến các máy bị chia vào các cụm mốc phút rời rạc (ví dụ 05:40, 05:45, 06:15, 06:20) nếu không có Stagger tầng 2 bù đắp.

### Chuẩn thiết kế Scheduling Jitter
- **Dải liên tục (Continuous Distribution):** Dùng `random.randint(-20, 20)` hoặc phân phối chuẩn Gaussian (`random.gauss(0, sigma=10)`) để rải đều thời gian bắt đầu của các ca chạy qua toàn bộ khung giờ.
- **Deterministic Seed per Machine/Day:** Khởi tạo seed từ `machine_day_seed(day, machine, assignment_seed)` để đảm bảo mỗi máy mỗi ngày có một mốc thời gian riêng biệt, không bị trùng chéo giữa các máy và không bị lặp lại pattern cross-day.
