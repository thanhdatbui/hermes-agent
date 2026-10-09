# Bẫy Mật Khẩu Random Ảo Trong Đăng Ký TikTok & Kỷ Luật Evidence OCR Readback

## 1. Sự cố sai mật khẩu toàn farm (Phát hiện 17/09/2026 trên Máy 30)

### Hiện tượng:
- Các tài khoản phôi reg từ tháng 8/2026 (chưa bật 2FA) khi đăng nhập lại trên thiết bị mới (S7 Máy 30) bị TikTok báo đỏ:
  `Sai tài khoản hoặc mật khẩu. Còn 5 lần nhập.` hoặc `Tài khoản không tồn tại`.
- Trong file Excel `taikhoan_dat_v2_updated .xlsx`, cột PASS vẫn có chuỗi mật khẩu phức tạp đầy đủ (ví dụ: `&h7i9UAG*B$2#`, `FN4WstbpPd8O@9Y`).

### Nguyên nhân gốc rễ (Root Cause):
1. **Lỗi logic trong script reg (`social_reg_v1.py` dòng 5538):**
   ```python
   tiktok_pw = tiktok_pw or (make_tiktok_password(mail_pw) if mail_pw else "")
   ```
2. **Cơ chế phát sinh bug:**
   - Trong luồng đăng ký TikTok bằng email, nếu TikTok điều hướng theo nhánh OTP-only hoặc bỏ qua bước tạo mật khẩu tại thời điểm reg, biến `tiktok_pw` bị rỗng.
   - Khi chạy đến bước ghi nhận tracking vào Excel (`ensure_profile_completed_and_track`), script tự ý gọi hàm `make_tiktok_password(...)` để sinh một mật khẩu random HOÀN TOÀN MỚI.
   - Mật khẩu này được ghi vào cột PASS của Excel, nhưng trên server TikTok tài khoản CHƯA TỪNG ĐƯỢC ĐẶT MẬT KHẨU NÀY.
   - Dẫn đến lệch dữ liệu: Excel lưu pass ảo, server TikTok không khớp.

### Phạm vi ảnh hưởng:
- **296 tài khoản ĐÃ BẬT 2FA:** An toàn 100% vì luồng `tiktok-add-bao-mat-f2a` bắt buộc đổi mật khẩu thực tế thành công mới kích hoạt được 2FA Authenticator.
- **~299 tài khoản CHƯA BẬT 2FA:** Nguy cơ dính pass ảo. Phải coi mật khẩu trong Excel là unverified cho đến khi chạy qua flow reset/add 2FA.

---

## 2. Kỷ luật EVIDENCE-FIRST OCR READBACK (Gate chống kết luận mù)

### Bối cảnh sự cố:
- Agent chụp ảnh hiện trường màn hình TikTok có dòng chữ đỏ:
  `Số lần nhập sai tài khoản hoặc mật khẩu đã đạt giới hạn. Hãy thử lại sau 29m.`
- Do chỉ nhìn accessibility XML (vốn không xuất hiện text đỏ do thuộc WebView/Canvas), Agent không chạy OCR đọc lại ảnh, dẫn đến kết luận mù rằng: *"Nút Tiếp bị mất callback JavaScript"*.
- User bức xúc yêu cầu siết rule: Đã chụp ảnh thì BẮT BUỘC phải OCR đọc lại trước khi phát ngôn.

### Quy trình bắt buộc (EVIDENCE-FIRST OCR READBACK GATE):
```text
[BƯỚC 1] SCREENSHOT (Chụp ảnh đóng băng hiện trường lỗi trước cleanup/teardown).
    ↓
[BƯỚC 2] WinRT OCR READBACK (BẮT BUỘC gọi winrt_ocr.py đọc 100% text trên ảnh).
    ↓
[BƯỚC 3] KEYWORD SCAN (Quét các từ khóa: sai, mật khẩu, giới hạn, thử lại sau, limit, lock, captcha, lỗi).
    ↓
[BƯỚC 4] SO KHỚP KẾT LUẬN (Nếu ảnh có thông báo lỗi người dùng -> Trích dẫn nguyên văn làm bằng chứng số 1).
    ↓
[BƯỚC 5] GỬI MEDIA CHO USER KÈM DÒNG MEDIA: Ở DÒNG ĐẦU TIÊN.
```

### Lệnh chạy OCR WinRT nhanh trên Windows:
```bash
python "C:/Users/Kibe/AppData/Local/hermes/skills/productivity/windows-native-ocr/scripts/winrt_ocr.py" "D:/path/to/screenshot.png"
```
CẤM TUYỆT ĐỐI suy luận mò từ XML khi chưa chạy OCR đối soát ảnh.
