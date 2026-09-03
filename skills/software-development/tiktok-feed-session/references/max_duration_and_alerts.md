# Troubleshooting: Max Duration Exceeded & Telegram Farm Alerts

## 1. Lỗi `run plan max_duration_seconds exceeded before ...`
- **Hiện tượng:** Bot Farm Alerts báo lỗi `run plan max_duration_seconds exceeded before ...` trên hàng loạt máy.
- **Nguyên nhân:** Khi chạy batch `multi-machine-feed-session`, mỗi worker có một deadline được gán từ `DEFAULT_DEVICE_TIMEOUT_SECONDS` (trước đây là 900s, sau được nâng lên 1500s). Khi thiết bị xử lý nhiều popup, gặp mạng lag hoặc watch delay dài khiến tổng thời gian vượt quá mốc timeout của máy, hàm `ensure_run_plan_deadline` trong `python_runner/core/deadline.py` sẽ ngắt worker an toàn để không chạy vô tận.
- **Khắc phục:** Đảm bảo `DEFAULT_DEVICE_TIMEOUT_SECONDS = 1500.0` trong `python_runner/flows/multi_machine_feed_session.py`.

## 2. Ý nghĩa thông báo Telegram `🟡 GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`
- Đây là nội dung mẫu mặc định của bot gửi tin nhắn vào nhóm Telegram Farm Alerts khi có máy dừng vì lỗi, nhằm mục đích giữ nguyên hiện trạng màn hình app để tra cứu.
- **Không phải** là lệnh lock máy vật lý hay chiếm quyền máy thật.
