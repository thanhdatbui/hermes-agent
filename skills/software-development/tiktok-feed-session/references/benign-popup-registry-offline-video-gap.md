# Pitfall: Dual Benign Popup Systems & Registry Gap (Offline Video Prompt)

## Background & Context

Trong repo `D:\Taadaa\tiktok-luot nuoi acc`, hệ thống xử lý popup vô hại (benign popups) tồn tại ở 2 tầng:

1. **Legacy Module (`python_runner/core/benign_popup.py` & `python_runner/flows/benign_popup.py`)**:
   - Chứa các detector cũ như `detect_offline_video_prompt(root)`, `detect_playcore_download_popup(root)`, v.v.
   - Hàm `_handle_offline_video_prompt(ctx, current_root)` tìm nút `("đóng", "close", "ok")` để dismiss.
   - Các từ khóa đã hỗ trợ trong `core/benign_popup.py`:
     - `"video ngoại tuyến"`
     - `"tải video về để xem ngoại tuyến"`
     - `"tự động tải video về qua wi-fi để xem ngoại tuyến"`
     - `"tự động tải video về"`
     - `"download videos automatically over wi-fi"`

2. **Registry-Driven Engine (`python_runner/flows/benign_popup_registry.py`)**:
   - Cơ chế trung tâm mới sử dụng `RegistryEntry(name, priority, detector, dismisser)`.
   - Cung cấp hàm `find_matching_handler(xml_content, ocr_text)` được gọi bởi:
     - `_navigate_profile_for_preflight` (trong `feed_swipe_smoke.py` khi gặp navigation blocker)
     - `_maybe_recover_navigation_from_add_phone`
     - Swipe loop blockers & recovery handlers.

## The Gap / Pitfall

* **Triệu chứng**: Khi popup *"Tự động tải video về qua Wi-Fi để xem ngoại tuyến"* xuất hiện trong lúc `_navigate_profile_for_preflight` đang điều hướng về profile trước phiên feed, script không vượt qua được và fail navigation (`target not found` hoặc `navigation_blocker`).
* **Nguyên nhân**: Popup này đã có trong `core/benign_popup.py` nhưng **CHƯA ĐƯỢC ĐĂNG KÝ** vào `benign_popup_registry.py`. Hàm `find_matching_handler(...)` hoàn toàn không biết đến `offline_video_prompt`, dẫn tới việc registry bỏ qua popup này và coi màn hình là unhandled blocker.
* **Cách khắc phục chuẩn**:
  - Khi thêm hoặc rà soát benign popup, BẮT BUỘC phải đăng ký `RegistryEntry` trong `flows/benign_popup_registry.py`:
    ```python
    # Trong flows/benign_popup_registry.py
    from core.benign_popup import detect_offline_video_prompt

    def _detect_offline_video(xml_content: str = "", ocr_text: str = "") -> bool:
        root, _ = parse_xml_safely(xml_content)
        if root is None:
            return False
        return detect_offline_video_prompt(root) is not None

    def _dismiss_offline_video(ctx: Any) -> Any:
        # Tap nút 'Đóng' / resource-id z6g / dcj / text 'Đóng'
        ...
    ```
  - Đảm bảo popup có mặt trong `get_sorted_registry()` với priority phù hợp (tránh ghi đè login/account dialogs).
