# Account Switcher & Profile Identity Recognition Pitfalls (2026-08-22)

## 1. Profile Username rỗng khi XML thiếu node `@handle`
- **Hiện tượng:** Trên một số phiên bản giao diện TikTok / nick mới đăng ký, node `@username` có thể bị rỗng hoặc format text không có ký tự `@` ở đầu, dẫn đến `_profile_identity_from_xml` gán `identity["username"] = ""` dù `display_name` hiển thị đúng tên nick.
- **Hệ quả:** Preflight so sánh `current == expected` thất bại vì `"" != "quocthuong99"` -> kích hoạt luồng mở Account Switcher để đổi tài khoản dù tài khoản đích đã active sẵn trên máy.
- **Giải pháp chuẩn:** Trong `_profile_identity_from_xml`, nếu `username` rỗng mà `display_name` hợp lệ (không phải placeholder như 'Thêm tên', 'Thêm tiểu sử', 'Trang chủ'...), fallback `username = display_name`.

## 2. Account Switcher Bottom Sheet trượt trễ (Animation Lag)
- **Hiện tượng:** Khi tap vào tên nick / switch anchor để mở switcher sheet, modal trượt từ dưới lên cần 0.5s - 1.0s để render hoàn tất.
- **Hệ quả:** Lệnh dump XML capture ngay khi sheet chưa xuất hiện -> không tìm thấy tiêu đề `"Chuyển đổi tài khoản"` / `"Switch account"` -> script kích hoạt cơ chế recovery gửi phím BACK làm đóng luôn popup vừa mở -> dừng phiên với lỗi `manual-needed:account-switcher-not-open: profile screen remained after switch-anchor tap`.
- **Giải pháp chuẩn:** Trong `_capture_profile_switcher_xml_with_add_phone_guard`, nếu lần dump đầu chưa thấy switcher XML, thêm `time.sleep(1.0)` và dump lại settled XML (`f"profile_switcher_{attempt}_settled"`) trước khi kết luận kẹt/đóng popup.
