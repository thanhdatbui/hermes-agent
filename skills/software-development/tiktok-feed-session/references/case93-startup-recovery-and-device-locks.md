# Case 93: Startup Splash Recovery, Launcher Focus, and Safe Device-Lock Handling

## 1. Kiểm Tra Trạng Thái Device-Lock An Toàn (Cấm Quét Đĩa / Grep)
- **Vị trí file lock:** `~/.codex/device-locks/machine_<N>.lock.json` và `~/.codex/device-locks/serial_<SERIAL>.lock.json`.
- **Quy tắc an toàn:**
  1. Kiểm tra trực tiếp đường dẫn file lock `~/.codex/device-locks/machine_<N>.lock.json`. Tuyệt đối **CẤM** dùng `grep -rn`, `os.walk`, hoặc `glob` quét cả thư mục/ổ đĩa.
  2. Nếu có PID đang giữ lock (`status: running`, `owner_active: true`), kiểm tra log runtime `D:/Taadaa/runtime/kibe/live/...` của máy đó để theo dõi tiến độ.
  3. Đợi tiến trình hoàn thành và file lock tự giải phóng (file biến mất) rồi mới chạy canary.

## 2. Lệnh Chạy Canary 1 Máy Nhanh (Recovery Test Swipes = 2)
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```

## 3. Pitfalls Về Startup & Launcher Recovery (Case 93)
- **`_capture_splash_slow_retry`**: Luôn định nghĩa `tiktok_pkgs = {expected_package, "com.ss.android.ugc.trill", "com.zhiliaoapp.musically", "com.ss.android.ugc.aweme"}` bao gồm package mục tiêu và các biến thể quốc tế/nội địa.
- **`_capture_baseline_with_startup_retry`**: Gán cờ `baseline_recovered_by_prepare_tiktok = True` khi launcher recovery thành công để bảo toàn metadata trạng thái cho các assertion downstream.
- **`_is_launcher_focus_loss`**: Khi kiểm tra `popup_type == "packageinstaller_permission"`, chỉ bỏ qua khi popup **chưa** được dismiss (`and not row.get("popup_dismissed")`), cho phép kích hoạt launcher recovery bình thường sau khi bấm từ chối quyền.
- **`_profile_identity_from_xml`**: Không lọc bỏ các phần tử placeholder ("Thêm tên") trong vòng lặp tìm `display_name_element` khi tìm anchor parent container, giúp `_find_sticky_profile_header` phát hiện chính xác nút mũi tên switcher (`:id/s8k`).
