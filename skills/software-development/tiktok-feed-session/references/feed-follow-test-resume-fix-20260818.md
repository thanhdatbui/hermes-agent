# Test Resume và Xử lý Lỗi Follow & Feed (18/08)

## 1. Quy tắc Test Resume trước khi Mở khóa (Lock Retention)
- **CẤM TỰ Ý MỞ KHÓA HÀNG LOẠT**: Khi sửa xong một rule/handler (popup, focus, selector), KHÔNG được tự động xóa lock của tất cả các máy.
- **BẮT BUỘC CHẠY TEST RESUME**: Chạy lại script trên chính máy bị lỗi để kiểm chứng thực tế xem script có vượt qua được màn hình kẹt đó hay không.
- **CHỈ MỞ KHÓA KHI TEST THÀNH CÔNG (PASS 100%)**: Nếu máy vẫn kẹt hoặc rơi vào màn khác (Login, Challenge, Checkpoint) -> Tiếp tục GIỮ LOCK file trong `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json`.
- **CHỈ MỞ KHÓA MÁY CỤ THỂ KHI USER RA LỆNH** (vd "Máy 4 mở khóa").

## 2. Reconcile Focused Package & UI XML (Fix Mất Focus TikTok Giả)
- Khi `focused_package` từ system trả về `com.android.systemui` (do thanh thông báo, notification, volume slider, hoặc overlay hệ thống), nhưng UI XML dump được qua ATX vẫn chứa đầy đủ cấu trúc màn hình in-app (`for-you`, `following`, `friends`, `home`, `profile`), `safety_check` phải chấp nhận là **TikTok focused** thay vì báo `TikTok focus lost`.

## 3. Các điểm fix luồng Follow (`tiktok-follow`)
- **Máy 51 (Unicode bidi/isolate)**: Chuẩn hóa toàn bộ text username bằng `_normalize_search_value()` trước khi so sánh `==` với `uid` mục tiêu để tránh bị `identity_mismatch` do ký tự ẩn Unicode.
- **Máy 21 (Profile 2 nút song song)**: Khi profile hiển thị cả nút *"Follow"* đỏ và nút phụ *"Nhắn tin"*, classifier phải ưu tiên kiểm tra nút Follow để phân loại `not_followed` và lấy tọa độ tap.
- **Máy 17, 39 (Tận dụng Feed có sẵn)**: Khi chạy follow hook nối tiếp sau feed với `--skip-identity-verify`, kiểm tra thấy app đang ở Feed thì bắt đầu tìm kiếm follow ngay, tránh relaunch gây timeout 90s (`OPEN_TIKTOK_FAILED`).
