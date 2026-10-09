# False-Positive P0 "Login/Account Screen Detected" từ Card "Tài khoản được đề xuất"

## Hiện tượng & Triệu chứng
Khi chạy nuôi feed TikTok trên farm (`multi-machine-feed-session`), một số máy (ví dụ M23, M68) bị hệ thống phân loại cảnh báo:
`error: "login/account screen detected"`
`blocker_type: "login-gms-verification"`
`final_status: "manual-needed"`

Cảnh báo này thường kích hoạt cờ đỏ **P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT**, gây nghi ngờ tài khoản bị logout hoặc checkpoint đăng nhập.

## Hiện trường thực tế (Root Cause Analysis)
Khi trích xuất XML UI dump tại thời điểm lỗi (`ui.xml`):
1. Tài khoản TikTok hoàn toàn không bị văng, vẫn đang login bình thường ở feed Bạn bè (`Friends`) hoặc For You.
2. TikTok hiển thị card gợi ý kết bạn:
   - Header: `"Tài khoản được đề xuất"` (hoặc `"Gợi ý tài khoản"`)
   - Nút hành động: Nút `"Follow lại"` (`:id/che`) và icon `"Đóng"` (`:id/fwi`).
3. Trong `automation-core/src/automation_core/tiktok/benign_popup.py`:
   - `SENSITIVE_POPUP_TERMS` có chứa chuỗi `"tài khoản"`.
   - `has_sensitive_marker(root)` phát hiện thấy có text chứa `"tài khoản"` kết hợp với một node clickable chứa text/desc `"đóng"` (`:id/fwi`), dẫn đến việc đánh giá màn hình là nhạy cảm (`sensitive_action_terms` khớp `"đóng"`).
4. Trong `classifier.py`:
   - Điều kiện `if has_sensitive_marker(root)` được đặt TRƯỚC bộ kiểm tra popup thông thường (`detect_allowed_generic_popup(root)`).
   - Dù hàm `detect_contact_follow_suggestion(root)` nhận diện chính xác card này, nhưng màn hình vẫn bị gán nhầm thành `screen="manual-needed:login"`, `reasons=["login/account/credential marker present"]`.

## Giải pháp chuẩn hóa (Patch Contract)
Phải miễn trừ rõ ràng `detect_contact_follow_suggestion` khỏi `has_sensitive_marker` tại cả 2 tầng:

1. **Tại `automation-core/src/automation_core/tiktok/benign_popup.py`**:
```python
def has_sensitive_marker(root: ET.Element) -> bool:
    ...
    if _has_any_packageinstaller_permission_marker(elements):
        return True
    if detect_contact_follow_suggestion(root) is not None:
        return False
    if not marker_elements:
        return False
```

2. **Tại consumer (`python_runner/core/benign_popup.py`)**:
```python
def has_sensitive_marker(root):
    ...
    if detect_add_phone_popup(root) is not None:
        return False
    if detect_contact_follow_suggestion(root) is not None:
        return False
    return _impl.has_sensitive_marker(root) or _impl.detect_save_login_popup(root) is not None
```

## Quy trình đối soát & Kiểm chứng
- Kiểm tra bằng unit test: `pytest tests/test_tiktok_benign_popup.py` và `pytest python_runner/tests/test_classifier.py`.
- Kiểm tra trực tiếp trên artifact thật: Gọi `classify_tiktok_screen(root)` với file XML dump hiện trường. Kết quả phải chuyển từ `manual-needed:login` sang `manual-needed:popup` với reason `known contact_follow_suggestion popup detected`.
