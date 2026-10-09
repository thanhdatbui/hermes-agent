# Teardown: Luôn Force-Stop App và Về HOME Khi Hoàn Tất Hoặc Gặp Lỗi

## 1. Vấn Đề (Problem Statement)
Trên Phone Farm Android (Taadaa Phone Farm), khi một tác vụ tự động kết thúc (dù thành công hay crash/exception), nếu ứng dụng (TikTok, Gmail, Google Play Services...) còn đang mở ở foreground:
1. Gây tiêu tốn tài nguyên thiết bị (RAM/CPU nóng máy, pin yếu trên dòng Samsung S7/Note cũ).
2. Khi tác vụ tiếp theo hoặc cron job tiếp theo (ví dụ feed session, check live, follow) chạy, màn hình không ở trạng thái chuẩn (HOME hoặc app launch state), dễ dẫn đến lệch UI dump XML, click sai tọa độ hoặc kẹt pop-up.
3. Rò rỉ trạng thái giữa các phiên làm việc của từng slot/tài khoản.

## 2. Quy Tắc Bắt Buộc (Mandatory Contract)
Mọi script chạy consumer hoặc runner trên device (như `gmail_reg_v10.py`, `run_capture_phase_b.py`, v.v.) **BẮT BUỘC** phải đặt teardown đóng app và đưa máy về HOME bên trong khối `finally:` ngay trước khi giải phóng lock (`device_lock.finish(...)` hoặc `lease.finish(...)`).

### Cấu trúc chuẩn:
```python
finally:
    try:
        # 1. Force-stop các package liên quan đến phiên chạy
        shell(device, "am", "force-stop", TARGET_PACKAGE)
        # hoặc qua ADB wrapper:
        # adapter.adb.shell(["am", "force-stop", cfg.tiktok_package], check=False)

        # 2. Đưa thiết bị về màn hình chính HOME (keyevent 3)
        shell(device, "input", "keyevent", "3")
        # hoặc:
        # adapter.adb.shell(["input", "keyevent", "3"], check=False)
    except Exception:
        pass  # Không để lỗi teardown chặn việc giải phóng lease/device_lock
    device_lock.finish(succeeded=goal_completed)
```

## 3. Lưu Ý Triển Khai
- Luôn bọc các lệnh teardown UI/app trong `try ... except Exception: pass` để nếu ADB ngắt kết nối đột ngột hoặc lệnh shell lỗi, luồng giải phóng lock (`finish()`) vẫn được thực thi đầy đủ.
- Keyevent `3` là mã phím `KEYCODE_HOME` tiêu chuẩn của Android.
