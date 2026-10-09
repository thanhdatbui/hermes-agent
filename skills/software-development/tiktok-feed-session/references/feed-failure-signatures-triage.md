# TikTok Feed Session Failure Signatures & Triage

## Overview & Diagnostics
Khi tỷ lệ lỗi feed session tăng cao (> 20-30% trên toàn farm), sử dụng `run_manifest.json` và machine logs tại `D:\Taadaa\runtime\kibe\live\<date>\<batch>\<session_id>\` để phân loại theo 5 nhóm signature chính.

---

## 5 Failure Signatures & Root Causes

### 1. Following Tab Empty / Retry Marker False Positive (`manual-needed:network`)
- **Triệu chứng trong log:**
  - `step`: `switch_following_<N>_navigation_confirm`
  - `reason`: `network/error/retry marker detected`
  - `status`: `manual-needed:network`
  - Máy đã lướt được 3-8 video FYP bình thường, nhưng dừng ngay sau khi chuyển sang tab Following.
- **Nguyên nhân gốc rễ:**
  - Nick mới follow ít tài khoản hoặc các kênh vừa follow chưa đăng video mới. TikTok hiển thị giao diện trống hoặc gợi ý thử lại ("Chưa có video", "Tải lại").
  - Detector của runner nhầm thông báo này là lỗi mạng nghiêm trọng và dừng toàn bộ session.
- **Giải pháp / Rule:**
  - Soft-fallback: Khi tab Following trống hoặc gặp retry marker, ghi nhận degraded và lập tức điều hướng quay lại tab "Dành cho bạn" (FYP) để hoàn thành quota swipes thay vì abort session.

### 2. Kẹt Profile Người Lạ Do Gợi Ý Bạn Bè / Follow Back (`navigation target profile not found in XML`)
- **Triệu chứng trong log:**
  - `step`: `feed-session-smoke/tap_profile` -> `find_navigation_target`
  - `error`: `navigation target profile not found in XML`
  - `total_swipes_completed`: 0
- **Hiện trường XML / UI:**
  - Xuất hiện các nút: `"Follow lại"`, `"Nhắn tin"`, `"Bạn bè với ..."` hoặc `"Được ... follow"`.
  - Không có thanh navigation bar đáy hoặc nút `"Hồ sơ"` chính chủ.
- **Nguyên nhân gốc rễ:**
  - Popup đề xuất ("Follow lại", "Gợi ý kết bạn") bị chạm nhầm hoặc tự điều hướng vào trang profile cá nhân của tài khoản khác.
  - Runner tìm nút "Hồ sơ" để preflight nhưng ở trang người lạ không có nút này.
- **Giải pháp / Rule:**
  - Bổ sung handler nhận diện Profile người lạ (Foreign Profile Guard): Nếu phát hiện nút "Follow lại" / "Nhắn tin" và không có "Sửa hồ sơ" / "Thêm tiểu sử", lập tức bấm `KEYCODE_BACK` (tối đa 2 lần) để trở về Home feed trước khi điều hướng.

### 3. Profile Screen Vision & XML Drift (`known TikTok screen` / `screenshot_xml_mismatch`)
- **Triệu chứng trong log:**
  - `xml_detected_screen: profile`
  - `image_selected_top_tab: following` (confidence ~0.89)
  - `screenshot_xml_mismatch: true`
  - Kết quả dừng: `safety_reason: known TikTok screen`, `status: manual-needed`, 0 swipes.
- **Nguyên nhân gốc rễ:**
  - Thiết bị đã đứng ở Profile chính chủ (có đầy đủ username, Đã follow, Follower, Thích).
  - Tuy nhiên, detector thị giác (image classifier) nhận diện sai các đường line/tab trang trí trên header Profile thành underline của tab "Following", ghi đè kết quả XML và rơi vào vòng lặp retap vô hạn.
- **Giải pháp / Rule:**
  - XML Ground Truth Precedence: Khi XML đã xác nhận chắc chắn màn hình Profile (`profile_selected: true` hoặc có `@username` + nút "Sửa hồ sơ" / "Thêm tiểu sử"), cấm image top-tab classifier ghi đè thành `following`.

### 4. Switcher Thiếu Nick & Reconcile Timeout (`account-switcher-missing-expected`)
- **Triệu chứng trong log:**
  - `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`
  - Theo sau bởi `finish_reconcile ... timed out after 300.0 seconds`.
- **Nguyên nhân gốc rễ:**
  - Nick chỉ định trong workbook chưa được đăng nhập trên máy thật.
  - Subprocess `reconcile_tiktok_accounts.py` chạy quá 300s mà không thoát hoặc bị kẹt dialog OTP.
- **Giải pháp / Rule:**
  - Kiểm tra đối chiếu trước giữa workbook `taikhoan_run_safe.xlsx` và nick thực tế trên switcher.

### 5. Rớt Mạng Wi-Fi & ADB Disconnect Cục Bộ
- **Triệu chứng:**
  - `required router proxy is unreachable ... dumpsys connectivity: Wi-Fi not connected`
  - `device offline or ADB/USB disconnected: adb.exe: device '...' not found`
- **Xử lý:**
  - Không sửa code. Cần can thiệp vật lý vào Wi-Fi AP hoặc hub USB/cáp nối máy thật.
