# Invariants Vận Hành Pipeline Nuôi Acc 25 Workers (Fail-Closed & Chống Timeout)

## 1. Giữ Nguyên 25 Workers Song Song Không Bị Nghẽn ADB Remote
- **Vấn đề:** 25 luồng trên cụm Admin (`192.168.110.119:5037`) nếu khởi động cùng thời điểm (0ms stagger) sẽ làm nghẽn socket ADB LAN, gây `adb command timed out` hàng loạt trên các lệnh `screencap` và `input swipe`.
- **Giải pháp bắt buộc:** Cấu hình mặc định `-MachineStartStaggerMs "2000,8000"` trong `run-feed-session.ps1` cho toàn bộ các lần chạy (kể cả Local lẫn Remote). Mỗi worker khởi động cách nhau 2-8s giúp rải đều tải trong ~1 phút mà vẫn đảm bảo 25 worker chạy song song mượt mà.

## 2. In-Flight Self-Relaunch Khi TikTok Văng Về Launcher
- **Hiện tượng:** Máy Samsung S7 khi bị crash/văng về `com.sec.android.app.launcher` (như M44, M269, M274) khiến `verify_tiktok_focus` fail và script dừng phiên báo `failed`.
- **Cơ chế phục hồi:** `device_prepare.py` khi phát hiện focus là launcher phải kích hoạt intent mở lại app TikTok tối đa 2 lần kèm xóa cache nhẹ trước khi kết luận thất bại.

## 3. Lọc Bỏ Slot Trống (Skipped-Empty Sanitization)
- **Vấn đề:** Các máy chưa nạp nick ở hàng tương ứng trong Excel (như M255 hàng 6) bị ném lỗi `config-error` và Watchdog tính nhầm vào danh sách Fail của ca.
- **Quy chuẩn:** Phải nhận diện trước các slot trống (`expected_username is None / empty`), gắn cờ `skipped-empty` hợp lệ ngay từ khâu nạp runner để không tính vào tỷ lệ lỗi của phiên nuôi.
