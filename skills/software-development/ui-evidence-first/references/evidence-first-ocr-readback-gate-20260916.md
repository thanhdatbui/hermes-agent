# Evidence-First OCR Readback Gate & Anti-Blind-Diagnosis Protocol (2026-09-16)

## Bối cảnh Sự cố (Incident Context)
- **Hiện tượng:** Trong phiên đăng nhập TikTok v46.6.3 trên Samsung Galaxy S7 (Máy 30), tài khoản đăng nhập gặp màn hình con `SparkActivity` (WebView container). Trên màn hình hiện rõ ràng viền đỏ và dòng chữ cảnh báo lỗi màu đỏ:
  `"Số lần nhập sai tài khoản hoặc mật khẩu đã đạt giới hạn. Hãy thử lại sau 29m."`
- **Sai lầm chết người của Agent:**
  - Agent chỉ dump cây accessibility XML (`capture_atx_session_ui`). Trong Android WebView/Canvas hoặc custom view của TikTok, dòng chữ lỗi màu đỏ không xuất hiện dưới dạng text node trong accessibility tree.
  - Agent **KHÔNG tự chạy tool OCR đọc lại bức ảnh screencap vừa chụp**, dẫn đến suy luận mù quáng và kết luận xàm: *"Nút Tiếp bị mất liên kết callback JavaScript trong SparkActivity"*.
  - User bức xúc chất vấn: *"Ủa t cài rule khi mày gửi ảnh cho t thì tự mày phải ocr đọc ảnh xem suy luận của mày đúng k đã chứ. Hay có cơ chế nào cho mày kẹt ở đâu mày tự dump ảnh đọc kĩ trc khi kết luận xàm k. Tốn quota cũng đc"*.

---

## 5 Điều khoản Kỷ luật: EVIDENCE-FIRST OCR READBACK GATE (EOG Protocol)

### 1. RULE EOG-001 — MEDIA ≠ EVIDENCE (Ảnh chụp chưa đọc = Chưa có bằng chứng)
- Việc chỉ chụp ảnh screencap rồi lưu ra file hoàn toàn **KHÔNG CÓ GIÁ TRỊ BẰNG CHỨNG** nếu Agent chưa trực tiếp đọc và phân tích nội dung trên ảnh.
- CẤM TUYỆT ĐỐI kết luận nguyên nhân lỗi chỉ dựa vào accessibility XML khi hiện trường có màn hình WebView, Canvas, hoặc đồ họa tuỳ biến.

### 2. RULE EOG-002 — BẮT BUỘC OCR READBACK (Quy trình đóng băng và đọc lại)
Mọi kết luận về lỗi, kẹt màn hình, hoặc trước khi gửi `MEDIA:<path>` cho User BẮT BUỘC phải đi qua luồng tuần tự:
```text
SCREENSHOT 
  ➔ WinRT OCR READBACK (scripts/winrt_ocr.py hoặc WinRT API)
  ➔ EXTRACT 100% TEXT
  ➔ KEYWORD SCAN & CLASSIFICATION
  ➔ HYPOTHESIS VALIDATION (So khớp giả thuyết)
  ➔ CONCLUSION & REPORT
  ➔ SEND MEDIA:<path>
```
**Không có kết quả OCR text từ ảnh = CẤM phát ngôn hoặc đưa ra nhận định nguyên nhân.**

### 3. RULE EOG-003 — ERROR KEYWORD SCAN GATE
Text bóc tách từ OCR bắt buộc phải được quét tự động qua các nhóm từ khóa lỗi người dùng:
- `sai mật khẩu`, `incorrect password`, `wrong password`
- `giới hạn`, `đạt giới hạn`, `limit reached`, `too many attempts`
- `thử lại sau`, `try again after`, `29m`, `30m`
- `không thể thay đổi cài đặt vì lý do bảo mật`, `security reasons`
- `captcha`, `recaptcha`, `xác nhận bạn không phải là người máy`
- `tài khoản không tồn tại`, `account does not exist`
- `mã không đúng`, `mã pin không hợp lệ`, `expired`

**Nguyên tắc tối cao:** Nếu OCR phát hiện bất kỳ câu thông báo lỗi nào trên giao diện, **BẮT BUỘC coi câu thông báo đó là BẰNG CHỨNG GỐC CỐT LÕI (Primary Evidence)**. Tuyệt đối CẤM suy diễn sang lỗi kỹ thuật trừu tượng ("mất callback JS", "kẹt event", "lỗi layout") khi chưa loại trừ thông báo trực quan này.

### 4. RULE EOG-004 — HYPOTHESIS CONTRADICTION CIRCUIT BREAKER
Mọi chẩn đoán phải tuân thủ công thức:
`Claim (Khẳng định) = OCR Text Trích Dẫn + XML State + Action Event`
- Nếu kết luận mâu thuẫn với chữ hiển thị trên ảnh (ví dụ: ảnh báo limit mật khẩu nhưng kết luận do nút không ăn), Circuit Breaker tự động kích hoạt: **HỦY BỎ TOÀN BỘ KẾT LUẬN CŨ**, bắt buộc trích nguyên văn thông báo lỗi từ OCR vào báo cáo gửi User.

### 5. RULE EOG-005 — REPORT FORMAT
Báo cáo gửi User khi gặp lỗi hoặc kẹt màn hình bắt buộc có cấu trúc:
1. `MEDIA:<path_anh>` (dòng đầu tiên).
2. `Theo OCR đọc lại hiện trường:`
   ```text
   "<Trích nguyên văn dòng text lỗi/cảnh báo bóc tách từ ảnh>"
   ```
3. `Kết luận:` Nêu đúng bản chất theo câu chữ trên ảnh, không suy diễn mò.

---

## Tool thực thi chuẩn trên Windows
Sử dụng script WinRT OCR có sẵn, không phụ thuộc pip package nặng:
```bash
python "C:/Users/Kibe/AppData/Local/hermes/skills/productivity/windows-native-ocr/scripts/winrt_ocr.py" "<path_to_screenshot>" --lang vi-VN
```
*(Nếu thiếu gói vi-VN, script tự fallback en-US vẫn bóc tách rất tốt các từ khóa tiếng Việt và số liệu).*
