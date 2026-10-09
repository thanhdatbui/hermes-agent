# Finger Drift & Human Dwell Timing Patterns (TikTok Consumer Automation)

## 1. Natural Finger Drift (ADB Swipe Anti-Detection)
Hành vi vuốt của người thật không bao giờ có tọa độ X hoàn toàn thẳng đứng (`dx == 0`) hoặc thời gian cố định.
Để tránh bot detection khi swipe trên Android/TikTok:
- Thêm độ trễ / lệch tọa độ ngang ngẫu nhiên: `drift_x = start_x + random.randint(-15, 12)`.
- Ngẫu nhiên hóa thời lượng vuốt: `random.randint(420, 490)` ms thay vì cố định `450` ms.

Ví dụ triển khai ADB swipe:
```python
drift_x = start_x + random.randint(-15, 12)
duration_str = str(random.randint(420, 490))
self._adb.shell(
    [
        "input", "swipe",
        str(start_x), str(start_y),
        str(drift_x), str(end_y),
        duration_str,
    ],
    timeout=10,
    check=False,
)
```

## 2. Human Dwell Time Trước Nút Đăng (Post Button)
Người thật luôn dừng lại quan sát 1-3 giây trước khi ấn nút Đăng/Post cuối cùng sau khi hoàn thiện caption/cài đặt.
- Thêm `time.sleep(random.uniform(1.8, 3.5))` ngay trước thao tác tap Post sau khi ghi nhận post intent.

## 3. Quy Tắc Khi Chỉnh Sửa State Machine
- Luôn kiểm tra `import random` ở phần đầu file (`state_machine.py` hoặc bất kỳ module nào) trước khi sử dụng `random.randint` / `random.uniform` để tránh `NameError: name 'random' is not defined`.
