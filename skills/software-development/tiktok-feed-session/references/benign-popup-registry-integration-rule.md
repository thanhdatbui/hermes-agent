# Centralized Benign Popup Registry vs Orphan Handlers Pitfall

## Bối cảnh & Hiện tượng
- Trong repo `tiktok-luot nuoi acc`, một số popup (ví dụ popup yêu cầu truy cập danh bạ: *"Để kết nối với những người bạn biết trên TikTok, hãy cho phép truy cập vào danh bạ của bạn trong mục cài đặt thiết bị"* với nút `Không cho phép` / `Mở cài đặt`) đã từng có hàm `detect_contact_permission_popup` / `dismiss_contacts_permission_popup` viết trong `python_runner/flows/benign_popup.py`.
- Tuy nhiên khi chạy live batch (`multi-machine-feed-session`), máy vẫn bị dừng phiên với lý do:
  `unexpected popup/dialog marker detected` (Trạng thái: GIỮ HIỆN TRƯỜNG).

## Nguyên nhân gốc rễ
1. **Cơ chế điều phối trung tâm:**
   - Luồng feed runtime (`feed_swipe_smoke.py`, `calibrate_screens.py`, `observe.py`) ưu tiên gọi `find_matching_handler(xml, ocr)` từ `python_runner/flows/benign_popup_registry.py`.
   - Nếu một popup chỉ có hàm rời rạc trong `benign_popup.py` mà **không được đăng ký** qua `register_popup_handler(RegistryEntry(...))` trong `benign_popup_registry.py`, nó là dead code đối với runtime.

2. **Cơ chế an toàn fail-closed của Classifier:**
   - Khi phát hiện các marker popup/dialog trên UI mà không nằm trong allowlist của `detect_allowed_generic_popup` hoặc `find_matching_handler`, `core/classifier.py` sẽ phân loại màn hình là `manual-needed:popup`.
   - Điều này trigger `safety.py` trả về `unexpected popup/dialog marker detected`, buộc worker dừng phiên và gửi cảnh báo giữ hiện trường.

## Quy tắc bắt buộc khi tạo/sửa Popup Dismiss Handler
1. **Luôn đăng ký vào `BENIGN_POPUP_REGISTRY`:**
   - File: `python_runner/flows/benign_popup_registry.py`.
   - Định nghĩa detector `_detect_<popup_name>(xml_content, ocr_text) -> bool` kiểm tra cả text/content-desc và XML structure (tránh false positive với các dialog bảo mật/login).
   - Định nghĩa dismisser `_dismiss_<popup_name>(ctx) -> PopupDismissResult` ưu tiên tap nút từ chối (`Không cho phép`, `Hủy`, `Đóng`, icon X) theo tọa độ node XML thật hoặc fallback coordinate tỷ lệ, trả về `popup_closed=True`.
   - Gọi `register_popup_handler(RegistryEntry("<popup_name>", priority, detector, dismisser, True, "manual"))`.
2. **Kiểm tra tương thích với `core/benign_popup.py` và `core/classifier.py`:**
   - Nếu popup có thể xuất hiện tại bước calibrate/start-up/swipe, đảm bảo `detect_allowed_generic_popup` trong `core/benign_popup.py` hoặc `benign_popup_registry` nhận diện được để classifier không gán nhãn `manual-needed:manual_challenge` hoặc unhandled popup.
3. **Unit test verification:**
   - Thêm test case trong `python_runner/tests/test_benign_popup_registry.py` để verify `find_matching_handler` match đúng handler khi gặp sample XML thật.
