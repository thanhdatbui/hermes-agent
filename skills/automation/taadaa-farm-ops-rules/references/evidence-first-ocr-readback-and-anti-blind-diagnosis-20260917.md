# Case 56: Evidence-First OCR Readback Gate & Anti-Blind Diagnosis (17/09/2026)

## 1. Triệu chứng & Nguyên nhân sự cố
- **Triệu chứng:** Khi thử nghiệm đăng nhập TikTok Máy 30, màn hình hiển thị dòng chữ đỏ to rõ:
  `"Số lần nhập sai tài khoản hoặc mật khẩu đã đạt giới hạn. Hãy thử lại sau 29m."`
  và `"Sai tài khoản hoặc mật khẩu. Còn 4 lần nhập. Hãy thử lại."`
- **Lỗi nghiêm trọng của Agent:**
  - Agent chụp ảnh gửi User nhưng **không tự chạy OCR đọc lại chính ảnh mình vừa chụp**.
  - Chỉ nhìn vào cây XML UI (thành phần WebView/Canvas của `SparkActivity` không nhả text đỏ ra XML accessibility tree).
  - Tự suy diễn lý thuyết sai lệch: *"Nút Tiếp bị mất liên kết callback JavaScript trong SparkActivity"*, khiến User bức xúc: *"Bằng chứng như l... vậy, tự ocr đọc ảnh xem suy luận đúng không đã chứ!"*.

## 2. Kỷ luật bắt buộc: EVIDENCE-FIRST OCR READBACK GATE
Quy trình bất di bất dịch khi chụp ảnh hiện trường lỗi/kẹt:
```
SCREENSHOT 
  → WinRT OCR (winrt_ocr.py) 
  → KEYWORD SCAN (nhập sai, giới hạn, thử lại sau, locked, lỗi, captcha, phiên đã hết hạn)
  → SO KHỚP KẾT LUẬN
  → MỚI ĐƯỢC PHÁT NGÔN / GỬI MEDIA
```

### Script thực thi chuẩn (Zero install trên Windows):
```bash
python "C:/Users/Kibe/AppData/Local/hermes/skills/productivity/windows-native-ocr/scripts/winrt_ocr.py" "<đường_dẫn_ảnh.png>"
```

### Checklist 3 câu hỏi bắt buộc trước khi phát ngôn:
1. Đã chạy WinRT OCR trên chính ảnh vừa chụp chưa? (Chưa -> CẤM KẾT LUẬN).
2. OCR có phát hiện thông báo đỏ / cảnh báo nào của app không? (Có -> Trích nguyên văn làm bằng chứng số 1).
3. Kết luận có bằng chứng trực quan hỗ trợ không? (Không -> TUYỆT ĐỐI CẤM suy đoán "lỗi JS/kẹt nút").

## 3. Bản vá gốc rễ: Chống sinh Pass ảo khi Reg TikTok (`social_reg_v1.py`)
- **Nguyên nhân gốc rễ dàn nick reg bị sai pass:**
  Khi reg TikTok bằng email, nếu app bỏ qua bước tạo mật khẩu (flow email-only/OTP), `tiktok_pw` bị rỗng. Script cũ tại `ensure_profile_completed_and_track` có đoạn fallback tai hại:
  `tiktok_pw = tiktok_pw or (make_tiktok_password(mail_pw) if mail_pw else "")`
  -> Tự sinh chuỗi pass random mới tinh ghi vào Excel trong khi server TikTok chưa từng có pass này!
- **Quy tắc bất biến:**
  Nếu app TikTok không qua bước tạo pass -> Cột `PASS` trong Excel BẮT BUỘC ĐỂ TRỐNG (`None` hoặc `""`). TUYỆT ĐỐI CẤM sinh pass ảo ghi đè.
