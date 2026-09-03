# Nickname Auto-fill & Profile Switcher Fixes (2026-08-19)

## 1. Cấm tap `@username` để mở Account Switcher (Bị Copy Username)
- **Hành vi thật của TikTok trên Profile**: Khi tap vào node `@username` bên dưới avatar, TikTok sẽ **copy username vào clipboard** kèm toast thông báo, KHÔNG BAO GIỜ mở menu Chuyển đổi tài khoản (Account Switcher).
- **Vấn đề acc chưa có tên**: Acc vừa reg chưa có Display Name sẽ hiển thị nút `+ Thêm tên` (`Add name`) ở header trên cùng (`com.ss.android.ugc.trill:id/sew` / `id/se2`). Nếu code cố tìm anchor từ header, nó sẽ bấm trúng form đổi tên hoặc bị kẹt.
- **Giải pháp chuẩn (User chỉ đạo 19/08)**: Khi `_resolve_profile_switch_anchor()` phát hiện tài khoản hiện tại chưa có tên ("Thêm tên" / "Add name" trong XML):
  1. Gọi hàm `fill_name(device_id, email)` từ module `D:\Taadaa\Tiktok_Reg\social_reg_v1.py`.
  2. Bấm `+ Thêm tên` -> Tạo tên hiển thị chuẩn đẹp từ email qua `make_tiktok_name(email)` -> Nhập vào ô `id/hjp` -> Bấm `Lưu` (góc trên phải) -> Bấm `Xác nhận` dialog 7 ngày.
  3. Re-capture lại XML mới -> Profile lúc này đã có Display Name chuẩn -> Tìm được ngay Account Switcher Anchor (`_find_sticky_profile_header`).

## 2. Lỗi mất Focus giả do SystemUI (`com.android.systemui`)
- Trên các máy Samsung S7 (Android 7/8), thanh trạng thái trên đỉnh (pin, sóng, đồng hồ, thông báo VPN) chiếm các node đầu tiên trong UI XML (`package="com.android.systemui"`).
- Nếu `get_focused_activity()` dùng regex `package="([^"]+)"` đơn giản lấy node đầu tiên, nó sẽ phán nhầm TikTok bị mất focus -> kích hoạt `preserve_blocker_screen` và dừng oan toàn bộ máy.
- **Fix**: Luôn dùng `re.findall(r'package="([^"]+)"', cap.xml)` và ưu tiên kiểm tra sự xuất hiện của các package TikTok (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`).

## 3. Chống bấm nhầm vào trang "Số lượt xem hồ sơ"
- Trên header bên phải của Profile có icon 2 người / dấu chân (`id/ic7`, `id/tv_number`, `Số lượt xem hồ sơ`).
- Bộ lọc `find_switcher_anchor` và `_resolve_profile_switch_anchor` phải loại trừ tuyệt đối:
  - Resource ID chứa `:id/ic7`
  - Text / Content-desc chứa `"số lượt xem hồ sơ"`, `"lượt xem hồ sơ"`

## 4. Bắt buộc truyền `result` khi log trong `auto_fill_name` exception handler
- Trong `_resolve_profile_switch_anchor()`, khi khối `auto_fill_name` gặp ngoại lệ và nhảy vào `except Exception as exc:`, mọi lệnh gọi `ctx.logger.log(...)` BẮT BUỘC phải có tham số `result="failed"` (hoặc `result="fail"`).
- Nếu thiếu `result`, `JsonlLogger.log()` sẽ quăng `TypeError: JsonlLogger.log() missing 1 required keyword-only argument: 'result'`, làm dừng phiên oan uổng và trigger alert `[MÁY XX] DỪNG PHIÊN`.

## 5. Dọn dẹp định nghĩa trùng lặp trong `social_reg_v1.py`
- Kiểm tra không để tồn tại 2 định nghĩa hàm `make_tiktok_nickname_candidates(email)` trong cùng file (bản trên dòng 3195 là logic Việt hóa mới theo quy tắc farm, bản dưới dòng 3293 là code cũ thừa dễ gây xung đột/ghi đè).

