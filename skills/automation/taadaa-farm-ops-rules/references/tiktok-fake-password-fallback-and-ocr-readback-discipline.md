# Cảnh giác lỗi lệch mật khẩu TikTok trong Excel & Kỷ luật Evidence-First OCR Readback

## 1. Bản chất sự cố: "Lệch pass ảo" khi reg TikTok (User Rule 2026-08-16)

### A. Triệu chứng
- Khi login tài khoản TikTok trên thiết bị mới bằng mật khẩu lưu trong file Excel (`taikhoan_dat_v2_updated .xlsx` / `Tik1..8.xlsx`), app báo đỏ:
  `Sai tài khoản hoặc mật khẩu. Còn N lần nhập. Hãy thử lại.` hoặc `Số lần nhập sai tài khoản hoặc mật khẩu đã đạt giới hạn. Hãy thử lại sau 29m.`
- Dù tài khoản do chính hệ thống/script reg tạo ra và ghi vào Excel, mật khẩu thực tế trên server TikTok lại không khớp.

### B. Nguyên nhân gốc rễ (Root Cause)
1. **TikTok Skip Password Screen:** Trong nhiều luồng đăng ký bằng email/OTP hoặc one-tap signup, app TikTok bỏ qua màn hình tạo mật khẩu và đưa thẳng vào Profile (`email-only flow`).
2. **Con bug Fallback tự chế pass:** Dù user đã chốt rule ngày 2026-08-16 là "Nếu không có màn tạo pass thì để trống pass", ở hàm ghi file cuối cùng `ensure_profile_completed_and_track` (trong `social_reg_v1.py`) vẫn còn sót dòng:
   ```python
   tiktok_pw = tiktok_pw or (make_tiktok_password(mail_pw) if mail_pw else "")
   ```
   Dòng này tự động sinh ra một chuỗi mật khẩu random ngẫu nhiên và ghi đè vào cột `PASS` của Excel!
3. **Hậu quả:** File Excel có mật khẩu trông rất mạnh/hợp lệ, nhưng trên server TikTok tài khoản này **chưa từng được đặt mật khẩu**. Khi đăng nhập bằng pass trong Excel sẽ fail 100%.

### C. Giải pháp phòng ngừa & Xử lý
- **Trong script reg:** BẮT BUỘC xóa bỏ triệt để đoạn fallback `make_tiktok_password`. Nếu flow không nhập pass, `tiktok_pw` PHẢI là chuỗi rỗng `""` hoặc `None`.
- **Đối với tài khoản chưa có pass thật:** Bắt buộc đăng nhập bằng mã OTP gửi về Email (qua Microsoft Graph API hoặc App Mail), sau đó vào Cài đặt TikTok ➔ Đặt mật khẩu lần đầu và cập nhật mật khẩu thật đó vào Excel.

---

## 2. Kỷ luật Evidence-First OCR Readback (Chống kết luận xàm / suy diễn mù)

### A. Triệu chứng vi phạm của Agent
- Agent chụp ảnh màn hình lỗi gửi cho user nhưng **không tự đọc ảnh**, chỉ nhìn vào accessibility XML rồi suy diễn lý thuyết sai lệch (ví dụ: màn hình hiện chữ đỏ "Số lần nhập sai đã đạt giới hạn. Thử lại sau 29m", nhưng Agent lại kết luận là "nút Tiếp tục bị mất callback JavaScript").
- Bị user bắt lỗi: *"Ủa t cài rule khi mày gửi ảnh cho t thì tự mày phải ocr đọc ảnh xem suy luận của mày đúng k đã chứ. Hay có cơ chế nào cho mày kẹt ở đâu mày tự dump ảnh đọc kĩ trc khi kết luận xàm k. Tốn quota cũng đc"*.

### B. Quy trình bắt buộc trước khi đưa ra kết luận (Mandatory Inspection Loop)
Mỗi khi phát hiện kẹt/lỗi trên thiết bị:
1. **FREEZE SCREENSHOT:** Chụp screencap hiện trường đóng băng ngay tại millisecond phát hiện lỗi (`adb exec-out screencap -p > /path/error.png`).
2. **WinRT OCR READBACK:** BẮT BUỘC chạy WinRT OCR đọc 100% nội dung chữ có trên ảnh:
   ```bash
   python "C:/Users/Kibe/AppData/Local/hermes/skills/productivity/windows-native-ocr/scripts/winrt_ocr.py" "/path/error.png"
   ```
3. **KEYWORD ERROR SCAN:** Rà soát bắt buộc các cụm từ cảnh báo trên kết quả OCR:
   - `nhập sai`, `giới hạn`, `thử lại sau`, `sai mật khẩu`, `incorrect password`, `limit`
   - `phiên đã hết hạn`, `lý do bảo mật`, `không thể thay đổi cài đặt`
   - `captcha`, `xác minh đó là bạn`, `tài khoản không tồn tại`
4. **ĐỐI SOÁT & BÁO CÁO NGUYÊN VĂN:** 
   - Nếu OCR phát hiện thông báo lỗi, BẮT BUỘC trích nguyên văn câu thông báo đó làm bằng chứng số 1 trong báo cáo.
   - TUYỆT ĐỐI CẤM chỉ nhìn accessibility tree XML rồi suy đoán cảm tính (vì chữ đỏ báo lỗi, WebView canvas thường không hiện trong node XML accessibility).
