# Interactive In-feed Ad Modal Swipe Interception & Recovery Failure (2026-08-24)

## Hiện tượng & Alert
- Alert Telegram: `[MÁY 29] DỪNG PHIÊN - unexpected popup/dialog marker detected - Trạng thái: GIỮ HIỆN TRƯỜNG`.
- Màn hình hiện trường: TikTok feed hiển thị interactive promotional modal / card quảng cáo có nút **"Tìm hiểu thêm"** và text/nút **"Đóng"**.
- `classifier.py` nhận diện marker "Đóng" / popup $\rightarrow$ gán nhãn `manual-needed:popup`.
- `safety.py` map `manual-needed:popup` $\rightarrow$ reason `"unexpected popup/dialog marker detected"`.

## Phân tích nguyên nhân gốc rễ

### 1. Modal overlay chặn cử chỉ swipe (Gesture Interception)
- Card quảng cáo dạng interactive modal nằm ở lớp UI đè lên ViewPager của Feed.
- Cử chỉ vuốt dọc thông thường (`input swipe 540 1600 540 400`) bị chính view của modal tiêu thụ (consumed/intercepted), không truyền xuống Feed ViewPager bên dưới $\rightarrow$ màn hình không trượt sang video mới.

### 2. Tại sao cơ chế vuốt 2 lần cứu kẹt (`_swipe_recovery_on_stuck`) không vượt qua được?
- `_swipe_recovery_on_stuck` gửi lệnh swipe 2 lần, mỗi lần sau đó re-capture và phân loại lại.
- Do swipe không có tác dụng với modal, sau 2 lần swipe màn hình vẫn giữ nguyên popup $\rightarrow$ hàm trả về `None` (không cứu được).
- Sau khi `_swipe_recovery_on_stuck` trả về `None`, row giữ nguyên `manual-needed:popup`.
- `ManualReasonGuard.record()` kiểm tra thấy lỗi `manual-needed:popup` lặp lại liên tiếp $\ge 2$ lần $\rightarrow$ kích hoạt ngắt phiên khẩn cấp và giữ hiện trường.

### 3. Thiếu fallback `BACK` trong swipe recovery khi bị modal đè
- Các popup / overlay dạng modal trong TikTok có thể bỏ qua gesture swipe nhưng phản hồi với phím cứng Android `KEYCODE_BACK` hoặc tap chính xác node "Đóng".
- Nếu rule `learn_more_dialog_dismiss` không match trúng selector nút "Đóng" (do id/class thay đổi trên template quảng cáo mới), flow rơi vào bẫy kẹt vô tận nếu chỉ thử swipe.

## Giải pháp & Hợp đồng xử lý
1. **Typed Ad Dismiss Selector:** Cập nhật detector cho các modal quảng cáo "Tìm hiểu thêm" + "Đóng" bao phủ cả text, content-desc và node bounds của nút "Đóng".
2. **BACK Keyevent Fallback trong Recovery:** Trong `_swipe_recovery_on_stuck`, nếu swipe dọc 2 lần không làm thay đổi màn hình (modal ad đè gesture), thực hiện fallback gửi 1 lệnh `KEYCODE_BACK` để hạ overlay trước khi kết luận thất bại.
3. **Navigation Seam Coverage:** Đảm bảo các seam chuyển tab feed (`tap_navigation_target` / `_maybe_recover_navigation_from_add_phone`) cũng được bọc cơ chế recovery trước khi gọi trực tiếp `manual_guard.record()`.
