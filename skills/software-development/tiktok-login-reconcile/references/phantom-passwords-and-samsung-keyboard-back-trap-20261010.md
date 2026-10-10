# Khám Nghiệm Mật Khẩu Ma (Phantom Password) & Bẫy Samsung Keyboard Back (2026-10-10)

## 1. Hiện Tượng & Nguyên Nhân "Mật Khẩu Ma" (Phantom Password)
Khi chạy runner đăng nhập tài khoản TikTok từ workbook/tracking (`taikhoan_dat_v2_updated .xlsx` / `taikhoan_run_safe.xlsx`), tool báo lỗi `Mật khẩu sai` / `WRONG_TIKTOK_PASSWORD` mặc dù workbook có lưu mật khẩu đầy đủ.

### Căn nguyên cốt lõi trong code lịch sử (Các nick reg trước ngày 30/09/2026):
1. **TikTok không yêu cầu đặt mật khẩu khi reg qua Email OTP:**
   Khi tài khoản được đăng ký qua luồng Email OTP (Hotmail/Gmail), TikTok cho vào thẳng trang chủ mà không hiển thị màn hình tạo mật khẩu (`flow email-only / OTP`).
   Trong `social_reg_log.txt`:
   ```text
   [pw] Không có màn nhập password → KHÔNG lưu pass (để trống)
   ```
2. **Bug fallback trong code cũ (`social_reg_v1.py`):**
   Trong hàm `ensure_profile_completed_and_track()`, code cũ có dòng:
   ```python
   tiktok_pw = tiktok_pw or (make_tiktok_password(mail_pw) if mail_pw else "")
   ```
   Do `tiktok_pw` là chuỗi rỗng `""`, toán tử `or` kích hoạt và gọi `make_tiktok_password()` tự chế ra một chuỗi mật khẩu ngẫu nhiên (ví dụ `qk2A%Rt9Bm4J`, `tAq*K8Fcyy4&K`) và ghi đè vào file tracking kết quả (`tracking_result_stt*.json`) cũng như workbook Excel!
3. **Thực tế trên TikTok:** Tài khoản này **chưa từng được đặt mật khẩu thật**. Mật khẩu trong file Excel hoàn toàn là "mật khẩu ma" do tool tự sinh.

> **Ghi chú:** Từ ngày 30/09/2026 (commit `e51929d` & `31fc0fa`), bug này đã được chặn cho các nick mới. Tuy nhiên, toàn bộ nick reg trong giai đoạn tháng 8 - 9/2026 vẫn mang mật khẩu ma trong database/Excel.

---

## 2. Quy Trình Khám Nghiệm O(1) Khi Bị Báo Sai Mật Khẩu
1. Tra cứu thời điểm reg của nick trong `taikhoan_dat_v2_updated .xlsx` (cột `NGÀY TẠO`).
2. Mở `D:/Taadaa/Tiktok_Reg/social_reg_log.txt` hoặc tìm artifact `tracking_result_stt<N>_<email>.json`.
3. Kiểm tra log bước 8: Nếu thấy dòng `Không có màn nhập password → KHÔNG lưu pass (để trống)`, xác nhận 100% nick này không có mật khẩu trên TikTok.
4. **CẤM ĐOÁN MẬT KHẨU / CẤM THỬ ĐIỀN LẠI NHIỀU LẦN:** Tránh bị TikTok rate limit / khóa tài khoản tạm thời.

---

## 3. Quy Trình Khôi Phục Đăng Nhập Bằng Email OTP (`--otp-only`)
Với tài khoản mang mật khẩu ma, phương thức đăng nhập duy nhất là dùng **Mã xác minh Email**:
```bash
python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <ID_HOAC_EMAIL> --otp-only --ss
```

---

## 4. Bẫy Samsung Keyboard Dismiss Gây Văng Ra Launcher
- **Triệu chứng:** Runner fail với lỗi `STOPPED: [06_email_option] Không tìm thấy: Email / icon email`, dump UI cho thấy máy đang ở màn hình Home (`LauncherActivity`).
- **Nguyên nhân:** Trong hàm `dismiss_samsung_keyboard_tutorial()`: Khi kiểm tra thấy chuỗi package `"com.sec.android.inputmethod"` trong UI XML mà gửi mù `keyevent 4` (phím BACK), thiết bị Samsung S7 sẽ thoát khỏi TikTok ra ngoài màn hình chính. Package bàn phím Samsung thường trú thường xuyên trong system dump, không đồng nghĩa với tutorial popup đang hiển thị.
- **Khắc phục:** Không gửi `keyevent 4` trừ khi có marker tutorial/skipButton rõ ràng, và luôn kiểm tra foreground package phải là TikTok (`com.ss.android.ugc.trill`) sau thao tác dismiss.
