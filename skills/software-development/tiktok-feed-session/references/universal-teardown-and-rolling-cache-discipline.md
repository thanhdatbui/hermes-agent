# Kỷ Luật Teardown Về Home & Dọn Cache Cuốn Chiếu Toàn Farm

## 1. Nguyên Tắc Cốt Lõi: Đóng App -> Về Home -> Nhả Lock (Cả Success Lẫn Fail)
- **Xóa bỏ triệt để tàn dư anti-pattern "Preserve Blocker Screen":**
  - Trước đây khi gặp lỗi, script cố tình không đóng app để "giữ hiện trường".
  - Với farm 80-160 máy chạy liên tục 4 ca/ngày, việc này gây lỗi dây chuyền: ca sau vào gặp ngay app treo, popup cũ, hoặc màn hình trắng dẫn tới `focused package unavailable` / `focus lost to launcher`.
  - **Kỷ luật mới:** Mọi hiện trường lỗi bắt buộc số hóa 100% bằng cách chụp screencap + dump UI XML lưu vào artifact directory. Ngay sau đó:
    1. Đóng sạch recent apps hoặc `am force-stop` package.
    2. Gửi lệnh về màn hình chính Launcher (`input keyevent 3` / `KEYCODE_HOME`).
    3. Nhả `DeviceLock` ngay lập tức (`lease.release()`).
- **Triển khai cụ thể trên các repo:**
  - `multi_machine_feed_session.py`: Bắt buộc bật `child_config["_cleanup_close_all_on_error"] = True`.
  - `run_follow.py`: Luôn chạy `close_all_recent_apps()` và nhả lock trong `finally:` bất kể fail hay success.
  - `state_machine.py` (Upload): Khi failure/manual-review, sau khi dọn recent apps về Home phải gọi `self._release_leases()`, CẤM gọi `_hold_leases_for_recovery()` giữ lock `handoff` 60 phút.
  - `tiktok_reg_live_email_v1.py`: Khối `finally:` bắt buộc bọc `shell(device_id, "am", "force-stop", ...)` và `shell(device_id, "input", "keyevent", "3")` trước khi nhả lock.

## 2. Kỷ Luật Cron Dọn Cache Cuốn Chiếu (`cron_clear_tiktok_cache.py`)
- **Lỗi schedule cần tránh:**
  - Không bao giờ đặt `*/10 1,2,3,4 * * *` (mỗi 10 phút từ 1h-4h sáng). Schedule này sẽ bắn phá 40 workers liên tục force-stop TikTok giữa lúc các máy đang chạy lướt feed Ca 4.
  - Lịch chuẩn: `*/15 3,4,5 * * *` (mỗi 15 phút từ 03:00 đến 05:45 sáng, sau khi Ca 4 đêm hoàn tất).
- **Cơ chế chạy cuốn chiếu & Quản lý State 1 lần/ngày:**
  - Sử dụng file state `post_night_clear_cache_state.json` theo dõi mảng `cleared_machines` theo ngày `today_str`.
  - Sang ngày mới: tự động reset danh sách.
  - Mỗi tick cron: chỉ lọc `target_machines` đối với các máy online **chưa nằm trong `cleared_machines`**.
  - Khi toàn bộ máy online đã hoàn tất: script thoát im lặng (`return 0`).
  - Máy nào dọn xong thành công: append ngay vào `cleared_machines` và lưu state.
- **Kỷ luật Khóa DeviceLock & CẤM PHÁ LOCK:**
  - Trước khi chạm vào thiết bị, BẮT BUỘC acquire `DeviceLock(serial=serial, machine=str(m), project="clear-cache", bypass_proxy_readiness=True)`.
  - NẾU gặp `DeviceLockUnavailable` hoặc `DeviceLockNeedsUserDecision` (máy đang có script khác giữ lock):
    - **TUYỆT ĐỐI CẤM** gửi lệnh ADB can thiệp.
    - **CẤM** `am force-stop` và **CẤM** `input keyevent KEYCODE_HOME`.
    - Bỏ qua an toàn, ghi nhận trạng thái `[LOCKED]` và chờ lượt cron kế tiếp máy rảnh nhả lock thì dọn.
  - Khi acquire lock thành công: Chạy dọn dẹp trong khối `with lock:`, đảm bảo `force-stop` + phím Home trong `finally:` của lock trước khi nhả lock.
