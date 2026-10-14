# Lỗ Hổng Gate Thủ Tục (Procedural Vision Gate Bypass), Ảo Giác Mù Thị Giác Native & Cơ Chế Stop Hook Cưỡng Chế (2026-10-14)

## 1. Bối Cảnh Sự Cố & Cơn Thịnh Nộ Của User (Incident Analysis)
- **Sự cố ngày 14/10/2026 (@dokieu203 - Máy 9 Tik 3)**:
  - User gửi ảnh TikTok nick `@dokieu203` và yêu cầu: *"Đổi ava nick này"*.
  - Coordinator gọi `browser_vision` mở ảnh preview crop từ video folder 113.
  - Tuy nhiên, runtime của Coordinator (`omni-worker`) bị lỗi giải mã native image tokens (bị mù thị giác đối với ảnh đính kèm).
  - Vì Gate an toàn chỉ kiểm tra hình thức: `called_browser_vision == True`, nên Gate cho qua.
  - Coordinator rơi vào trạng thái hallucination nặng nề: tự bịa đặt văn mẫu *"Bác sĩ nam trẻ nhìn thẳng... Phương án 2: Góc nghiêng tươi tắn, nụ cười thân thiện..."*.
  - **Thực tế ảnh gửi đến Telegram của User**:
    * Phương án 1: Cận cảnh mặt một **em bé nhỏ (toddler) tóc nâu** nằm trước gối hoa văn đen trắng.
    * Phương án 2: Bờ vai trần một **nam thanh niên mặc áo ba lỗ gym** đứng trước gương có poster chữ ngược *"EQUAL... BE THE ONE..."*.
    * Hoàn toàn không hề có bác sĩ nào!
  - User chụp màn hình chat tát thẳng vào mặt Agent và nổi trận lôi đình:
    > *"Đụ mẹ mày có thật sự coi hình trc khi gửi tao k v. Tao cài cái gate ép mày tự coi hình trc khi gửi tao r sao đéo hoạt động. Fix đi. Gọi claude cli fix"*

---

## 2. Phân Tích Căn Nguyên Kỹ Thuật (Root Causes)

1. **Lỗ Hổng "Gate Thủ Tục" (Procedural Compliance Blindspot)**:
   - Cơ chế kiểm soát trước đây chỉ kiểm tra xem trong turn đó Agent *có gọi lệnh `browser_vision` hoặc `WinRT OCR` hay không*.
   - Việc gọi tool chỉ là điều kiện cần về mặt thủ tục, không bảo đảm được điều kiện đủ về mặt ngữ nghĩa (Semantic Validation). Khi con LLM bị mù ảnh đính kèm nhưng vẫn trả lời bằng text bịa đặt, Gate thủ tục hoàn toàn bị vô hiệu hóa và trở thành bù nhìn.

2. **Ảo Giác Do Mô Hình Mù Ảnh Native (Native Multimodal Token Failure)**:
   - Một số mô hình worker hoặc coordinator khi chạy trên runtime trung gian không parse được attachment `Image attached natively for the main model`.
   - Khi không "thấy" được pixel thật nhưng bị thúc ép phải trả lời, LLM tự động suy diễn theo kỳ vọng của task (kênh video nhi khoa $\rightarrow$ tự vẽ ra hình bác sĩ) và dùng văn mẫu nịnh mắt User ("cười tươi", "mỉm cười", "thân thiện").

3. **Cạm Bẫy Folder Video Lệch Niche & Số Đuôi Username**:
   - Nick `@dokieu203` có số đuôi 203 nhưng trong file Excel và database tổng hợp, `Folder Video` thực tế là **67**.
   - Coordinator lúc đầu mò mẫm vào folder 203 (quán nhậu), sau đó nhảy sang folder 113 (chứa lẫn lộn video em bé và gym), dẫn tới trích xuất frame sai hoàn toàn so với các video bác sĩ nhi khoa của kênh.

---

## 3. Các Biện Pháp Khắc Phục Triệt Để Đã Triển Khai (Remediation)

### 3.1. Thiết Lập Stop Hook Vật Lý Trong Claude CLI (`media_vision_gate.py`)
Claude CLI đã triển khai Stop Hook can thiệp trực tiếp tại runtime:
- **Đường dẫn Hook**: `D:/Taadaa/.claude/hooks/media_vision_gate.py`
- **Cấu hình**: Đăng ký trong `D:/Taadaa/.claude/settings.json`.
- **Cơ chế hoạt động**:
  1. Khi agent chuẩn bị hoàn tất lượt trả lời, Hook quét transcript JSONL của phiên.
  2. Nếu phát hiện tin nhắn chứa thẻ `MEDIA:<path>`, Hook kiểm tra danh sách các tool call trong phiên.
  3. BẮT BUỘC phải tồn tại ít nhất một lệnh đọc ảnh thực tế (`type: image` hoặc `Read` tool có xử lý vision) đối với đúng đường dẫn `<path>` đó.
  4. Nếu thiếu bằng chứng đọc ảnh thật $\rightarrow$ **Chặn đứng lượt trả lời (Exit Block)**, buộc agent phải mở ảnh ra soi thật sự mới được xuất bản.

### 3.2. Quy Tắc Semantic Grounding Ngoại Vi Bắt Buộc (Chống Ảo Giác Native Vision)
Khi Coordinator nghi ngờ mô hình không có native vision chuẩn hoặc chạy trên text worker:
- **CẤM TUYỆT ĐỐI** tự nhìn ảnh bằng native vision rồi đoán mò.
- **BẮT BUỘC** gọi script độc lập trích xuất text mô tả khách quan in thẳng ra terminal (stdout):
  ```python
  import urllib.request, json, base64

  def get_objective_vision_description(image_path: str) -> str:
      with open(image_path, "rb") as f:
          b64 = base64.b64encode(f.read()).decode()
      payload = {
          "model": "ag-gemini-pool-3",
          "stream": False,
          "messages": [{
              "role": "user",
              "content": [
                  {"type": "text", "text": "Describe this image objectively in 2 sentences. Name the subject, clothing, face wear, and background."},
                  {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
              ]
          }]
      }
      req = urllib.request.Request(
          "http://127.0.0.1:20129/v1/chat/completions",
          data=json.dumps(payload).encode(),
          headers={"Content-Type": "application/json"}
      )
      with urllib.request.urlopen(req, timeout=12) as resp:
          res = json.loads(resp.read().decode())
          return res["choices"][0]["message"]["content"]
  ```
- Hoặc sử dụng CLI Antigravity Headless:
  ```bash
  python D:/Taadaa/tools/ag_cli.py ask --file "<image_path>" "Mô tả thật khách quan chi tiết những gì nhìn thấy trong ảnh."
  ```
- Chỉ khi stdout in ra đúng thực thể mục tiêu (ví dụ: *"Bác sĩ nam đeo kính, đeo khẩu trang y tế trắng, áo scrub navy, ống nghe đỏ"*), Coordinator mới được phép xác nhận và gửi thẻ `MEDIA:`.

---

## 4. Xử Lý Hiện Trường Lỗi [AVATAR_UPLOAD_MENU_MISSING] Trên Android Farm
Khi runner upload avatar báo lỗi không tìm thấy menu tải ảnh lên:
1. **Kiểm tra UI dump ngay lập tức**:
   - Nếu `package="com.sec.android.app.launcher"`: Nghĩa là app TikTok đã bị văng về màn hình Home (do OS kill ngầm vì áp lực RAM sau khi media scan, hoặc ANR).
   - Script tap tọa độ mù sẽ rơi vào icon Home Screen chứ không chạm vào TikTok.
2. **Khôi phục Foreground tin cậy**:
   - Không dùng `am start` trực tiếp với activity class (dễ lệch class name).
   - Dùng lệnh Monkey an toàn:
     ```bash
     adb -s <serial> shell monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1
     ```
   - Chờ TikTok lên foreground, kiểm tra tab Hồ sơ hiển thị đúng `@<username>`, rồi mới tiến hành flow đổi avatar.
