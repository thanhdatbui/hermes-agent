# Troubleshooting: Navigation Overlay Dismissal Failures

## Case: `failed_dismiss_overlay_before_navigation: follow_friends_popup_no_close_control`

### Triệu chứng & Nguyên nhân
1. Khi `calibrate_screens.py` chuẩn bị click vào navigation target (vd: Tab Profile hoặc Home), nó chạy tiền kiểm tra overlay qua `find_matching_handler(xml_text, "")`.
2. Handler `follow_friends_suggestion_popup` (priority 81 trong `benign_popup_registry.py`) khớp với màn hình hiện tại.
3. `calibrate_screens.py` gọi dismisser `_dismiss_follow_friends` -> `dismiss_follow_friends_suggestion_popup` trong `benign_popup.py`.
4. Hàm này dùng `_find_follow_friends_semantic_close_control(current_root)` để tìm nút đóng (X hoặc "Không quan tâm"). Nếu màn hình là subpage full-screen, bottom sheet mới, hoặc giao diện chỉ có nút Back mũi tên điều hướng, hàm trả về `None`.
5. Khi không có nút đóng semantic, hàm fail ngay với `reason = "follow_friends_popup_no_close_control"` thay vì thử các biện pháp đóng fallback.
6. `calibrate_screens.py` nhận kết quả `dismissed=False` và dừng toàn bộ chu trình điều hướng với lỗi:
   `failed_dismiss_overlay_before_navigation: follow_friends_popup_no_close_control`.

### Cách khắc phục chuẩn
- Tại `dismiss_follow_friends_suggestion_popup` trong `python_runner/flows/benign_popup.py`:
  - Khi không tìm thấy close target semantic, bổ sung fallback:
    1. Tìm nút back navigation ở góc trên bên trái (nút arrow back clickable ở top-left).
    2. Nếu không có hoặc tap thất bại, gửi lệnh `ctx.adb.press_back()` (Keyevent 4).
    3. Đợi UI settle (`time.sleep(1.0)`), dump/capture lại hierarchy.
    4. Kiểm tra lại `detect_follow_friends_suggestion_popup(after_root)`: nếu màn hình đã thoát khỏi popup gợi ý bạn bè, trả về `dismissed=True`.
- Đảm bảo `calibrate_screens.py` có thể tiếp tục navigation suôn sẻ mà không bị fail-closed oan.
