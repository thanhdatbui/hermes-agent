# Recovery Màn Hình Subpage "Sửa Hồ Sơ" / "Thay Đổi Ảnh" (Edit Profile)

## 1. Bối cảnh & Hiện tượng lỗi
- Khi TikTok đang ở màn hình "Sửa hồ sơ" ("Edit Profile", "Thay đổi ảnh", "Thay đổi video", "Tên người dùng", "Tiểu sử") do phiên trước hoặc tác vụ chỉnh sửa profile để lại.
- Màn hình này không chứa thanh điều hướng tab dưới đáy (Bottom Navigation: Trang chủ, Hồ sơ, Hộp thư), khiến `classifier.py` không nhận diện được là feed hay profile chính, rơi vào trạng thái `unknown TikTok state` và kích hoạt alert máy kẹt.

## 2. Giải pháp Recovery chuẩn (2 tầng)
1. **Tầng Core (`automation-core/src/automation_core/tiktok/benign_popup.py`)**:
   - Hàm detector `detect_edit_profile_subpage(root)`:
     - Nhận diện các markers: "Sửa hồ sơ" / "Edit profile", "Thay đổi ảnh" / "Change photo", "Thay đổi video", "Tên người dùng", "Tiểu sử".
     - Loại trừ nếu có thanh điều hướng tab dưới đáy hoặc các input nhạy cảm (password, login).
     - Tìm nút Back (góc trên bên trái: bounds x <= 250, y <= 350) với content-desc / text "Quay lại", "Back", "←", hoặc resource-id có `back`/`close`.
   - Đưa `detect_edit_profile_subpage` vào `detect_allowed_generic_popup(root)` và ánh xạ action `dismiss_close_button`.

2. **Tầng Centralized Registry (`tiktok-luot nuoi acc/python_runner/flows/benign_popup_registry.py`)**:
   - Đăng ký entry `profile_edit_subpage_overlay` (priority 87).
   - Dùng `_detect_edit_profile(xml_content, ocr_text)` và `_dismiss_edit_profile(ctx)`:
     - Ưu tiên tap nút Back nếu tìm thấy element hợp lệ.
     - Fallback gửi `send_device_back_key(ctx)` (hoặc `input keyevent 4`) để thoát subpage về Profile / Feed.

## 3. Lệnh kiểm chứng & Canary
- Unit tests:
  ```powershell
  python -m pytest "D:\Taadaa\automation-core\tests\test_tiktok_benign_popup.py"
  python -m pytest "D:\Taadaa\tiktok-luot nuoi acc\python_runner\tests\test_benign_popup_registry.py"
  ```
- Canary test máy kẹt:
  ```powershell
  powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
  ```
