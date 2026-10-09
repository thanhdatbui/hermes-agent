# Bẫy False Alarm Văng Nick Trên TikTok 47.x, Bung Switcher Chuẩn & Quy Trình Nạp Split Dex v47.0.3 (2026-09-21)

## 1. Bẫy False Alarm "Văng Nick / Mất Session" Trên TikTok 47.0.3

### 1.1. Hiện tượng & Sai lầm thường gặp
- Sau khi nâng cấp hoặc khởi chạy TikTok 47.0.3, nếu Agent kiểm tra danh sách tài khoản bằng cách:
  - Mở Menu hồ sơ (icon 3 gạch `954, 96`) -> Chọn "Cài đặt và quyền riêng tư" -> Cuộn xuống đáy tìm "Chuyển đổi tài khoản".
- **BẪY**: Trên TikTok 47.0.3, mục này ở đáy menu Cài đặt có thể bị co gọn (collapsed), hoặc chỉ render 2 tài khoản đầu tiên nếu chưa cuộn sâu/chưa bung toàn diện.
- **Hậu quả**: Agent vội vàng kết luận *"Máy chỉ còn 2 nick, các nick khác đã bị văng!"*, gây hoang mang và hiểu nhầm nghiêm trọng cho User (trong khi thực tế 7-8 nick vẫn còn nguyên vẹn 100% trong SQLite SharedPreferences).

### 1.2. Quy chuẩn kiểm tra Account Switcher Chuẩn Xác 100%
- BẮT BUỘC mở trực tiếp bảng **Account Switcher Bottom Sheet** từ màn hình Hồ sơ:
  1. Vào tab Hồ sơ: `input tap 972 1857`.
  2. Tap thẳng vào Header/Display name của nick hiện tại: tọa độ `(500, 290)` (hoặc khoảng `Y = 250..300` giữa màn hình).
  3. Màn hình sẽ bung lên Bottom Sheet chuẩn:
     - Resource ID: `com.ss.android.ugc.trill:id/g1z` (Trang tính dưới cùng).
     - Title: `com.ss.android.ugc.trill:id/psy` (`text='Chuyển đổi tài khoản'`).
     - Từng tài khoản hiển thị với container `rid='ls_'` và text username `rid='ndk'`.
     - Số lượng badge thông báo: `rid='p05'`.
     - Nút thêm tài khoản: `text='Thêm tài khoản'`.
- **Kỷ luật bất biến**: CẤM TUYỆT ĐỐI kết luận máy mất tài khoản khi chưa dump XML từ đúng Bottom Sheet `rid='psy' text='Chuyển đổi tài khoản'` mở từ Profile header.

---

## 2. Quy Trình Nạp TikTok 47.0.3 Split Dex An Toàn Trên Android 8 (Samsung S7)

### 2.1. Bản chất kiến trúc APK TikTok 47.x
- TikTok 47.0.3 phân rã mã nguồn thành:
  - 4 split cơ bản: `base.apk` (68MB), `split_config.arm64_v8a.apk` (52MB), `split_config.vi.apk`, `split_config.xxhdpi.apk`.
  - **1 split bytecode cốt lõi**: `split_df_a_dex.apk` (83.8MB, chứa toàn bộ class logic của app).
- Nếu chỉ cài 4 split cơ bản qua `adb install-multiple`: App cài thành công (`versionName=47.0.3`) nhưng crash ngay khi mở:
  `java.lang.ClassNotFoundException: Didn't find class "X.1OEX"`.

### 2.2. Kỹ thuật cài đặt tránh nghẽn Bus USB Hub 20 cổng
- **Cấm**: Chạy `adb install-multiple` đồng thời 10-20 máy với file 84MB. Tốc độ qua USB Hub S7 bị chia nhỏ còn <0.3 MB/s, gây timeout 180s/300s, đứt kết nối hoặc lỗi `Failure [INSTALL_PARSE_FAILED_UNEXPECTED_EXCEPTION]`.
- **Quy trình chuẩn 5 bước**:
  ```python
  # 1. Push file split dex vào thiết bị (timeout 450s, concurrency <= 3 workers)
  adb -s <serial> push split_df_a_dex.apk /data/local/tmp/split_df_a_dex.apk

  # 2. Tạo package installer session liên kết với package hiện tại
  sid=$(adb -s <serial> shell "pm install-create -r -d -p com.ss.android.ugc.trill" | cut -d'[' -f2 | cut -d']' -f1)

  # 3. Ghi file dex từ local tmp vào session
  adb -s <serial> shell "pm install-write -S <dex_size_bytes> $sid split_df_a_dex.apk /data/local/tmp/split_df_a_dex.apk"

  # 4. Commit session
  adb -s <serial> shell "pm install-commit $sid"

  # 5. Dọn dẹp & Khóa auto-update
  adb -s <serial> shell "rm -f /data/local/tmp/split_df_a_dex.apk"
  adb -s <serial> shell "settings put global auto_update_apps 0"
  ```
- **Xác minh sau cài đặt**:
  `adb -s <serial> shell "dumpsys package com.ss.android.ugc.trill | grep splits="`
  Bắt buộc phải có `df_a_dex` trong danh sách: `splits=[base, config.arm64_v8a, config.vi, config.xxhdpi, df_a_dex]`.

---

## 3. Kỷ Luật Xử Lý Thông Báo Tiến Trình Nền (Background Process Injections)

### 3.1. Bối cảnh
- Khi một tiến trình nền cũ kết thúc (ví dụ cronjob login hay batch script chạy từ trước), hệ thống Hermes sẽ tự động chèn thông báo `[IMPORTANT: Background process proc_... completed normally]` vào cuộc trò chuyện.
- Nếu User phản hồi một dấu hỏi `?` hoặc câu hỏi ngắn, User thường đang thắc mắc: *"Đây là cái gì thế?"* hoặc tiếp tục câu chuyện chính đang làm dở.

### 3.2. Quy tắc phản ứng của Agent
- **CẤM**: Tự động chuyển hướng toàn bộ session sang phân tích lỗi của tiến trình nền không liên quan (ví dụ lao vào mổ xẻ lỗi login của Máy 1/Máy 32 khi session đang làm việc về update TikTok / follow).
- **ĐÚNG**:
  1. Kiểm tra lại context phiên làm việc: Nhiệm vụ hiện tại là gì? User có yêu cầu sửa/chạy tác vụ đó không?
  2. Báo cáo ngắn gọn, minh bạch: *"Đây là tiến trình nền [tên script] chạy từ trước vừa kết thúc và hệ thống tự đẩy log vào chat, không ảnh hưởng đến tác vụ hiện tại của anh."*
  3. Tiếp tục giữ vững trọng tâm công việc mà User đang chỉ đạo.
