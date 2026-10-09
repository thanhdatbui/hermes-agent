# Case UI-87: Chuẩn hóa Abstraction Xem Video Tự Nhiên & Telemetry Độc Lập Cho Mode 1 (10-20%) và Mode 2 (30-35%)

## 1. Bối cảnh & Yêu cầu vận hành
- Trước đây, hành vi xem video tự nhiên (`_maybe_watch_profile_video`) chỉ được triển khai thử nghiệm trên Mode 2, và không có cơ chế cuộn tìm video khi profile bị che bởi Bio/Header, dẫn đến việc bỏ qua trong im lặng (silent pass) và không có telemetry theo dõi.
- User yêu cầu:
  1. Module 2: Bấm follow trên list -> vào Profile verify (Path B) -> nếu bị nhả thoát luôn -> nếu đã follow, cuộn tìm video đàng hoàng, xem lướt và thả tim tự nhiên.
  2. Anchor: Mở video anchor xem, like, follow trên video -> back ra Profile vuốt reload kiểm tra nhả -> bị nhả ngắt phiên lập tức.
  3. Module 1: Mở rộng cơ chế xem video tự nhiên sau khi follow thành công với tỷ lệ kiểm soát 10% – 20%.
  4. Báo cáo Telegram Watchdog (`feed_session_watchdog.py`): Phải tách bạch riêng biệt số lượt xem video của Module 2 và Module 1, cấm gộp chung gây hiểu lầm.

## 2. Kiến trúc Clean Abstraction dùng chung (`_maybe_watch_profile_video`)
Để tránh trùng lặp code và vi phạm DRY giữa `mode1_search_follow.py` và `mode2_follow_followers.py`, abstraction được đặt tại `mode2_follow_followers.py` và xuất khẩu cho Mode 1:

```python
def _maybe_watch_profile_video(
    engine,
    profile_nodes: list[dict],
    uid: str = "",
    *,
    chance_range: tuple[float, float] = (0.30, 0.35),
    dwell_range: tuple[float, float] = (12.0, 20.0),
    mode_tag: str = "MODE2",
    env_override: str = "MODE2_FORCE_WATCH_CHANCE",
) -> None:
    ...
```

### Các thông số chuẩn hóa:
- **Mode 2 (Following list):** `chance_range=(0.30, 0.35)`, `mode_tag="MODE2"`, `env_override="MODE2_FORCE_WATCH_CHANCE"`.
- **Mode 1 (Search follow):** `chance_range=(0.10, 0.20)`, `mode_tag="MODE1"`, `env_override="MODE1_FORCE_WATCH_CHANCE"`.
- **Scroll Recovery:** Nếu chưa thấy cover video (do Bio dài/Header chiếm màn hình), tự động cuộn nhẹ 1-2 lần (`adapter.swipe(540, 1400, 540, 800, 400)`), dump lại UI để tìm `video_covers`.
- **Dwell Time:** Ngẫu nhiên 12.0s – 20.0s qua tham số hóa `dwell_range=(12.0, 20.0)` với phép tính `round(random.uniform(*dwell_range), 1)` (nâng từ mức cũ 6.0s – 10.0s vì sau khi trừ 2s chụp screencap và buffer mạng 4G/proxy, video phát thực tế chỉ còn 3-5s gây cảm giác quá nhanh, thiếu tự nhiên). Cho phép caller linh hoạt override khoảng dwell time theo từng kịch bản mà không sửa mã nguồn hàm lõi.
- **Tương tác Like:** Xác suất 30% bấm Like video (nhận diện selector `Thích`, `Like`, `like_icon`).
- **Screencap Evidence:** Lưu riêng biệt `mode1_video_watching_evidence.png` và `mode2_video_watching_evidence.png`.
- **Mock Safety:** Tránh can thiệp khi chạy FakeAdapter trong unit test (`"FakeAdapter" in type(adapter).__name__`).

## 3. Định dạng Telemetry Báo Cáo Ca Chạy (Telegram Sink)
Trong `feed_session_watchdog.py`, tổng hợp độc lập và in rõ ràng:

```text
• Follow chéo (50 lượt follow) [Module 2 (Anchor): 46 (Xem video: 15) | Module 1 (Bù): 4 (Xem video: 1)]:
```
- Hiển thị trực tiếp số lượt xem video ngay bên trong ngoặc module tương ứng.
- Không gộp chung, giúp User và Coordinator đối soát trực tiếp hiệu quả tạo entropy tài khoản của từng module.

## 4. Bài học & Pitfalls khi kiểm thử Closeout Gate
- **Pitfall 1 (Pytest Timeout trên test cũ):** Khi file test tích hợp cũ (`test_mode1_search_follow.py`) có nhiều mock time phức tạp và chạy lâu (>30s), việc thêm test mới vào file đó dễ làm trigger `PYTEST_TIMEOUT` của `closeout_gate.py`.
  - **Khắc phục:** Tạo file test chuyên biệt riêng (ví dụ `test_mode1_watch_video.py`) tập trung test đúng abstraction, env fallback, like interaction và telemetry aggregation để hoàn thành trong < 2 giây.
- **Pitfall 2 (Mock Engine arithmetic comparison):** Trong `run_mode1`, phép tính budget `min(state.session_budget(...), state.budget_remaining())` sẽ ném `TypeError` nếu mock trả về MagicMock thay vì int. Luôn mock rõ ràng `session_budget.return_value = 0` và `budget_remaining.return_value = 0` trong test telemetry.
- **Pitfall 3 (Kiểm thử Dwell Range & Telemetry Record):** Khi viết unit test cho `dwell_range=(12.0, 20.0)` và telemetry record trong `test_mode1_watch_video.py`, mock `random.uniform` để bắt danh sách args `(a, b)` truyền vào và kiểm tra `record["dwell"]` khớp với công thức round của khoảng dwell time.
