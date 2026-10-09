# TikTok Offline Video / Wi-Fi Popup Allowlist Pattern

## 1. Triệu chứng & Nguyên nhân
- Khi đang chạy feed-session hoặc swipe feed, script dừng lại với stop_reason / error:
  `popup is not in the shared TikTok allowlist; manual review required`
- Màn hình thiết bị hiển thị popup thông báo tính năng tải ngoại tuyến của TikTok:
  - Text chính: `"Tự động tải video về qua Wi-Fi để xem ngoại tuyến?"` hoặc `"Tự động tải video về qua Wi-Fi"` (Tiếng Anh: `"Download videos automatically over Wi-Fi"`).
  - Nút bấm chính: `"OK"` (hoặc `"Đóng"`, `"Hủy"`, `"Dismiss"`).

## 2. Luồng xử lý Popup trong Codebase (Consumer ↔ Core)
- **Consumer (`tiktok-luot nuoi acc`)**:
  1. `flows/feed_swipe_smoke.py` gọi `dismiss_allowed_generic_popup` (`flows/benign_popup.py`).
  2. `dismiss_allowed_generic_popup` trước tiên kiểm tra `flows/benign_popup_registry.py` (`find_matching_handler`).
  3. Nếu registry không khớp, gọi `_dismiss_shared_popup_via_core` uỷ quyền cho `automation-core`.
- **Shared Core (`automation-core`)**:
  1. Gọi `dismiss_tiktok_popups` trong `automation_core/tiktok/startup.py`.
  2. Kiểm tra `detect_tiktok_popup_action(root)` trong `automation_core/tiktok/benign_popup.py`.
  3. Duyệt qua danh sách detector trong `detect_allowed_generic_popup(root)` và các detector cụ thể.
  4. Nếu không detector nào match, hàm trả về `None` -> Consumer gán `reason = "popup is not in the shared TikTok allowlist; manual review required"` và dừng flow để bảo vệ an toàn tài khoản.

## 3. Quy chuẩn vá Allowlist
Khi gặp popup mới dạng này:
1. **Tại `automation-core/src/automation_core/tiktok/benign_popup.py`**:
   - Viết detector `detect_offline_video_wifi_download_popup(root: ET.Element) -> BenignPopupMatch | None`:
     - Text markers: `"tự động tải video về qua wi-fi để xem ngoại tuyến?"`, `"tự động tải video về qua wi-fi"`, `"download videos automatically over wi-fi"`.
     - Tìm nút target: ưu tiên `"OK"` (nếu có), fallback `"Đóng"`, `"Hủy"`, `"Dismiss"`.
     - Trả về `BenignPopupMatch("offline_video_wifi_download", markers, target_element)`.
   - Cập nhật hàm `_dismiss_action(popup_type: str)` trả về action `"tap_ok_button"` (hoặc `"allowlist_dismiss"`).
   - Thêm detector vào danh sách `detect_allowed_generic_popup(root)` hoặc `detect_tiktok_popup_action(root)`.
2. **Hoặc đăng ký nhanh qua Registry (`benign_popup_registry.py`)**:
   - Đăng ký `RegistryEntry` với detector match chuỗi XML/OCR và action tap tương ứng.
3. **Canary Test B4 xác nhận**:
   ```powershell
   powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
   ```
