# Auto Fill Name & Nickname Auto-Recovery Flow (2026-08-23)

## 1. Cơ chế hoạt động
Khi runner vào màn hình Profile của TikTok để chuẩn bị chuyển acc hoặc lướt feed:
- Nếu tài khoản chưa có Display Name (hiện nút `+ Thêm tên` / `Add name`), runner sẽ không tìm thấy anchor Profile header thông thường.
- `_resolve_profile_switch_anchor()` trong `python_runner/flows/feed_swipe_smoke.py` tự động phát hiện và kích hoạt `fill_name(device_id, email)` từ module `D:\Taadaa\Tiktok_Reg\social_reg_v1.py`.

## 2. Chi tiết các bước thực hiện của `fill_name`
1. Bấm `+ Thêm tên` / `Add name` trên màn Profile.
2. Sinh tên tiếng Việt chuẩn đẹp từ prefix email thông qua `make_tiktok_name(email)`.
3. Nhập tên vào ô EditText tên hiển thị (qua node hoặc broadcast ADB Keyboard).
4. Bấm nút `Lưu` (hoặc `Tiếp tục`).
5. Bấm `Xác nhận` trên dialog cảnh báo đổi tên 7 ngày.
6. Re-capture lại UI XML mới (`profile_switch_anchor_after_fill_name`).
7. Lúc này Profile đã có Display Name chuẩn, runner tìm được ngay Account Switcher Anchor và tiếp tục chu trình chuyển nick hoặc lướt feed bình thường.

## 3. Pitfall & Invariant quan trọng
- **Bắt buộc có `result` khi log:** Trong các block `try...except` xử lý flow đặt tên, mọi lời gọi `ctx.logger.log()` bắt buộc phải truyền `result="failed"` (hoặc `"start"`, `"success"`). Thiếu `result` sẽ gây ngoại lệ `TypeError: JsonlLogger.log() missing 1 required keyword-only argument: 'result'` làm dừng phiên fatal.
