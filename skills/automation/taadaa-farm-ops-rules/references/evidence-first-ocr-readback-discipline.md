# Kỷ luật Bằng chứng: Evidence-First OCR Readback Gate & Chống Suy Luận Mù

## Bối cảnh sự cố thực tế (17/09/2026)
Khi đăng nhập tài khoản TikTok trên thiết bị mới (Máy 30), Agent chụp ảnh hiện trường màn hình lỗi nhưng chỉ kiểm tra cây accessibility XML (`dumpsys` / ATX dump).
Do các màn hình WebView, SparkActivity hoặc giao diện Canvas của TikTok hiển thị dòng chữ đỏ thông báo lỗi trực tiếp lên lớp đồ họa mà không đưa text node vào cây XML accessibility của Android, Agent đã:
1. Không thấy text lỗi trong XML.
2. Không tự chạy OCR đọc lại chính bức ảnh vừa chụp.
3. Tự suy diễn lý thuyết mù quáng: *"Nút Tiếp bị mất liên kết callback JavaScript trong SparkActivity"*.
Trong khi thực tế trên ảnh có dòng chữ đỏ cảnh báo rất rõ:
- *"Số lần nhập sai tài khoản hoặc mật khẩu đã đạt giới hạn. Hãy thử lại sau 29m."*
- Hoặc *"Sai tài khoản hoặc mật khẩu. Còn 5 lần nhập. Hãy thử lại."*
- Hoặc *"Không thể thay đổi cài đặt vì lý do bảo mật, hãy thử lại sau"*.

User đã nghiêm khắc chất vấn:
> *"Ủa t cài rule khi mày gửi ảnh cho t thì tự mày phải ocr đọc ảnh xem suy luận của mày đúng k đã chứ. Hay có cơ chế nào cho mày kẹt ở đâu mày tự dump ảnh đọc kĩ trc khi kết luận xàm k. Tốn quota cũng đc"*
> *"Gì thế bằng chứng của mày như lồn v"*

---

## Quy trình bắt buộc (EVIDENCE-FIRST OCR READBACK GATE)

Mọi chẩn đoán lỗi trên giao diện thiết bị di động PHẢI tuân thủ luồng 5 bước khép kín:

```text
1. SCREENSHOT (Freeze screencap tại chỗ trước khi thoát/teardown)
   ↓
2. WinRT OCR READBACK (BẮT BUỘC gọi winrt_ocr.py đọc 100% text trên ảnh)
   ↓
3. KEYWORD SCAN (Quét bắt buộc các nhóm từ khóa báo lỗi/cảnh báo)
   ↓
4. HYPOTHESIS & ERROR MATCHING (So khớp giả thuyết với nguyên văn câu lỗi)
   ↓
5. REPORT & MEDIA (Chỉ phát ngôn và gửi MEDIA: khi đã có trích dẫn từ OCR)
```

---

## 1. Công cụ thực thi OCR trên Windows host
Sử dụng script WinRT OCR không phụ thuộc thư viện ngoài (zero install, dùng API Windows Media OCR có sẵn):
```bash
python "C:/Users/Kibe/AppData/Local/hermes/skills/productivity/windows-native-ocr/scripts/winrt_ocr.py" "<đường_dẫn_ảnh_tuyệt_đối>"
```

Đoạn mã Python tích hợp vào các script tự động/watchdog:
```python
import subprocess

def run_winrt_ocr(image_path: str) -> str:
    script = r"C:\Users\Kibe\AppData\Local\hermes\skills\productivity\windows-native-ocr\scripts\winrt_ocr.py"
    try:
        res = subprocess.run(["python", script, image_path], capture_output=True, text=True, timeout=30)
        return res.stdout.strip()
    except Exception as e:
        return ""
```

---

## 2. Danh mục từ khóa bắt buộc quét (Keyword Gate)
Sau khi nhận kết quả OCR, bắt buộc kiểm tra các nhóm từ khóa trước khi đưa ra bất kỳ kết luận nào:

1. **Nhóm mật khẩu / xác thực:**
   - `sai mật khẩu`, `mật khẩu sai`, `sai tài khoản`, `còn x lần nhập`, `incorrect password`, `invalid credentials`.
2. **Nhóm giới hạn / Rate limit:**
   - `giới hạn`, `đạt giới hạn`, `thử lại sau`, `sau 29m`, `too many attempts`, `rate limit`, `phiên đã hết hạn`.
3. **Nhóm bảo mật thiết bị lạ:**
   - `lý do bảo mật`, `không thể thay đổi cài đặt vì lý do bảo mật`, `security reason`, `unrecognized device`, `suspicious login`.
4. **Nhóm tồn tại tài khoản / định danh:**
   - `tài khoản không tồn tại`, `không tìm thấy tài khoản`, `user does not exist`, `account not found`.
5. **Nhóm Captcha / Chặn bot:**
   - `xác nhận bạn không phải là rô-bốt`, `tôi không phải là người máy`, `recaptcha`, `trượt để khớp`.

---

## 3. Điều khoản kỷ luật tối cao (Anti-Hallucination Invariants)

- **CẤM SUY LUẬN MÙ TỪ ACCESSIBILITY XML:** Tuyệt đối không được kết luận *"lỗi JS"*, *"mất event click"*, *"kẹt nút"* nếu trên ảnh màn hình hiển thị bất kỳ text màu đỏ hoặc thông báo dạng toast/canvas.
- **MEDIA ≠ EVIDENCE NẾU CHƯA OCR:** Gửi ảnh cho user mà không chạy OCR đọc ảnh để trích xuất bằng chứng xem ảnh nói gì bị coi là **hành vi cẩu thả và vi phạm quy chuẩn nghiêm trọng**.
- **TRÍCH NGUYÊN VĂN:** Trong tin nhắn báo cáo, bắt buộc phải trích nguyên văn thông báo lỗi mà OCR đọc được, ví dụ:
  `[Bằng chứng OCR]: "Sai tài khoản hoặc mật khẩu. Còn 5 lần nhập. Hãy thử lại."`
- **CIRCUIT BREAKER KHI LOGIN THỬ LẠI:**
  Khi chạy watchdog/batch thử lại các nick dính lỗi bảo mật: Thử tối đa 2 tài khoản, nếu cả 2 tài khoản liên tiếp fail (báo đỏ giới hạn hoặc sai pass) thì **BẮT BUỘC DỪNG TOÀN BỘ TIẾN TRÌNH NGAY LẬP TỨC**, cấm thử tiếp hàng loạt gây cháy IP hoặc nát farm.
