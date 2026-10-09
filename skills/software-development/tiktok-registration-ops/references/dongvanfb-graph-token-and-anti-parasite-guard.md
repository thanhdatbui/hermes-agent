# Dongvanfb.net Hotmail Graph API & Anti-Parasite Account Protocol

> Ngày ghi nhận: 23/09/2026.
> Phạm vi: Repo `Tiktok_Reg` (`social_reg_v1.py`, `tiktok_login_v1.py`, `hotmail_provider.py`) và toàn bộ vận hành Phone Farm Taadaa.

---

## 1. Đánh Giá Thực Nghiệm 3 Loại Hotmail Trên dongvanfb.net
Sàn `dongvanfb.net` cung cấp các danh mục Hotmail via Facebook với các mức giá và cấu hình token khác nhau:

| Loại | ID | Giá | Scope OAuth2 Microsoft | Đánh Giá Farm Taadaa |
|---|---|---|---|---|
| Hotmail TRUSTED [GRAPH API] | 5 | 350đ | `IMAP.AccessAsUser.All`, `POP.AccessAsUser.All`, `SMTP.Send` (Thiếu `Mail.Read`) | ❌ **LỎ - CẤM MUA**: Gọi Microsoft Graph API bị từ chối quyền truy cập hộp thư (`Graph token invalid.`). Phải mở app Outlook trên phone gõ pass thủ công rất dễ dính checkpoint. |
| Hotmail TRUSTED [IMAP/POP3/GRAPH API] | 59 | 350đ | Chỉ tối ưu cổng IMAP/POP3 cũ | ❌ **KHÔNG PHÙ HỢP**: Cấu hình tương tự ID 5. |
| HOTMAIL TRUSTED THÊM KHÔI PHỤC FVIAINBOXES.COM | 57 | 350đ | Full: `openid profile User.Read Mail.ReadWrite Mail.Send Mail.Read IMAP.AccessAsUser.All POP.AccessAsUser.All SMTP.Send` | ✅ **CHUẨN 100% CHO FARM**: Trao đổi token và kéo OTP qua Microsoft Graph API mượt mà từ PC. Có sẵn mail khôi phục `@fviainboxes.com` khớp 100% quy trình 7 ngày của User. |

### Quy trình ngâm 7 ngày đổi pass Hotmail:
1. Reg TikTok bằng email ID 57.
2. Nuôi ngâm tài khoản TikTok và Hotmail trong 7 ngày.
3. Vào trang quản lý bảo mật tài khoản Microsoft:
   - Đổi mật khẩu Hotmail mới.
   - Tích chọn *"Sign me out of all devices"* (Đăng xuất khỏi tất cả thiết bị) để đá toàn bộ phiên cũ của shop ra ngoài.
   - Vào mục *Advanced Security Options*, xóa địa chỉ mail khôi phục `@fviainboxes.com` và thay bằng thông tin cá nhân. Tài khoản trở thành sở hữu độc quyền 100%.

---

## 2. Hard Lock Enforcement trong social_reg_v1.py
### Tử huyệt bypass lock cũ:
Trước đây, hàm `_acquire_social_device_lock_or_skip` dùng biến môi trường:
```python
lock_enabled = os.environ.get("DEVICE_LOCK_ENABLED", "").strip().lower() in {"1", "true", "yes"}
```
Khi chạy lệnh CLI đơn lẻ bằng tay (`python social_reg_v1.py <STT> ...`), không ai truyền biến này -> `lock_enabled = False` -> Script chạy mà không hề tạo file lock chuẩn `machine_<N>.lock.json`. Hậu quả: Coordinator hoặc các cron khác (batch 2FA, feed session) tưởng máy rảnh nên can thiệp đè lên máy đang chạy.

### Cơ chế Hard Lock mới (Đã vá & verified):
1. **Ép cứng `user_authorized=True`:**
   Mọi lệnh reg đều bắt buộc phải đăng ký file lock `machine_<N>.lock.json` vào `~/.codex/device-locks/`.
2. **Kiểm tra ngay tại entrypoint `register()`:**
   Nếu máy đang có tiến trình khác giữ lock:
   ```text
   [telemetry:device-lock] machine={stt} serial={device_id} action=acquire_conflict status=safe_abort reason=active_lock_by_other_process
   ⚠ STT {stt} đang bị khóa bởi tiến trình/cron khác -> DỪNG để đảm bảo an toàn.
   ```
   Script lập tức `return False`, tuyệt đối không chạm vào app TikTok hay thiết bị.
3. **Giải phóng an toàn trong `finally:`**:
   Khối `finally:` luôn gọi `dev_lease.release()` kèm log telemetry `action=released status=closed`.

---

## 3. Sự Cố Nick Ký Sinh (Cross-Machine Parasite Account) & Quy Tắc Cấm Kỵ
### Bản chất sự cố ngày 23/09/2026:
- Con mail ID 57 (`odessostuffen14@hotmail.com`) đã được tool Farm tự động reg thành công lúc 13:29 trên **Máy 22** thành nick `@lethanhlan14` (lưu tại dòng 176 `taikhoan_dat_v2_updated .xlsx`).
- Coordinator lú lẫn không tra cứu lịch sử, lại đem chính con mail đó sang **Máy 201** để test.
- Khi TikTok báo *"Bạn đã đăng ký"*, Coordinator lại bấm *"Tiếp tục"* rồi bóc OTP qua Graph API nạp vào Máy 201.
- Hậu quả: Nick `@lethanhlan14` bị đăng nhập thêm trên Máy 201, biến thành **nick ký sinh** đăng nhập song song trên 2 thiết bị khác IP/khác cụm (Máy 22 Kibe vs Máy 201 Admin) -> Nguy cơ bị TikTok gắn cờ gian lận / checkpoint hàng loạt.

### Quy tắc bất di bất dịch (Invariants):
1. **Tra cứu Source of Truth trước khi chạy:**
   Trước khi đem bất kỳ mail nào đi test reg hoặc login:
   - Tra cứu sheet `'Tài Khoản'` trong `taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, SQLite `tiktok_tracker.db` và log `social_reg_log.txt`.
   - Nếu mail đã thuộc sở hữu của máy nào -> **CẤM TUYỆT ĐỐI** đăng nhập lên máy khác.
2. **Tách biệt chế độ Test Probe vs Login:**
   - Khi probe kiểm tra mail Zin: Chỉ điền email và bấm Tiếp tục để đọc phản hồi UI.
   - Nếu màn hình báo *"Bạn đã đăng ký"*: **DỪNG LẠI NGAY**, chụp ảnh màn hình Checkpoint 2 (Gate 6) rồi force-stop/quay lại Home. **TUYỆT ĐỐI CẤM** bấm Tiếp tục và nhập mã OTP mở phiên trên thiết bị lạ.

---

## 4. Quy Trình Đăng Xuất Sạch (Clean Multi-Account Logout) Khi Dính Nick Ký Sinh
Khi một máy lỡ bị đăng nhập nhầm 1 nick ký sinh trên thiết bị đang có nhiều nick active:
- **Cơ chế TikTok v46.x:** Khi vào Settings -> Đăng xuất, TikTok **CHỈ ĐĂNG XUẤT ĐÚNG NICK ACTIVE HIỆN TẠI** và tự động chuyển về 1 nick hợp lệ trước đó. Toàn bộ các nick còn lại trong Account Switcher **KHÔNG BỊ MẤT**.
- **Các bước thực thi (đã nghiệm thu thực tế Máy 201):**
  1. Vào tab Hồ sơ: tap `(972, 1857)`.
  2. Mở Menu 3 gạch góc trên phải: tap `(1002, 144)`.
  3. Chọn *"Cài đặt và quyền riêng tư"* (dùng WinRT OCR định vị hoặc tap `(576, 1248)`).
  4. Cuộn xuống đáy trang Settings: swipe từ `(540, 1600)` lên `(540, 300)` 4 lần.
  5. Tap nút *"Đăng xuất"* tại `(292, 1662)`.
  6. Tại popup xác nhận *"Bạn có chắc chắn muốn đăng xuất?"*, tap nút đỏ *"Đăng xuất"* tại `(540, 1664)`.
  7. **Nghiệm thu (Gate 6):**
     - Mở Account Switcher tại dropdown tên tài khoản trên cùng.
     - Chụp ảnh màn hình (`MEDIA:...`) chứng minh nick ký sinh đã biến mất và toàn bộ danh sách nick gốc của máy được bảo toàn nguyên vẹn.
     - Force-stop và đưa máy về Home.
