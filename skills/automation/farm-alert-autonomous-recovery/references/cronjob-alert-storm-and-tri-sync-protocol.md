# Giao Thức Chống Bão Alert Cron & Quy Trình Đồng Bộ Đa Điểm (Tri-Sync)

## 1. Cơ Chế Sinh Ra Bão Alert (Alert Storm Root Causes)
Khi một Cronjob Watchdog hoặc Pipeline định kỳ gặp lỗi chưa được xử lý (như lỗi cú pháp NameError, runtime crash):
- **Hiệu ứng Double-Fire:** Script tự bắt ngoại lệ ở khối ngoài cùng `if __name__ == '__main__':` rồi gọi `send_farm_script_alert()` bắn trực tiếp 1 tin nhắn Telegram vào nhóm Farm Alerts. Ngay sau đó script ném lại lỗi (`raise`) làm exit code != 0, khiến Hermes Cron Scheduler (`no_agent: true` với `deliver: telegram:...`) bắt stderr và tự động bắn thêm 1 tin nhắn failure nữa. Kết quả: 2 tin nhắn cảnh báo cho đúng 1 lần crash.
- **Khuếch đại theo nhịp Cron:** Cronjob chạy định kỳ mỗi 5 đến 15 phút (ví dụ: `*/15 3,4,5 * * *` = 12 lần/ca). Cứ mỗi nhịp chạy, 2 tin nhắn lại được bắn ra -> Telegram nhận 8–24 tin nhắn lặp lại liên tục trong 1 buổi sáng, gây ức chế nghiêm trọng cho người dùng.
- **Thiếu Cooldown cấp Framework:** Hàm gửi alert không lưu vết timestamp lần gửi gần nhất cho cùng cặp (script_name, error_reason).

## 2. Giải Pháp Chuẩn Hóa Triệt Tiêu Bão Alert

### A. Cooldown 1 giờ tại Framework (automation-core/src/automation_core/alerts.py)
- Mọi hàm `send_farm_script_alert()` bắt buộc có bộ đệm Cooldown tối thiểu 1 giờ (3600s).
- Định danh lỗi bằng mã băm MD5 của `f"{script_name}:{error_reason}"`.
- Sử dụng file tạm trong `farm_alerts_cooldown/` kèm kỹ thuật ghi nguyên tử (`atomic replace` từ file `.tmp` sang `.json`) để triệt tiêu triệt để race condition khi nhiều tiến trình hoặc worker chạy song song.
- Log telemetry rõ ràng: `log.info("[COOLDOWN_SUPPRESSED] Script alert for '%s' suppressed within 3600s cooldown", script_name)`.
- Cho phép bypass an toàn khi chạy Unit Test (`FORCE_TEST_ALERT_DISPATCH=1`) hoặc qua cờ môi trường khẩn cấp (`FARM_ALERT_DISABLE_COOLDOWN=1`).

### B. Debounce theo ngày tại Tầng Script Watchdog
Trong khối `if __name__ == "__main__":` của mọi script watchdog:
```python
if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        today_str = datetime.now().strftime("%Y-%m-%d")
        err_msg = f"Lỗi script nghiêm trọng: {exc}"
        state_data = load_state(today_str)
        if state_data.get("last_script_err") != err_msg:
            _send_script_alert(err_msg)
            state_data["last_script_err"] = err_msg
            save_state(state_data)
        raise
```

## 3. Quy Trình Đồng Bộ Đa Điểm Script Cron (Tri-Sync Protocol)
Mỗi script cron chạy trong farm phân tán tồn tại ở 3 vị trí khác nhau:
1. **Repo Chuẩn (Codebase Source of Truth):** `D:/Taadaa/Hermes/deploy/hermes-home/scripts/<script>.py`
2. **Runtime Scheduler (Nơi Cron Scheduler thực thi):** `%LOCALAPPDATA%/hermes/scripts/<script>.py` (Hermes Cron Scheduler luôn thực thi file nằm trong thư mục này).
3. **OneDrive Shared (Đồng bộ đa máy Kibe/Admin):** `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/<script>.py`

### Nguyên Tắc Đồng Bộ Bắt Buộc:
- Khi sửa bất kỳ script cron hoặc watchdog nào, **CẤM CHỈ SỬA 1 NƠI**.
- BẮT BUỘC sao chép đồng nhất cả 3 vị trí trước khi nghiệm thu.
- Viết unit test xác thực tự động kiểm tra sha256/nội dung giữa 3 vị trí (như `test_sync_to_runtime_and_shared` trong `test_cron_clear_tiktok_cache.py`).
- Trigger chạy thử ngay bằng `cronjob action='run', job_id='...'` để xác nhận `last_status: ok` và `execution_success: true` trên môi trường runtime thực tế.
