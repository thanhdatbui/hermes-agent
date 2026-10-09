# Chẩn đoán & Xử lý False-Positive Login Screen do Popup Gợi ý Bạn bè

## 1. Bản chất sự cố
- Khi TikTok hiển thị card gợi ý bạn bè / danh bạ (`detect_contact_follow_suggestion`):
  - Tiêu đề chứa từ khóa: `"Tài khoản được đề xuất"`, `"Gợi ý tài khoản"`, `"Người mà bạn có thể biết"`.
  - Giao diện có các nút tương tác: `"Follow lại"`, `"Theo dõi lại"`, và nút icon đóng `"Đóng"` (`ImageView` có `clickable="true"`).
- **Cơ chế gây lỗi false positive:**
  - `has_sensitive_marker(root)` trong `automation-core` và `python_runner` kiểm tra danh sách `SENSITIVE_POPUP_TERMS` có từ khóa `"tài khoản"`.
  - Đồng thời phát hiện element clickable có nhãn `"đóng"`.
  - Kết quả: `has_sensitive_marker` trả về `True`, kích hoạt cờ `manual-needed:login` ("login/account screen detected") ngắt ngang ca chạy của máy, dù tài khoản hoàn toàn không bị văng phiên hay đòi xác minh mật khẩu.

## 2. Quy tắc phân loại & Miễn trừ (Contract Rule)
- Trước khi đánh giá `has_sensitive_marker`:
  - Phải kiểm tra miễn trừ cho popup gợi ý danh bạ/bạn bè:
    ```python
    if detect_contact_follow_suggestion(root) is not None:
        return False
    ```
  - Điều này cho phép màn hình lọt qua tầng kiểm tra nhạy cảm để đi vào luồng phân loại popup lành tính (`known contact_follow_suggestion popup detected`), chuyển thành `manual-needed:popup` và kích hoạt handler đóng tự động thay vì dừng khẩn cấp.

## 3. Quy trình xác minh hiện trường O(1)
- Không vội can thiệp ADB hay kết luận nick bị văng.
- Kiểm tra file `log.jsonl` và trích xuất UI dump XML gần nhất tại bước kẹt (`switch_friends` hoặc `swipe_after`).
- Kiểm tra các text node xem có chứa `"Tài khoản được đề xuất"` và `detect_contact_follow_suggestion(root)` có trả về match hay không.
- Đối soát trạng thái `profile_identity`: nếu máy vừa pass profile identity trước đó vài phút thì 99% là false-positive từ card gợi ý.
