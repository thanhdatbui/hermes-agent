# Cron No-Agent Dual-Delivery Prevention & Alert Architecture

## 1. Bản chất sự cố Báo kép (Dual-Delivery Bug)
Khi một script watchdog (ví dụ: `post_evening_avatar_watchdog.py`, `watch_device_locks.py`, v.v.) tự phát thông báo và đồng thời chạy dưới Hermes Cron `no_agent: true`:
1. **Kênh 1 (Script Direct API)**: Script gọi trực tiếp HTTP Bot API Telegram (`send_farm_alert` / `sendMessage`) để gửi thông báo sạch dạng HTML/Markdown vào nhóm Farm Alert.
2. **Kênh 2 (Hermes Cron Scheduler)**: Nếu cấu hình Cronjob có `deliver: "telegram:<chat_id>"` và script in nội dung thông báo ra console (`print(report_msg)`), Hermes Cron xem mọi byte từ STDOUT là sản phẩm bàn giao, tự động forward thêm 1 lần nữa vào Telegram kèm header `Cronjob Response: <job_name> (job_id: ...)`.

Hậu quả: Nhóm Farm Alert nhận 2 tin nhắn y hệt nhau tại cùng một giây, gây khó chịu và rác kênh thông báo.

---

## 2. Quy chuẩn 2 Mô hình Cảnh báo (Two Valid Patterns - CẤM Pha trộn)

### Mô hình A: Script tự gửi trực tiếp (Self-Sending Script — Ưu tiên cho Farm Report phức tạp)
* **Khi nào dùng**: Các báo cáo tổng kết lớn, gộp toàn farm (Kibe + Admin), cần định dạng HTML phức tạp, có session stats hoặc đính kèm ảnh.
* **Quy tắc Cronjob**: BẮT BUỘC đặt `deliver: 'local'`.
  ```python
  cronjob(action='update', job_id='<id>', deliver='local')
  ```
* **Quy tắc STDOUT Script**: TUYỆT ĐỐI CẤM `print(report_msg)` ra STDOUT.
  - Khi gửi thành công: Giữ script im lặng (silent) hoặc chỉ in log debug ngắn gọn vào stderr:
    ```python
    try:
        send_farm_alert(report_msg)
    except Exception as e:
        sys.stderr.write(f"[WATCHDOG] send_farm_alert failed: {e}\n")
    ```
  - STDOUT sạch = Hermes Cron không lưu rác vào log cục bộ và không bao giờ rò rỉ tin nhắn thứ hai.

### Mô hình B: Script thuần Watchdog (Scheduler-Delivered Watchdog)
* **Khi nào dùng**: Các watchdog nhẹ (check disk, memory, ping gateway, device locks die count) chỉ cần bắn text ngắn khi có biến.
* **Quy tắc Cronjob**: Đặt `deliver: "telegram:<chat_id>"`, `no_agent: true`.
* **Quy tắc STDOUT Script**:
  - Script **CẤM** chứa mã gọi Telegram Bot API hay thư viện mạng gửi tin nhắn.
  - Khi hệ thống bình thường / không có lỗi: Script phải **hoàn toàn im lặng (0 byte stdout)**. Khi stdout rỗng, Hermes Cron sẽ không gửi tin nhắn nào.
  - Khi có sự cố / bất thường: Script `print(alert_text)` ra STDOUT để Hermes Cron tự forward tới người dùng.

---

## 3. Checklist nghiệm thu Watchdog / Cron Alert
Trước khi lưu hoặc sửa bất kỳ cronjob/watchdog nào trên Farm:
1. [ ] Kiểm tra mã nguồn script: Có hàm `send_farm_alert` hoặc gọi `api.telegram.org` không?
2. [ ] Nếu **CÓ**: Cấu hình cronjob `deliver` đã là `local` chưa? Đã xóa sạch các dòng `print(report_msg)` chưa?
3. [ ] Nếu **KHÔNG**: Script đã đảm bảo im lặng tuyệt đối (không print rác) khi không có sự cố chưa?
4. [ ] Chạy thử kiểm tra syntax: `python -m py_compile <script_path>` trước khi kết thúc phiên.
