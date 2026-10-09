# Case 58: Evidence-First OCR Readback Gate, Fake Password Fallback Elimination & Hotmail Recovery (17/09/2026)

## 1. Triệu chứng & Sự cố nghiêm trọng
- **Sự cố 1 (Suy diễn mù không đọc ảnh):** Agent chụp ảnh màn hình hiện trường lỗi của TikTok (`SparkActivity`/WebView) có dòng chữ đỏ *"Số lần nhập sai tài khoản hoặc mật khẩu đã đạt giới hạn. Hãy thử lại sau 29m"*, nhưng Agent không đọc ảnh mà tự suy diễn lý thuyết là *"nút Tiếp bị mất liên kết callback JavaScript"*. Bị user chấn chỉnh gay gắt: *"Sao mày gửi ảnh cho tao mà tự mày không OCR đọc ảnh xem suy luận đúng không... có cơ chế nào kẹt ở đâu tự dump ảnh đọc kĩ trước khi kết luận xàm không, tốn quota cũng được"*.
- **Sự cố 2 (Lưu pass ảo làm hỏng dữ liệu farm):** Toàn bộ các tài khoản Hotmail reg ngày 25/08 khi đăng nhập lại đều báo sai mật khẩu TikTok. User chất vấn: *"Pass lưu excel do script ghi làm sao mà sai... vấn đề mày không fix cái này thì cả farm sai pass sau này bán cho khách ăn lồn cả lũ à... tao nhớ là tao sửa ép không có pass là để trống rồi mà"*.
- **Sự cố 3 (Outlook App WebView kẹt redirect):** App Outlook trên Samsung S7 bị redirect sang trang tạo tài khoản mới thay vì login, và Hotmail báo sai pass cần khôi phục qua email `thanhdatbui1995@gmail.com`.

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Lỗ hổng kiểm soát bằng chứng:** Agent chỉ dựa vào cây Accessibility XML (hoặc chỉ gửi ảnh cho User xem) mà không tự phân tích hình ảnh. Nhiều thông báo lỗi, chữ đỏ, Canvas, hoặc WebView của TikTok/Google không xuất hiện trong XML mà chỉ hiển thị trên màn hình rendering.
2. **Lỗ hổng code đè pass ảo trong `social_reg_v1.py`:**
   - Dù ở dòng 8676 đã có rule: *Nếu flow không có màn nhập pass (email-only/OTP) thì để trống `tiktok_pw = ""`*.
   - Nhưng ở hàm `ensure_profile_completed_and_track` (dòng 5538) lại còn sót dòng fallback tai hại:
     `tiktok_pw = tiktok_pw or (make_tiktok_password(mail_pw) if mail_pw else "")`
   - Khi TikTok skip màn tạo pass, hàm này tự động sinh ra một chuỗi mật khẩu random ngẫu nhiên rồi ghi đè vào cột `PASS` của Excel. Trong khi đó tài khoản trên server TikTok chưa từng có mật khẩu.
3. **Hotmail security password rotation:** Các tài khoản Hotmail sau đợt change-info bảo mật có thể bị đổi pass trên server Microsoft, cần cơ chế khôi phục qua IMAP Gmail.

## 3. Bản vá kiến trúc & Kỷ luật bắt buộc (Rules)

### A. EVIDENCE-FIRST OCR READBACK GATE (BẮT BUỘC TRƯỚC KHI BÁO CÁO)
- Mọi trường hợp chụp ảnh màn hình hiện trường lỗi (`m30_*.png`, `failure_evidence`):
  1. **SCREENSHOT:** Chụp ảnh đóng băng hiện trường tại chỗ trước khi cleanup/teardown.
  2. **WinRT OCR READBACK:** BẮT BUỘC gọi `winrt_ocr.py` đọc 100% text trên bức ảnh vừa chụp.
  3. **KEYWORD SCAN:** Quét các từ khóa báo động: *"nhập sai"*, *"giới hạn"*, *"thử lại sau"*, *"locked"*, *"incorrect password"*, *"captcha"*, *"phiên đã hết hạn"*, *"không thể thay đổi cài đặt vì lý do bảo mật"*.
  4. **SO KHỚP BẰNG CHỨNG:** Nếu có thông báo lỗi, BẮT BUỘC trích nguyên văn câu thông báo đó làm bằng chứng số 1. **CẤM TUYỆT ĐỐI** nhìn XML rồi suy đoán lý thuyết.

### B. XÓA BỎ HOÀN TOÀN FALLBACK TỰ CHẾ PASS ẢO (`social_reg_v1.py`)
- Tại dòng 5538 của `social_reg_v1.py`, sửa thành:
  ```python
  # User rule 2026-08-16: Nếu flow không có pass, BẮT BUỘC ĐỂ TRỐNG.
  # CẤM TUYỆT ĐỐI fallback tự chế pass bằng make_tiktok_password(mail_pw).
  tiktok_pw = (tiktok_pw or "").strip()
  ```
- Nếu tài khoản chưa từng qua màn tạo mật khẩu trên app TikTok: Cột `PASS` trong `taikhoan_dat_v2_updated .xlsx` **BẮT BUỘC ĐỂ TRỐNG (`None` / `""`)**.

### C. KHÔI PHỤC HOTMAIL QUA `thanhdatbui1995@gmail.com`
- Khi Hotmail báo sai pass trên web/app Microsoft:
  1. Bấm vào link `Gửi mã đến th*****@gmail.com`.
  2. Nhập đầy đủ địa chỉ: `thanhdatbui1995@gmail.com` ➔ Bấm `Gửi mã`.
  3. Gọi IMAP tự động (`flows.hotmail_recovery.poll_latest_otp` hoặc script IMAP) đọc thư từ `Nhóm tài khoản Microsoft <account-security-noreply@accountprotection.microsoft.com>`.
  4. Nhập 6 số OTP ➔ Vượt qua màn hình passkey (bấm Back một lần) ➔ Bấm nút `Có` (Duy trì đăng nhập) tại tọa độ `(540, 1629)` ➔ Đăng nhập thành công vào `outlook.live.com/mail/0/inbox`.
