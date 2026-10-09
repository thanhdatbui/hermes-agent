# Dongvanfb Hotmail Selection & TikTok Reg Hard Invariants

## 1. Phân Tích Các Loại Hotmail Trên dongvanfb.net Cho Farm Taadaa

Khi mua Hotmail phục vụ flow reg TikTok và đọc mã OTP tự động qua Microsoft Graph API:

| ID Sản Phẩm | Tên Loại | Giá | Token Scope | Đọc OTP Graph API? | Đánh Giá Cho Farm |
|---|---|---|---|---|---|
| **ID 5** | Hotmail TRUSTED [GRAPH API] | 350đ | Chỉ IMAP, POP, SMTP (thiếu `Mail.Read`) | ❌ LỖI (`Graph token invalid`) | **LỎ, CẤM MUA** |
| **ID 59** | Hotmail TRUSTED [IMAP/POP3/GRAPH API] | 350đ | Tương tự ID 5 | ❌ LỖI / Thiếu scope | **CẤM MUA** |
| **ID 57** | HOTMAIL TRUSTED THÊM KHÔI PHỤC FVIAINBOXES.COM | 350đ | Đầy đủ: `User.Read`, `Mail.ReadWrite`, `Mail.Read`, `IMAP`, `POP`, `SMTP` | ✅ THÀNH CÔNG 100% | **CHUẨN NHẤT, NÊN MUA** |

### Khớp với quy trình ngâm nick 7 ngày của User:
1. Đăng ký TikTok bằng Hotmail ID 57.
2. Nuôi ngâm 7 ngày trên Farm.
3. Vào trang bảo mật Microsoft (`account.live.com`):
   - Đổi password mới, tích chọn *"Sign me out of all devices"* để đăng xuất sạch sẽ thiết bị cũ của shop.
   - Trong phần Advanced Security Options, xóa bỏ email khôi phục `@fviainboxes.com` của shop và thêm mail/SĐT của user vào.
4. **Lưu ý về sàn:** Sàn MMO / dongvanfb.net **KHÔNG có nhãn "Chưa qua dịch vụ" hay "Chưa qua TikTok"**, họ chỉ phân loại theo giao thức và mục đích Facebook.

---

## 2. Giới Hạn Trần 8 Tài Khoản Của App TikTok & Dropdown Switcher

- App TikTok trên Android có giới hạn cứng: **tối đa 8 tài khoản đăng nhập cùng lúc**.
- Khi app đã đủ 8 nick: nút **"Thêm tài khoản" (Add account)** trong dropdown switcher bị **ẨN HOÀN TOÀN**.
- `social_reg_v1.py` kiểm tra số lượng node tài khoản (`_acc_count >= 8`), nếu đủ 8 nick sẽ raise `MACHINE_FULL_8_ACCOUNTS` và thoát về Home.
- **Quy tắc đối soát:** Không được chỉ tin vào file Excel `taikhoan_dat_v2` hay `taikhoan_run_safe` (có thể bị lệch so với thực tế app nếu trước đó có nick thử nghiệm chưa cập nhật). Phải kiểm tra dropdown switcher thực tế trên máy trước khi chạy.

---

## 3. Cơ Chế Khóa Hai Chiều Bắt Buộc Trong `social_reg_v1.py`

- Hàm `_acquire_social_device_lock_or_skip` **BẮT BUỘC** gọi `acquire_device_lock(..., user_authorized=True)` để tạo file `machine_<N>.lock.json`.
- **CẤM** dùng biến môi trường opt-in `DEVICE_LOCK_ENABLED` (khiến chạy lệnh CLI đơn lẻ bị bypass lock).
- Entrypoint `register()` phải acquire lock trước khi thao tác ADB. Nếu máy đang có cron nuôi nick hoặc script khác giữ lock -> **Safe-Skip dừng ngay lập tức**, giải phóng lock trong khối `finally`.
