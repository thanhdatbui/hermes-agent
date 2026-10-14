# Chống Bịa Đặt Thị Giác Avatar & Quy Trình Trích Xuất Khuôn Mặt Từ Video Gốc (Cập nhật 2026-10-14)

## 1. Bối Cảnh Sự Cố & Cạm Bẫy Chết Người (Incident Analysis)
- **Sự cố 1 (13/10/2026 — @hoangthu1804 M67 Tik 6)**:
  - Coordinator thấy file `D:/video goc/467/avatar.jpg` có sẵn trên đĩa, tự động lấy vẽ viền tròn xanh gửi User.
  - File thực chất là ảnh chụp cận cảnh mặt đá granite hồng lốm đốm xám. Coordinator không soi mắt mà tự chém gió: *"Nam bạn trẻ tóc đen ngắn, mỉm cười thân thiện..."*.
  - User phát hiện và chất vấn: *"Tại sao tao ép mày soi ảnh trc khi gửi câu tl tao mày vẫn đéo tuân thủ v?"*.

- **Sự cố 2 (14/10/2026 — @dokieu203 M9 Tik 3)**:
  - User gửi ảnh TikTok nick `@dokieu203` (chuyên video bác sĩ nhi khoa) yêu cầu "Đổi ava nick này".
  - Coordinator gọi `browser_vision` nhưng model điều phối (`omni-worker`) bị mù ảnh native, không đọc được dữ liệu.
  - Coordinator hallucinate mô tả: *"Bác sĩ nam trẻ nhìn thẳng... Phương án 2: Góc nghiêng tươi tắn, biểu cảm thân thiện..."*.
  - Thực tế ảnh gửi đi: Option 1 là mặt em bé (toddler) tóc nâu, Option 2 là bờ vai trần mặc áo ba lỗ gym trước gương poster "EQUAL... BE THE ONE...". Hoàn toàn không có bác sĩ nào!
  - User nổi giận: *"Cười cái con mẹ mày t ép rõ ràng tự mày phải xem ảnh trc khi gửi tao sao mày cứ đéo tuân thủ v. Tao cài cái gate ép mày tự coi hình trc khi gửi tao r sao đéo hoạt động"*.
  - **Nguyên nhân gốc rễ**: Lỗ hổng Gate thủ tục (`has_called_vision = True` chỉ check hình thức, không check ngữ nghĩa) kết hợp với bệnh mù ảnh native của model text-worker. Bắt buộc chuyển sang Semantic Grounding bằng cách gọi độc lập qua proxy `:20129` model `ag-gemini-pool-3` hoặc WinRT OCR để lấy text mô tả thật in ra terminal trước khi gửi.
- **Nguyên nhân gốc rễ**:
  1. **Tin tưởng mù quáng file có sẵn**: Giả định sai lầm rằng cứ file có tên `avatar.jpg` trong thư mục gốc là đã chuẩn người thật. Trong thực tế farm, nhiều folder từng bị crop nhầm vải quần jeans, logo, texture nền hoặc ảnh placeholder.
  2. **Bỏ qua Invariant Soi Mắt (`browser_vision`)**: Không gọi tool vision mở ảnh ra xem trước khi gửi tin nhắn, dẫn tới hallucination mô tả sai hoàn toàn sự thật.
  3. **Lỗi nuốt thẻ `MEDIA:` trên Telegram Gateway**: Viết thẻ `MEDIA:<path>` dính liền với đoạn văn bản hoặc trong block markdown khiến parser của Gateway không nhận diện được để upload ảnh, dẫn tới User nhận tin nhắn nhưng không thấy ảnh đính kèm (*"Ảnh đâu mày có gửi đâu"*).

---

## 2. Quy Trình Trích Xuất & Tạo Avatar Chuẩn O(1) Từ Video Gốc

Khi phát hiện `avatar.jpg` cũ không đạt chuẩn hoặc chưa từng được kiểm chứng:

### Bước 1: Trích xuất ứng viên trực tiếp từ file video `.mp4` của kênh
CẤM TUYỆT ĐỐI lấy đại ảnh tĩnh không rõ nguồn gốc. Phải đọc trực tiếp từ các video đã render hoặc video gốc trong $F_{src}$:
```python
import cv2, os

video_path = "D:/video goc/<F_src>/3.mp4"  # Chọn video có mặt nhân vật
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS) or 30

cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
candidates = []

# Quét qua các mốc giây trong video (từ giây 3 đến 25)
for sec in range(3, 25):
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(sec * fps))
    ret, frame = cap.read()
    if not ret:
        break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, 1.1, 4)
    if len(faces) > 0:
        # Lấy khuôn mặt to nhất (chính diện)
        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        fx, fy, fw, fh = faces[0]
        if fw >= 150:  # Đảm bảo khuôn mặt đủ to, rõ nét
            candidates.append((sec, frame, (fx, fy, fw, fh)))
cap.release()
```

### Bước 2: Ghép Mosaic & Soi Mắt Chọn Khung Hình Xuất Sắc Nhất
Ghép 4–6 khung hình ứng viên vào một ảnh mosaic để so sánh biểu cảm (nụ cười, ánh mắt, độ nét):
```python
# Tạo mosaic và dùng browser_vision soi mắt
browser_navigate(url="file:///D:/Taadaa/tmp_cand_mosaic.jpg")
browser_vision(question="Đánh giá biểu cảm khuôn mặt của nhân vật trong các khung hình...")
```

### Bước 3: Crop Vuông $512 \times 512$ Tuân Thủ Invariant Headroom ($cy \approx 0.2 \times H$)
Để khi TikTok cắt tròn không bị cụt đầu hay lẹm cằm:
```python
# Tính toán crop vuông 512x512
crop_size = min(w, 576)
# Đỉnh tóc thường cách đỉnh hộp mặt khoảng 0.45 * fh
# Căn y1 sao cho đỉnh tóc cách mép trên ~30-40px (headroom an toàn)
y1 = max(0, fy - int(fh * 0.45) - 35)
y2 = y1 + crop_size
if y2 > h:
    y2 = h
    y1 = y2 - crop_size

crop_square = frame[y1:y2, 0:crop_size]
crop_512 = cv2.resize(crop_square, (512, 512), interpolation=cv2.INTER_LANCZOS4)

# Tạo ảnh preview viền tròn xanh để kiểm chứng thực tế
mask = np.zeros((512, 512), dtype=np.uint8)
cv2.circle(mask, (256, 256), 256, (255,), -1)
circle_prev = crop_512.copy()
circle_prev[mask == 0] = (circle_prev[mask == 0] * 0.25).astype(np.uint8)
cv2.circle(circle_prev, (256, 256), 256, (0, 255, 0), 2)
cv2.imwrite("D:/Taadaa/avatar_circle_preview.jpg", circle_prev)
```

### Bước 4: Soi Mắt Nghiệm Thu Bắt Buộc Trước Khi Gửi (`browser_vision`)
Trước khi soạn bất kỳ tin nhắn nào cho User:
1. Gọi `browser_navigate("file:///D:/Taadaa/avatar_circle_preview.jpg")`.
2. Gọi `browser_vision("Xác nhận khuôn mặt, tóc, viền tròn...")`.
3. Chỉ khi nhìn thấy tận mắt đúng người thật, đầu không chạm viền tròn xanh thì mới được xác nhận trong báo cáo.

---

### 3. Kỷ Luật Đặt Thẻ `MEDIA:` Tránh Nuốt Ảnh Trên Telegram Gateway
1. **Đứng riêng một dòng độc lập**: Tuyệt đối không để `MEDIA:` trong cùng dòng với text, không nằm sau dấu gạch đầu dòng (`- MEDIA:...`), không nằm trong trích dẫn blockquote (`> MEDIA:...`), không bọc trong backticks.
2. **Định dạng chuẩn xác**:
   ```text
   MEDIA:D:/Taadaa/avatar_circle_preview.jpg
   ```
3. **Cung cấp 2 lựa chọn có đối soát thực tế — CẤM VĂN MẪU TỰ ĐỘNG BỊA "CƯỜI"**:
   - Cung cấp 2 phương án crop/góc nhìn khác nhau (ví dụ: Phương án 1: Nhìn trực diện ống kính; Phương án 2: Góc nghiêng hoặc góc quay khác).
   - **CẤM TUYỆT ĐỐI dùng văn mẫu bịa đặt**: KHÔNG ĐƯỢC tự động viết "cười tươi", "cười mỉm", "biểu cảm tươi tắn" khi chưa nhìn tận mắt, đặc biệt khi đối tượng ĐANG ĐEO KHẨU TRANG, KÍNH BẢO HỘ hoặc che mặt. BẮT BUỘC chỉ mô tả đúng những gì mắt thấy thực tế (màu khẩu trang, kính, tóc, trang phục, hướng ánh nhìn).
   - Trước khi gửi tin nhắn, BẮT BUỘC phải đọc kỹ ảnh từ `browser_vision` / WinRT OCR, xác nhận không phải texture/phông nền rác và đối tượng thực sự có mặt trong ảnh.

---

## 4. Kỷ Luật Chủ Động Vận Hành (Chống Treo Chờ Watchdog Thụ Động)
- **CẤM CHỜ THỤ ĐỘNG KHI ĐỔI AVATAR ĐƠN MÁY**: Khi User đã chốt phương án avatar cho nick đơn máy, CẤM TUYỆT ĐỐI chỉ đánh dấu `PENDING` trong SQLite/Excel rồi đứng im chờ watchdog ca tối (`post_evening_avatar_watchdog`).
- **Thực thi dứt điểm ngay khi máy rảnh**:
  1. Kiểm tra trạng thái máy qua `python D:/Taadaa/tools/inspect_machine.py <M>` và device-lock.
  2. Nếu máy đang ở Launcher / ngoài ca nuôi feed, BẮT BUỘC khởi chạy ngay runner đơn máy:
     ```powershell
     powershell -File D:/Taadaa/Tiktok-video/run_tiktok_upload_avatar.ps1 -Tik <N> -ForceAvatarMachineList <M> -MaxParallel 1
     ```
  3. Soi mắt nghiệm thu ảnh thực tế trên máy (`avatar-save-surface-guard.png` và `avatar-uploaded-confirmed.png`) qua `browser_vision`.
  4. Cập nhật `avatar_replace_queue` sang `DONE`, Excel sang `OK` và báo cáo kết quả kèm ảnh cho User ngay lập tức.

---

## 5. Đối Soát Lưới Video & Phòng Chống Lệch Niche (Workbook F_src Mismatch)
- **CẤM TIN MÙ QUÁNG VÀO EXCEL $F_{src}$ KHI USER GỬI ẢNH KÊNH CÓ LƯỚI VIDEO**:
  1. Đọc tiêu đề/chủ đề các video đã đăng trên lưới trang cá nhân từ ảnh/OCR (ví dụ: *"GHẺ ĐẤY BỐ MẸ Ạ"*, *"CHÁU KHỊT MŨI KÉO DÀI"* -> Niche Bác sĩ nhi khoa).
  2. Kiểm tra nội dung video đầu tiên trong folder $F_{src}$ ghi ở Excel. Nếu Excel ghi niche khác (ví dụ: `Phụ kiện`) và video chứa sản phẩm/phụ kiện không khớp với kênh: BẮT BUỘC DỪNG CROP NGAY.
  3. Quét tìm đúng folder video gốc thực tế tương ứng với niche và các tiêu đề đó (ví dụ: folder 113) rồi mới trích xuất frame từ `.avatar_work/representative_frames/` hoặc video gốc.

---

## 6. Lỗ Hổng "Gate Thủ Tục" & Kiểm Chứng Thị Giác Độc Lập Qua Proxy :20129
- **Cạm bẫy mù thị giác của mô hình điều phối**:
  - Khi runtime gắn screenshot vào context qua `browser_vision`, nếu Coordinator model không giải mã được native image tokens, model sẽ **bịa đặt nội dung (hallucination)** dù vẫn thỏa mãn điều kiện hình thức của Safety Gate (`called browser_vision = True`).
  - Hậu quả: Gửi ảnh em bé hoặc áo tập gym nhưng lại mô tả là bác sĩ mỉm cười thân thiện, khiến User bức xúc nghiêm trọng.
- **Quy trình kiểm chứng thị giác bắt buộc (Semantic Grounding)**:
  CẤM dựa vào cảm tính hoặc text mô tả không có căn cứ. BẮT BUỘC chạy script Python độc lập gọi proxy nội bộ `:20129` model `ag-gemini-pool-3` để lấy mô tả khách quan in ra stdout trước khi gửi:
  ```python
  import urllib.request, json, base64

  def verify_image_content(img_path, question="Describe what is inside the green circle in 1 sentence."):
      with open(img_path, "rb") as f:
          b64 = base64.b64encode(f.read()).decode()
      payload = {
          "model": "ag-gemini-pool-3",
          "stream": False,
          "messages": [{
              "role": "user",
              "content": [
                  {"type": "text", "text": question},
                  {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
              ]
          }]
      }
      req = urllib.request.Request(
          "http://127.0.0.1:20129/v1/chat/completions",
          data=json.dumps(payload).encode(),
          headers={"Content-Type": "application/json"}
      )
      with urllib.request.urlopen(req, timeout=10) as r:
          res = json.loads(r.read().decode())
          return res["choices"][0]["message"]["content"].strip()
  ```
  - Ảnh resize tối đa 512×512 để request phản hồi tức thì (<2s), tránh timeout.
  - Chỉ khi stdout xác nhận đúng đối tượng mục tiêu (đúng người, đúng trang phục, đúng bối cảnh), Coordinator mới được phép đính kèm `MEDIA:`.

---

## 7. Cạm Bẫy Lệch Kho `video goc` vs Kho Render Thực Tế `TIKTOK-videonuoinick` (Sự Cố 14/10/2026 - @hoaikhoa9547)
- **Hiện tượng**:
  - Khi crop avatar cho kênh TikTok `@hoaikhoa9547` (Máy 57 - Tik 3), Coordinator đọc video từ `D:/video goc/451`.
  - Folder `D:/video goc/451` thực chất chứa video crawl cũ/lỗi (cảnh tàu hỏa chạy vỉa hè "Gần quá!", ẩm thực đường phố máy ép mỡ "Dễ ăn").
  - Trong khi đó, toàn bộ 9 video đã đăng trên lưới profile của kênh thực chất đến từ kho render thực tế **`D:/TIKTOK-videonuoinick/451`** (chứa 65 video về mô hình & merchandise Hatsune Miku, Nendoroid pajama, Mecha Miku).
  - Hậu quả: Coordinator lấy frame từ `video goc/451` rồi hallucinate thành Miku neon cyan, gửi User bị mắng: *"Cả 3 hình mày gửi đéo lq đến anime"*.
- **Quy tắc đối soát 2 kho bắt buộc**:
  1. Kiểm tra kích thước và nội dung video giữa `D:/video goc/<F>/1.mp4` và `D:/TIKTOK-videonuoinick/<F>/1.mp4`.
  2. Với các kênh đã có bài đăng trên TikTok: Kho video RENDER THỰC TẾ đang nuôi và đăng bài LUÔN nằm tại `D:/TIKTOK-videonuoinick/<F>/`.
  3. BẮT BUỘC trích xuất frame ứng viên avatar trực tiếp từ các file `.mp4` trong `D:/TIKTOK-videonuoinick/<F>/`. CẤM chỉ quét `.avatar_work/representative_frames/` của `video goc` mà không đối chiếu nội dung thực tế.

---

## 8. Sử Dụng Antigravity Headless CLI (`ag_cli.py`) Làm Giám Định Thị Giác Tối Cao
- **Công cụ tiêu chuẩn trên host**:
  - Khi cần soi mắt kiểm định ảnh/khung hình (chống hallucination), sử dụng trực tiếp CLI bridge headless Antigravity:
    ```bash
    python D:/Taadaa/tools/ag_cli.py ask --file "<path_anh_preview>" "Mô tả thật chính xác từng ô trong ảnh: là hình ảnh gì cụ thể? Có nhân vật anime hay người thật? Bố cục viền tròn có lẹm mặt không?"
    ```
  - `ag_cli.py` gọi trực tiếp `gemini-3.8-flash-high`, trả về phân tích thị giác chi tiết, đọc từng chữ subtitle tiếng Việt/Nhật, nhận diện chính xác từng nhân vật anime/người thật, chỉ ra ngay nếu frame bị lệch chủ đề.
  - BẮT BUỘC có kết quả xác nhận từ `ag_cli.py` trước khi soạn tin nhắn báo cáo và đính kèm thẻ `MEDIA:` cho User.

---

## 9. Cấm Map Số Đuôi Username Làm Folder & Kích Hoạt Stop Hook `media_vision_gate.py`
- **Cấm tự ý suy diễn folder từ số đuôi username**:
  - Nick `@dokieu203` có số đuôi 203 nhưng **Folder Video thực tế là 67** (ghi rõ trong `taikhoan_dat_v2_updated .xlsx` / `Tik3.xlsx`).
  - Lấy nhầm folder 203 (quán nhậu) hoặc nhầm folder 113 sẽ dẫn tới gửi sai ảnh (em bé / áo gym).
  - Khung hình bác sĩ nhi khoa thực tế chuẩn của kênh: `D:/TIKTOK-videonuoinick/67/.avatar_work/representative_frames/v03_002.jpg` và `v03_003.jpg`.
- **Cơ chế Hard Guard vật lý (`media_vision_gate.py`)**:
  - Triển khai tại `D:/Taadaa/.claude/hooks/media_vision_gate.py` và đăng ký trong `D:/Taadaa/.claude/settings.json`.
  - Mỗi khi kết thúc lượt trả lời, Hook kiểm tra mọi thẻ `MEDIA:<path>`. Nếu path đó chưa từng được mở và kiểm tra qua lệnh đọc ảnh có vision thật (`type: image`) trong phiên $\rightarrow$ **Block lượt xuất tin nhắn ngay lập tức**, triệt tiêu hoàn toàn khả năng gửi ảnh mù hoặc nói dối đã soi ảnh.

---

## 10. Xử Lý Lỗi [AVATAR_UPLOAD_MENU_MISSING] Do App Văng Về Home Launcher & Quy Trình Khôi Phục Foreground
- **Triệu chứng & Cạm bẫy**:
  - Runner upload avatar báo lỗi: `[AVATAR_UPLOAD_MENU_MISSING] ENSURE_AVATAR: Không tìm thấy Tải ảnh lên`.
  - Kiểm tra file dump `avatar_menu_dump.xml` hoặc `popup_before.xml` thấy toàn bộ cây UI thuộc `package="com.sec.android.app.launcher"` (Samsung Home Launcher), hoàn toàn không có node nào của `com.ss.android.ugc.trill` (TikTok).
- **Nguyên nhân gốc rễ**:
  - Sau khi push file avatar vào `/sdcard/Pictures/` và phát broadcast `MEDIA_SCANNER_SCAN_FILE`, thiết bị (nhất là dòng máy Ram 4GB cũ như Samsung S7) bị áp lực RAM hoặc ANR khiến TikTok bị đẩy về background hoặc bị OS kill ngầm.
  - Script automation re-tap theo tọa độ avatar circle cố định (ví dụ: `(540, 400)` hoặc `(75, 150)`) mà không re-verify foreground package trước khi tap. Cú tap rơi vào icon màn hình Home Launcher, khiến UI dump không thể tìm thấy nút "Tải ảnh lên" / "Upload photo", dẫn tới báo lỗi giả `AVATAR_UPLOAD_MENU_MISSING`.
- **Quy trình chẩn đoán & khôi phục foreground bắt buộc**:
  1. **Kiểm tra trạng thái focus thật**:
     ```bash
     adb -s <serial> shell dumpsys window | grep -E "mCurrentFocus|mFocusedApp"
     ```
  2. **Đánh thức và mở khóa màn hình nếu bị sleep**:
     - Gửi `input keyevent 224` (KEYWAKE) và swipe mở khóa: `input swipe 540 1600 540 400 300`.
  3. **Khởi động lại TikTok tin cậy qua Monkey Launcher**:
     ```bash
     adb -s <serial> shell monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1
     ```
     *(Tránh dùng `am start -n ...MainActivity` trực tiếp vì TikTok thường xuyên đổi main activity class gây lỗi "Activity class does not exist").*
  4. **Đối soát Profile & Thực hiện flow đổi ảnh**:
     - Kiểm tra tab Hồ sơ hiển thị đúng username mục tiêu (tránh chạm nhầm nick khác).
     - Vào Sửa hồ sơ $\rightarrow$ Bấm avatar $\rightarrow$ Bấm "Tải ảnh lên" $\rightarrow$ Chọn ảnh trong album "Pictures" $\rightarrow$ Bấm "Tiếp" (lưu ý nút Tiếp ở mép dưới $y \approx 1920$ có thể cần tap ở $y \approx 1895-1900$).
     - **BẮT BUỘC BỎ TICK**: Tại màn hình Cắt ảnh, kiểm tra checkbox "Đăng ảnh này lên Nhật ký" — bắt buộc để trống (không tick) trước khi bấm "Lưu".
     - Chụp ảnh màn hình Profile xác nhận avatar mới hiển thị thực tế trước khi đánh dấu hoàn tất.



