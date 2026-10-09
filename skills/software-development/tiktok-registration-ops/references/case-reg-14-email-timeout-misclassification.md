# Case REG-14: Phân Loại Lỗi Form Email Timeout Loading Chống Báo Nhầm "Đã Có Tài Khoản TikTok" (2026-09-13)

## 1. Vị trí áp dụng
- `social_reg_v1.py` (`fill_email_and_next`, `detect_after_continue`).
- `_run_all_targets.py` / `scripts/run_night_chain_pipeline.py`.
- Tài liệu quy chuẩn farm: `D:/Taadaa/Tiktok_Reg/docs/farm-automation-cases.md`.

## 2. Hiện tượng lỗi / Sự cố thực tế
Khi chạy batch reg TikTok qua `_run_all_targets.py` hoặc `social_reg_v1.py`, script ném ngoại lệ:
`RuntimeError: [07] Tat ca 1 email cua STT X da co TK TikTok`
hoặc kết luận toàn bộ email ứng viên đã có tài khoản TikTok, dù email vừa mới mua/tạo 100% chưa từng đăng ký TikTok.

## 3. Nguyên nhân cốt lõi (Anti-Pattern)
1. **Fallback mù quáng vào giả định tiêu cực:**
   Sau khi gõ email và bấm "Tiếp tục", nếu app lag, mạng chậm, hoặc TikTok hiển thị spinner loading quá 12s, hàm `detect_after_continue()` rơi vào timeout và trả về `"unknown"` / `None`.
2. **Không phân biệt lỗi mạng/timeout với lỗi tồn tại tài khoản:**
   Hàm `fill_email_and_next()` không kiểm tra cụ thể chuỗi báo lỗi tồn tại (`"Tài khoản này đã tồn tại"`, `"Email đã được đăng ký"`, v.v.). Khi không vào được màn hình OTP/Password mà lại kết thúc vòng lặp candidates, code tự động `raise RuntimeError(f"[07] Tat ca {len(candidates)} email cua STT {stt} da co TK TikTok")`.
3. **Hậu quả vận hành:**
   Gây hiểu lầm nghiêm trọng rằng kho mail bị trùng hoặc máy bị lỗi tracking, dẫn đến thao tác sai lệch là đánh dấu loại trừ mail còn sống, trong khi thực tế sang đợt sau khi mạng ổn định thì cùng email đó đăng ký thành công 100%.

## 4. Giải pháp chuẩn (Case Fix)
1. **Kiểm tra minh thị thông báo tài khoản tồn tại (Explicit Account Exists Guard):**
   Chỉ kết luận email đã có tài khoản khi UI XML/OCR xuất hiện chính xác các cụm từ:
   - `"Tài khoản đã tồn tại"` / `"Tài khoản này đã được liên kết"` / `"Account already exists"`
   - `"Email này đã được sử dụng"` / `"Email already registered"`
2. **Cờ theo dõi Timeout / Network Error:**
   Thêm biến cờ `had_timeout_error = True` khi `detect_after_continue()` trả về `unknown`/timeout.
3. **Ném ngoại lệ chính xác theo nguyên nhân gốc rễ:**
   - Nếu do timeout/mạng lag: `raise RuntimeError(f"[07] Khong the xac dinh trang thai email cho STT {stt} do timeout/mang cham khi bam Tiep tuc")`.
   - Giữ nguyên trạng thái email ở dạng pending/retry cho phiên sau thay vì đánh dấu hỏng kho mail.
4. **Quy tắc ghi chép tài liệu:**
   Luôn cập nhật Case REG-14 vào Mục lục và Phần 5 của `docs/farm-automation-cases.md`.
