# Benign Popup Registry & Dismissal Patterns

## 1. Kiến trúc Centralized Benign Popup Registry (`flows/benign_popup_registry.py`)
Mọi popup thông báo, điều khoản, modal che màn hình của TikTok trong feed session PHẢI được đăng ký qua Centralized Registry để các hook `drain_known_popups`, `_maybe_dismiss_popup_baseline`, `_maybe_dismiss_allowed_popup_row` tự động phát hiện và dismiss:

```python
register_popup_handler(
    RegistryEntry(
        name="rewards_virtual_items_policy_dialog",
        priority=89,  # 1..100 (Cao hơn chạy trước)
        detector=_detect_rewards_virtual_items_policy,
        dismisser=_dismiss_rewards_virtual_items_policy,
        enabled=True,
        source="manual",
    )
)
```

## 2. Popup Mẫu: Chính sách Phần thưởng & Vật phẩm ảo ("Đã hiểu")
- **Hiện tượng**: Modal popup xuất hiện đè lên video feed:
  - Header: `Thông tin cập nhật Chính sách Phần thưởng và Chính sách vật phẩm ảo` (resource-id: `.../ndu`)
  - Body: `Chúng tôi đang cập nhật Chính sách vật phẩm ảo và đã tạo một bản Chính sách Phần thưởng riêng biệt...` (resource-id: `.../ndt`)
  - Nút đóng: `Đã hiểu` (class: `android.widget.Button`, clickable: `true`)
- **Detector**:
  - Kiểm tra `chính sách phần thưởng` hoặc `chính sách vật phẩm ảo` trong `xml_content` / `ocr_text`.
  - Đồng thời kiểm tra nút `đã hiểu` hoặc `got it`.
- **Dismisser**:
  - Tìm node có text / content-desc `"Đã hiểu"`.
  - Tính tâm tọa độ từ bounds `((x1 + x2) // 2, (y1 + y2) // 2)`.
  - Gọi `_perform_click_target(ctx, tap_pt)`.
  - Trả về `PopupDismissResult(dismissed=True, reason="clicked_da_hieu_rewards_policy", before_attempt=before, popup_closed=True)`.

## 3. Quy tắc trích xuất UI XML trên máy farm
Khi cần dump XML để kiểm tra hiện trường:
- Không dùng `adb shell uiautomator dump` trần trụi vì dễ bị treo tiến trình hoặc trả về empty file.
- Dùng `automation_core.capture_ui_xml(AdbClient(serial=serial))` từ Python runner.
