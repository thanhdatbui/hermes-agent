# Camera Creation Screen Recovery during Feed Session

## 1. Triệu chứng & Nguyên nhân
- **Hiện trường:** Đang chạy script lướt feed nuôi acc (`tiktok-luot nuoi acc`), màn hình đột ngột dừng tại giao diện quay Camera / Tạo nội dung của TikTok (nút `✕` ở góc trái trên, `Thêm âm thanh`, chế độ `15s`, `60s`, `10 phút`, `Văn bản`, nút chụp/quay đỏ ở giữa).
- **Nguyên nhân gốc rễ:**
  1. **Horizontal Swipe Drift (Cử chỉ vuốt ngang):** Trên tab Cho Bạn (For You / FYP), TikTok mặc định hỗ trợ cử chỉ vuốt ngang từ trái sang phải (Swipe Right) để mở nhanh Camera/Story. Khi script vuốt lướt feed (`_perform_feed_swipe`), nếu tọa độ x bị lệch/chạm mép trái hoặc cử chỉ có độ nghiêng ngang, TikTok sẽ chuyển sang Camera.
  2. **Bottom Bar Tap Drift:** Nút `+` (Tạo/Camera) nằm chính giữa thanh điều hướng đáy `[432, 1794][648, 1920]`. Khi điều hướng giữa Trang chủ và Hồ sơ, nếu UI phản hồi chậm hoặc tọa độ fallback chạm vào khu vực giữa, Camera sẽ bị mở.

## 2. Nhận diện & Cơ chế Tự Phục Hồi (Auto-Recovery)
- **Detector:** `_detect_camera_creation` trong `python_runner/flows/benign_popup_registry.py`:
  - Nhận diện các marker đặc trưng: `shortvideo`, `record_layout`, các shoot mode `15s`, `60s`, `10 phút`, `10m`, `văn bản`, `mẫu`, kết hợp camera control `lật`, `hẹn giờ`, `tốc độ`, `bộ lọc`, `thêm âm thanh`.
  - Negative guard: Loại trừ màn hình Hồ sơ (profile markers) và thanh điều hướng For You để tránh nhận diện sai.
- **Dismisser:** `_dismiss_camera_creation` / `dismiss_camera_creation_screen`:
  - Tìm và bấm nút đóng `✕` (resource-id `com.ss.android.ugc.trill:id/close` hoặc content-desc `Đóng`).
  - Fallback: Gọi `send_device_back_key(ctx)` (`adb shell input keyevent 4`) để đóng Camera quay lại feed For You.

## 3. Lệnh Kiểm Chứng & Canary Test
- **Unit test chuyên biệt:**
  ```bash
  pytest python_runner/tests/test_camera_dismissal_and_profile_nav.py
  ```
- **Canary test thực tế máy kẹt:**
  ```powershell
  powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row <R> -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
  ```
