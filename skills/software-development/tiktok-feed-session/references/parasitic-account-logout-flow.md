# Xử lý Nick ký sinh (Parasitic Account Duplication) & Quy trình Logout chọn lọc

## 1. Vấn đề cốt lõi
- **Nick ký sinh**: 1 nick TikTok bị đăng nhập trên 2 máy cùng lúc (thường do nạp trùng email Hotmail/Gmail trong quá khứ).
- **Hệ quả**:
  - Vi phạm quy tắc 1 máy - 1 nick, dễ bị quét checkpoint do đăng nhập đồng thời trên nhiều IP/thiết bị.
  - Máy bị log nhầm bị đẩy lên đủ 8 nick -> ẩn nút "Thêm tài khoản" -> crash flow reg bù (`fail_04_add_account`).
  - CẤM TUYỆT ĐỐI dùng `pm clear` vì sẽ xóa sạch toàn bộ 7 nick chính chủ khác trên máy.

## 2. Quy trình Logout chọn lọc 6 bước trên UI TikTok
1. **Mở Switcher**: Dùng `social_reg_v1.open_account_dropdown(dev)` hoặc tap profile -> tap username header.
2. **Switch sang nick ký sinh**: Tìm node chứa tên nick trong UI XML, tap chuyển active account sang nick đó (`wait=8s`).
3. **Mở Menu hồ sơ & Cài đặt**: Tap Menu 3 gạch `(1005, 150)` -> tap `Cài đặt và quyền riêng tư` (khoảng `621, 1248`).
4. **Cuộn đáy trang Settings**: Vuốt ngược 5-6 lần (`swipe 540 1600 540 300 300`) -> tap nút `Đăng xuất` `(540, 1668)`.
5. **Xác nhận popup Logout**: Tap nút `Đăng xuất` trên bottom sheet xác nhận `(540, 1662)` -> đợi `6s` để TikTok tự out và chuyển sang nick khác.
6. **Nghiệm thu**: Mở lại Switcher, verify nick ký sinh đã biến mất, nút "Thêm tài khoản" đã hiện lại, chụp screencap đính kèm `MEDIA:<path>` trước khi force-stop về HOME.

## 3. Kỷ luật canh phiên Event-Driven vs Giờ cố định
- CẤM hẹn giờ cứng (`20:00`, `23:30`) để can thiệp thiết bị.
- BẮT BUỘC canh qua sự kiện: `run_manifest.json` có `end_time` VÀ số lượng device-lock trong `.codex/device-locks/` bằng `0`.
- BẮT BUỘC tạo cron watchdog script thực tế trong scheduler thay vì hứa suông.
