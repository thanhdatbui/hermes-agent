# Quy trình và Kiến trúc Xử lý Popup & Live Overlay (tiktok-luot nuoi acc)

## 1. Kiến trúc Dual-Layer Popup & Overlay Dispatch
Hệ thống xử lý popup và màn hình kẹt trong TikTok Feed Session chạy theo kiến trúc 2 lớp:
1. **`python_runner/flows/benign_popup.py`**:
   - Định nghĩa các hàm `detect_<name>` (kiểm tra XML tags, bounds, OCR text) và `dismiss_<name>` (thực hiện tap nút đóng, swipe hoặc back).
   - Utility chuẩn để gửi phím quay lại: `send_device_back_key(ctx)` (tương thích đa phương thức qua adb shell `input keyevent 4`, actions.back, v.v.).
   - Định dạng trả về bắt buộc: `PopupDismissResult(dismissed=True, reason="...", before_attempt=..., popup_closed=True)`.

2. **`python_runner/flows/benign_popup_registry.py`**:
   - Centralized Registry: Quản lý danh sách các popup/overlay có thứ tự ưu tiên (`RegistryEntry(name, priority, detector, dismisser, enabled, source)`).
   - Cơ chế hoạt động: Khi `dismiss_allowed_generic_popup` hoặc `dismiss_any_popup` được gọi, hệ thống ưu tiên kiểm tra **Registry-first dispatch** thông qua `find_matching_handler(xml_content, ocr_text)`.
   - Khi phát hiện một popup mới (ví dụ: `event_space_overlay`, `live_campaign_overlay`), BẮT BUỘC phải đăng ký vào registry này với độ ưu tiên phù hợp (overlay livestream/sự kiện thường ở mức ~79).

## 2. Quy trình 3 bước thêm Popup/Overlay mới
1. **Tạo detector và dismisser**:
   - Viết `detect_<name>(xml_content, ocr_text)` tìm các text markers đặc trưng (ví dụ tiếng Việt có dấu và không dấu).
   - Viết `dismiss_<name>(ctx)` dùng `send_device_back_key(ctx)` hoặc tìm bounds nút bấm để click.
2. **Đăng ký vào Registry**:
   - Thêm `register_popup_handler(RegistryEntry("<name>", priority, _detect_<name>, _dismiss_<name>, True, "manual"))` trong `benign_popup_registry.py`.
3. **Kiểm tra hồi quy & Canary Test**:
   - Chạy test suite của registry:
     ```bash
     cd "D:/Taadaa/tiktok-luot nuoi acc/python_runner"
     python -m pytest tests/test_benign_popup_registry.py
     ```
   - Chạy Canary Test trên máy thực tế (ví dụ Máy 40):
     ```powershell
     powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines 40 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
     ```

## 3. Pitfall nghiêm trọng: Quét file trong `python_runner`
- Repo `tiktok-luot nuoi acc/python_runner` chứa các thư mục rác rất lớn như `.ai-runs`, `.pytest_cache`, wheel build và log.
- **CẤM:** Tuyệt đối không dùng `grep -rn` hoặc ripgrep toàn bộ cây thư mục `python_runner`. Thao tác này sẽ gây timeout lệnh (lên tới 900 giây) và tiêu tốn tài nguyên.
- **CHUẨN:** Luôn chỉ định file đích rõ ràng (`flows/benign_popup.py`, `flows/benign_popup_registry.py`, `tests/...`).
