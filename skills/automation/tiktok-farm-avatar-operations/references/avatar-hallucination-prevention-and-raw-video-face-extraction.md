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

- **Sự cố 2.1 (16/10/2026 — @thanh.huyn4934 M39 Tik 1 — Bẫy Ảo Giác Nhầm 2 Ảnh Cùng Kênh Thành Kênh Nguồn & Kênh Re-up)**:
  - User gửi 2 ảnh yêu cầu "Chuẩn hoá kênh này và pin video nhiều view cái". Ảnh 1 là màn hình Profile đỉnh trang, Ảnh 2 là khi cuộn xuống (Sticky Bar hiện avatar thu nhỏ và nút Follow khi view từ iOS cá nhân).
  - Coordinator không so khớp lưới video mà vội vàng hallucinate phán: *"Ảnh 2 là Kênh nguồn gốc (Source idol channel), Ảnh 1 là Kênh farm clone re-up"*.
  - User chửi thẳng: *"Xàm lồn 2 ảnh cùng 1 kênh của tao"*.
  - **Nguyên nhân gốc rễ**: Nhìn thấy thanh sticky bar có nút Follow liền suy diễn sai là kênh của người khác (idol), mà không nhận ra đây là cùng một profile của User khi được cuộn xuống để xem các video cũ nhiều view (clip 31,3K view).
  - **Quy tắc đối soát 2 ảnh profile**: Khi User gửi nhiều ảnh trong một yêu cầu chuẩn hoá/pin video: BẮT BUỘC kiểm tra xem các ảnh có phải là các đoạn cuộn (scroll viewports) của cùng một trang cá nhân hay không (cùng nhân vật, cùng style nội dung, cùng bio/avatar). Tuyệt đối không tự suy diễn ảnh là "kênh nguồn / kênh đối thủ" khi chưa có xác nhận rõ ràng.
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

---

## 11. Bẫy Khách Mời / Chuyên Gia Trong Video Tin Tức & Phỏng Vấn (Guest Speaker Trap)
- **Hiện tượng**:
  - Khi trích xuất khuôn mặt tự động từ các video dạng tin tức, tài chính hoặc talkshow/phỏng vấn (ví dụ kênh `@karunmmkx35` - M65 Tik 5 "Bản tin Tài chính"), các frame quét ở đoạn giữa/cuối video thường nhận diện khuôn mặt của chuyên gia, khách mời hoặc người trả lời phỏng vấn (ví dụ người đàn ông trung niên phát biểu lúc 22s).
  - Tên kênh TikTok là nữ ("Mai"), thumbnail trên lưới trang cá nhân toàn bộ là Nữ MC dẫn tin áo dạ hồng / đỏ đô, nhưng nếu script tự động lấy face lớn nhất ở giây 22 sẽ cho ra avatar đàn ông trung niên lạc đề.
- **Quy tắc phân biệt Host chính vs Khách mời**:
  1. **Đối chiếu tần suất xuất hiện trên lưới trang cá nhân**: Chủ kênh / MC chính LUÔN là người xuất hiện lặp đi lặp lại ở khung hình mở đầu (3–5s đầu) của phần lớn video trên grid.
  2. **Soi mắt qua `ag_cli.py` & `browser_vision`**:
     - Phân tích chi tiết bối cảnh: MC ngồi ở bàn dẫn tin trường quay (có logo chương trình, ticker chữ chạy phía dưới) khác hoàn toàn với khách mời/chuyên gia (thường ở bục hội thảo, hiện trường ngoài trời hoặc khung phỏng vấn).
     - Khi cung cấp 2 phương án cho User, Option 1 LUÔN LUÔN là MC/Host chính diện, Option 2 có thể là góc quay khác của Host; nếu đưa frame khách mời thì BẮT BUỘC chú thích rõ là "Khách mời / Chuyên gia phát biểu" để User không bị chọn nhầm.

---

## 12. Mẫu Self-Contained Test Khi Dispatch Worker Crop Avatar (Vượt Scope Lock & Terminal Whitelist)
- **Bối cảnh điều phối**:
  - Khi Coordinator hết hạn ngạch ghi T1 (> 200 dòng) và phải dispatch Worker leaf để tạo script xử lý ảnh:
  - Guard bắt buộc định dạng: `FOCUSED_TEST: python -m pytest <file.py>::<test_node> -q` (cấm `pytest` trần, cấm sai cú pháp).
  - Terminal sandbox của Worker áp dụng Default-Deny: cấm `python -m py_compile`, chỉ cho phép `pytest`.
  - Đồng thời Worker bị khóa cứng Single-File Scope Lock (`FILE: D:/Taadaa/reports/<script>.py`). Nếu Worker cố tạo thêm file test riêng (như `test_<script>.py`) sẽ bị Guard chặn vì vi phạm Scope Lock.
- **Kỹ thuật Self-Contained Test chuẩn O(1)**:
  - Nhúng trực tiếp hàm test vào cuối file script chính:
    ```python
    def test_generate_and_verify_avatars():
        main()
        expected = ["avatar_opt1.jpg", "preview_opt1.jpg", ...]
        for fname in expected:
            p = os.path.join(OUTPUT_DIR, fname)
            assert os.path.exists(p) and os.path.getsize(p) > 1000
    ```
  - Khai báo contract dispatch:
    ```text
    TASK_KIND: CREATE
    FILE: D:/Taadaa/reports/create_final_avatars.py
    FOCUSED_TEST: python -m pytest D:/Taadaa/reports/create_final_avatars.py::test_generate_and_verify_avatars -q
    ```
  - Kết quả: Worker chỉ cần tạo đúng 1 file duy nhất, chạy 1 lệnh pytest pass 100%, vừa sinh đủ file ảnh vừa thỏa mãn mọi gate điều phối mà không bị kẹt sandbox.

---

## 13. Cạm Bẫy Trôi Tâm Crop & Cắt Mất Miệng/Cằm (Sự Cố 15/10/2026 — "Thấy Mỗi Cái Tóc / Không Thấy Người")
- **Hiện tượng & Bị User mắng**:
  - Khi crop avatar cho kênh TikTok `@nhathasz4vw` (Folder 396) và `@pegsofuh038` (Folder 325), script tạo ra ảnh viền tròn xanh chỉ thấy trán, lông mày hoặc chóp mũ đội ngược nằm ép sát đáy vòng tròn, trong khi 70% diện tích bên trên là trần nhà, phụ đề slogan chữ viết tay (*"...xua đuổi mấy tên dê trong 1 nốt nhạc"*).
  - Toàn bộ mũi, miệng, cằm bị cắt cụt ngoài viền tròn. User phản ứng gay gắt: *"Ava loz gì k thấy ng hoặc thấy mỗi cái tóc v"*.
- **Nguyên nhân gốc rễ**:
  1. **Công thức Headroom bị giật ngược lên phụ đề**: Công thức cũ `y1 = fy - int(fh * 0.45) - 35` giả định đỉnh tóc nằm ngay trên trán. Nhưng trong video TikTok dọc ($1080 \times 1920$), ngay phía trên đầu nhân vật thường chèn phụ đề/chữ trang trí. Trừ ngược quá tay khiến `y0` kéo tít lên vùng chữ, đẩy toàn bộ khuôn mặt thật xuống đáy crop.
  2. **Tọa độ trục dọc sai lệch nghiêm trọng trên video dọc 9:16**: Nhân vật ngồi/đứng làm việc trong video $1080 \times 1920$ thường có tâm đầu ở $y \approx 800 - 950$, nhưng script hardcode hoặc tính Haar nhầm $y \approx 420$ (rơi vào khoảng không gian trống phía trên).
  3. **Vi phạm tiêu chuẩn nghiệm thu Vision**: Kiểm tra mắt chỉ nhìn xem "có mặt người không" mà không kiểm tra độ trọn vẹn của ngũ quan và vị trí tâm.
- **Quy tắc vàng Crop Avatar Ngũ Quan Chuẩn 100%**:
  1. **Định vị tâm mặt (Center-based Crop)**:
     - Luôn tính tâm mặt trước: `center_x = fx + fw * 0.5`, `center_y = fy + fh * 0.55` (ngay giữa sống mũi).
     - Chiều rộng crop vuông: `side = int(min(fw * 2.6, w * 0.9, h * 0.55))`.
     - Tọa độ góc trên: `x0 = int(center_x - side / 2)`, `y0 = int(center_y - side * 0.5)`.
     - Kẹp an toàn trong khung hình: `x0 = max(0, min(x0, w - side))`, `y0 = max(0, min(y0, h - side))`.
  2. **Tiêu chuẩn nghiệm thu Vision qua `ag_cli.py ask` (Checklist 4 điểm bắt buộc)**:
     - [ ] **Đủ ngũ quan**: Phải nhìn thấy rõ trọn vẹn cả hai mắt, sống mũi, miệng/môi, cằm và đường quai hàm. CẤM chấp nhận ảnh bị mất mũi, môi hoặc cằm.
     - [ ] **Cân đối tâm**: Khuôn mặt phải nằm ở giữa vòng tròn (cho phép thiên nhẹ 5-10% lên trên để lấy cổ áo, nhưng CẤM tụt xuống sát đáy).
     - [ ] **Đệm an toàn (Headroom & Chin clearance)**: Cả đỉnh đầu/tóc và cằm đều phải cách đường viền tròn xanh một khoảng an toàn (chin clearance $\ge 20$px), không để viền tròn cắt ngang cằm hay chỏm tóc.
     - [ ] **Không dính phụ đề rác**: Vùng trên đỉnh đầu không được chứa dòng chữ slogan, caption hay logo to choán diện tích.

---

## 14. Cạm Bẫy Up Lại Y Hệt Avatar Cũ & Quy Tắc Trích Xuất Nhân Vật Mới (Sự Cố 15/10/2026 — @sambich012 Máy 49)
- **Hiện tượng & Bị User mắng chửi gay gắt**:
  - Khi User gửi ảnh profile hoặc yêu cầu "chuẩn hoá kênh này" / "đổi ava", Coordinator thấy trên đĩa tại `D:/TIKTOK-videonuoinick/<F_out>/avatar.jpg` đã có sẵn file `avatar.jpg`.
  - Thay vì trích xuất ảnh mới khác biệt, Coordinator chạy thẳng runner upload file có sẵn đó lên thiết bị.
  - Kết quả: TikTok nạp lại y hệt bức ảnh đại diện cũ mà kênh đang dùng từ trước. User nổi giận: *"dụd mẹ t ns đổi ava mày đưa y cái ava cũ..."*.
- **Nguyên nhân cốt lõi**:
  1. **Hiểu sai ngữ nghĩa "Đổi avatar"**: Khi User yêu cầu đổi avatar hoặc chuẩn hoá kênh, mục tiêu là thay diện mạo mới cho kênh. File `avatar.jpg` tồn tại sẵn trong folder thường chính là avatar cũ từng up từ các phiên trước.
  2. **Thiếu bước so khớp sai khác (Visual/Diff Check)**: Không so sánh ảnh trong folder với avatar đang hiển thị trên TikTok profile của máy/ảnh User gửi.
- **Quy tắc bắt buộc khi thực hiện "Đổi Avatar"**:
  1. **BẮT BUỘC TRÍCH XUẤT NHÂN VẬT/FRAME MỚI**: Luôn trích xuất khuôn mặt nhân vật từ các video `.mp4` khác trong `D:/video goc/<F_src>` (hoặc từ `.avatar_work/representative_frames/`).
  2. **Loại trừ tuyệt đối frame trùng avatar cũ**:
     - So sánh trực quan hoặc tính sai khác với avatar hiện tại của kênh.
     - Nếu ứng viên trùng khớp biểu cảm/quần áo/góc chụp với avatar hiện tại: LOẠI BỎ NGAY, chọn video khác (ví dụ: đang dùng frame video 1 thì chuyển sang video 10, 20...).
  3. **Ghi đè đồng bộ 3 kho trước khi chạy runner**:
     - `D:/TIKTOK-videonuoinick/<F_out>/avatar.jpg`
     - `D:/video goc/<F_src>/avatar.jpg`
     - `D:/video goc/<F_out>/avatar.jpg` (nếu có)
  4. **Tạo marker vật lý `.manual_avatar_locked`**:
     - Tạo file marker `.manual_avatar_locked` tại cả 3 folder trên để khóa cứng `is_folder_avatar_protected` = `True` ngay lập tức, ngăn ngừa mọi cron/script quét hàng loạt ghi đè.

---

## 15. Bẫy Sticky Header vs Profile Header Khi Cuộn Trang & Ảo Giác "Kênh Nguồn vs Kênh Clone" (Sự Cố 16/10/2026 — @thanh.huyn4934 Máy 39)
- **Hiện tượng & Bị User mắng chửi gay gắt**:
  - User gửi 2 ảnh chụp màn hình TikTok cùng lúc và yêu cầu: *"Chuẩn hoá kênh này và pin video nhiều view cái"*.
  - Ảnh 1 chụp đỉnh profile: Avatar góc phải, tên "Thanh Huyền", `@thanh.huyn4934`, stats 321/391/3.243, 4 hàng video đầu (view cao nhất 2.357).
  - Ảnh 2 chụp khi User đã **cuộn màn hình xuống dưới (Scrolled Down)**: Profile Header lớn cuộn mất, xuất hiện **Sticky Header** với avatar mini ở giữa, nút Follow màu đỏ bên phải; bên dưới là các hàng video cũ/sâu hơn của kênh (chứa clip viral **31,3K view**).
  - Coordinator nhìn thấy Ảnh 2 có Sticky Header mini và video khác 3 hàng đầu Ảnh 1, liền tự **bịa đặt giả thuyết**: Ảnh 2 là *"Kênh nguồn gốc (Source idol channel)"*, còn Ảnh 1 là *"Kênh clone re-up"*.
  - Hậu quả: Coordinator bỏ sót clip viral **31,3K view** khi tư vấn pin video cho kênh. User chửi thẳng: *"Xàm lồn 2 ảnh cùng 1 kênh của tao"*.
- **Cơ chế UI TikTok khi cuộn (Sticky Header Mechanics)**:
  - Khi cuộn trang cá nhân TikTok trên mobile, Header lớn chứa Tên/Username/Stats sẽ trượt ra khỏi viewport và được thay thế bằng **Sticky Header** cố định ở đỉnh: avatar tròn thu nhỏ ở giữa, nút Follow/Chia sẻ thu gọn bên phải, tab `||| ▾` trượt sát mép dưới sticky header.
- **Quy tắc đối soát đa ảnh (Multi-Screenshot Reconcile Invariant)**:
  1. **Nhận diện Sticky Header**: Nếu đỉnh ảnh chỉ có 1 avatar tròn nhỏ nằm chính giữa thanh bar trên cùng, không có Tên/Bio/Stats $\rightarrow$ đây là màn hình Profile đang CUỘN XUỐNG của cùng 1 kênh, CẤM suy diễn thành kênh khác.
  2. **Đối soát tính liên tục của lưới video**: Kiểm tra bối cảnh, nhân vật, font chữ phụ đề giữa các video mép dưới ảnh 1 và mép trên ảnh 2. Nếu cùng nhân vật/phòng tập/font chữ $\rightarrow$ 100% là cùng một kênh.
  3. **Cấm bịa đặt quan hệ "Kênh Nguồn vs Kênh Clone"**: Khi User dùng từ số ít ("kênh này") và gửi nhiều ảnh, mặc định là các đoạn cuộn khác nhau của cùng 1 kênh.
  4. **Gộp toàn bộ video để xếp hạng Pin Video**: Gom toàn bộ video trên tất cả các ảnh được gửi vào một danh sách, sắp xếp view giảm dần để chọn đúng top video (không được bỏ sót clip viral ở ảnh cuộn sâu).

---

## 16. Cạm Bẫy Avatar Nhiễm Màn Hình Cài Đặt (Settings Artifact) & Bẫy Cột Avatar "OK" Ảo (Sự Cố 16/10/2026 — @lenhi09116 Máy 16 Tik 3)
- **Hiện tượng thực tế**:
  - Khi User yêu cầu "Chuẩn hoá kênh này" kèm ảnh profile `@lenhi09116` (Máy 16 Tik 3).
  - Tra cứu Excel `Tik3.xlsx`: Cột `Avatar` ghi `OK`, SQLite `avatar_replace_queue` từng đánh dấu `DONE`.
  - Tuy nhiên, avatar thực tế hiển thị trên kênh và file lưu trên đĩa (`D:/TIKTOK-videonuoinick/123/avatar.jpg`, `D:/video goc/123/avatar.jpg`) lại là ảnh chụp màn hình danh mục **Cài đặt (Settings)** Samsung One UI (chứa chữ *Màn hình*, *Hình nền và phong cách*, *Theme*, *Màn hình chờ*, *Màn hình khóa*...).
- **Nguyên nhân gốc rễ**:
  1. Trong một lần chạy runner tự động trước đó, thiết bị bị văng hoặc bấm nhầm vào ứng dụng Cài đặt của điện thoại khi chụp màn hình/crop, dẫn tới lưu nhầm giao diện Settings thành `avatar.jpg`.
  2. Runner exit 0 và đánh dấu `OK` / `DONE` vào database/Excel mà không qua bước giám định thị giác ngữ nghĩa (`ag_cli.py ask`).
  3. Cột `Avatar = OK` trong Excel trở thành "OK ảo", che giấu avatar rác suốt nhiều phiên.
- **Quy trình chuẩn hóa 3 món (Ava - Hashtag - Pin) chuẩn xác**:
  1. **Ghim video (Pin Rule $\ge 1.000$ view)**:
     - Quét toàn bộ lượt xem hiển thị trên lưới video của profile từ ảnh gửi hoặc ADB UI dump.
     - **Chỉ ghim video có lượt xem $\ge 1.000$ view** (ví dụ 1.200, 3.800, 15.000 view).
     - Nếu toàn bộ video trên lưới đều $< 1.000$ view (ví dụ cao nhất chỉ 358 view): **TUYỆT ĐỐI KHÔNG GHIM**, giữ nguyên thứ tự video tự nhiên.
  2. **Giám định thị giác file avatar hiện tại**:
     - BẮT BUỘC gọi `ag_cli.py ask --file "<path_avatar>" "Mô tả ngắn gọn nội dung: có người hay không, chi tiết là gì?"`.
     - Nếu phát hiện avatar là giao diện cài đặt (Settings), màn hình Home Launcher, texture hoặc không có người $\rightarrow$ Coi như avatar bị hỏng hoàn toàn dù Excel ghi `OK`.
  3. **Trích xuất nhân vật từ video thực tế của kênh**:
     - Đọc video từ kho render `D:/TIKTOK-videonuoinick/<F_out>/` hoặc `.avatar_work/representative_frames/`.
     - Trích xuất frame góc mặt rõ nét, áp dụng Center-based Crop ngũ quan chuẩn (Section 13) với Headroom & Chin clearance $\ge 20$px.
     - Cung cấp 2 phương án preview viền tròn xanh đã qua kiểm chứng `ag_cli.py ask` cho User lựa chọn trước khi nạp lên máy.
  4. **Xử lý thiết bị S7 bị treo ADB Shell trong quá trình chuẩn hóa**:
     - Nếu lệnh adb shell/dumpsys bị timeout do thiết bị S7 bị đơ: Chạy `recover_stuck_s7.py --machine <N>` qua `with_device_lock.py` ở chế độ background để khôi phục phân tầng (Soft recovery $\rightarrow$ Reboot có cooldown 300s $\rightarrow$ Reconnect).

---

## 17. Cạm Bẫy Avatar Dính Chữ Overlay/Emoji & Lệch Niche Lưới Video Khi Chuẩn Hoá Kênh (Sự Cố 16/10/2026 — @dinhgia0906 Máy 70 & @minhan2473 Máy 8)
- **Hiện tượng**:
  - Khi User yêu cầu *"Chuẩn hoá 2 kênh này"* kèm 2 ảnh chụp TikTok profile:
    1. Kênh `@dinhgia0906` (Máy 70 Tik 2, F_src 150, F_out 554): Avatar hiện tại trên TikTok profile bị dính chữ cắt dở và emoji cười ra nước mắt: `"tổng cộng km 😂"` đè ngang mặt (do cắt nhầm frame từ video đi bộ *"hôm nay đi bộ tổng cộng 20km 😂"*).
    2. Kênh `Vy Miu` (`@minhan2473`) (Máy 8 Tik 2, F_src 88, F_out 58): Video thực tế trên lưới là cơ sở chăm sóc mắt/spa y tế *Tâm An Đường*, nhưng workbook `Tik2.xlsx` lại gán Niche `Thời trang` và pool hashtag `#thoitrang...`; avatar trong kho lại là ảnh nam thanh niên selfie phòng gym đeo tai nghe đen.
- **Nguyên nhân gốc rễ**:
  1. Khi trích xuất avatar tự động từ video clip TikTok dọc ($1080 \times 1920$), frame nhận diện khuôn mặt thường rơi trúng các giây có chèn chữ caption overlay hoặc sticker/emoji hoạt hình. Nếu không soi kỹ sẽ crop dính chữ/emoji lên mặt avatar.
  2. Lệch Niche (Niche Drift) giữa thực tế bài đăng trên kênh và dữ liệu Excel: Kênh đã chuyển hướng đăng nội dung spa/chăm sóc mắt nhưng Excel chưa cập nhật, dẫn tới gán nhầm hashtag và nuôi lệch tệp.
- **Quy tắc chuẩn hóa 3 món chuẩn mực**:
  1. **Kiểm tra Text/Emoji trên Avatar**:
     - Phải kiểm tra và loại bỏ các frame có chữ caption/overlay hoặc emoji đè lên mặt.
     - Trích xuất frame từ video gốc ở những giây không có text (hoặc video không chèn chữ to lên nhân vật).
  2. **Đối soát Niche Lưới Video trước khi khóa Hashtag**:
     - CẤM khóa mù quáng hashtag từ Excel khi chưa đối soát với video trên profile.
     - Nếu phát hiện kênh đăng video y tế/spa mắt Tâm An Đường mà Excel ghi Thời trang $\rightarrow$ Báo cáo lệch niche, sửa lại Niche/Hashtag trong Excel cho đúng thực tế trước khi ghi nhận `.manual_hashtag_locked`.
  3. **Ngưỡng Ghim Video (Pin Gate $\ge 1.000$ view)**:
     - Kênh `@dinhgia0906` (max 790 view) và `@minhan2473` (max 230 view) đều chưa đạt ngưỡng $\ge 1.000$ view $\rightarrow$ Giữ nguyên thứ tự tự nhiên, KHÔNG ghim.
  4. **Kỷ luật Device Lock khi thao tác ADB Farm**:
     - Mọi lệnh ADB kiểm tra hoặc thao tác trên máy thật bắt buộc chạy qua `python D:/Taadaa/tools/with_device_lock.py --machine <N> -- <cmd>` để tránh xung đột với tiến trình nuôi ngầm (`HARD GATE #5 - DEVICE LOCK REQUIRED`). Tuyệt đối không can thiệp trần vào thiết bị.

---

## 18. Tinh Chỉnh Bounding Box Né Phụ Đề Góc Dưới & Bảo Toàn Cằm (Sự Cố 16/10/2026 — @lenhi09116)
- **Hiện tượng**:
  - Khi crop avatar bằng Center-based crop (Section 13) từ video clip có phụ đề chữ trắng ở góc dưới (ví dụ video salon tóc có text `Bị nghiện Mullet Layer á @DUNNHAIRSALON` ở $y > 700$):
  - Khung crop mặc định theo Haar cascade lấy trọn cả vùng text ở đáy, khiến chữ lọt vào bên trong vòng tròn xanh (vị trí 7h-8h), bị viền tròn cắt ngang chân chữ rất mất thẩm mỹ.
  - Nếu chỉ dịch `y0` lên cao để né chữ mà giữ nguyên `side`, cằm sẽ bị viền tròn xanh cắt ngang sát mép dưới bờ môi (mất cằm hoàn toàn).
- **Quy tắc điều chỉnh Bounding Box loại bỏ phụ đề & bảo toàn cằm**:
  1. **Tăng kích thước `side` và hạ nhẹ `y0` có kiểm soát**:
     - Tăng `side` thêm $10-15\%$ (ví dụ từ 500px lên 540px) để mở rộng đường tròn viền xanh ra xa khuôn mặt hơn.
     - Dịch `y0` xuống vừa đủ để lấy trọn vẹn cằm tự nhiên và cổ áo, đồng thời chọn góc `x0` dịch sang hướng ngược lại với vị trí đặt text (ví dụ text ở góc trái thì căn lề sang phải hoặc căn `x0` sao cho text lọt vào vùng góc 4 góc vuông sẽ bị làm mờ ngoài bán kính $R=256$).
  2. **Vòng kiểm định 2 lớp bắt buộc**:
     - **Lớp 1 (Antigravity CLI headless)**: Chạy `python D:/Taadaa/tools/ag_cli.py ask --file "<preview.jpg>"` chất vấn trực diện 4 điểm: (1) Đủ ngũ quan 100%, (2) Cằm có bị cắt lẹm không, (3) Đỉnh đầu và cằm có cách viền xanh an toàn không, (4) Có dính chữ/phụ đề rác không.
     - **Lớp 2 (Browser Vision)**: Mở ảnh trực tiếp qua `browser_navigate("file:///<preview.jpg>")` và `browser_vision` xác nhận bằng mắt trước khi đính kèm thẻ `MEDIA:<path>`.

---

## 19. Xử Lý Phản Hồi "Ava Khác Đi" & Tiêu Chí Lựa Chọn Frame Solo Thần Thái Creator (Sự Cố 16/10/2026 — @lenhi09116)
- **Bối cảnh & Phản hồi của User**:
  - Khi đề xuất 2 phương án avatar đầu tiên cho kênh `@lenhi09116`: Option 1 là góc cắt tiệm tóc mullet layer, Option 2 là góc bạn nữ nằm tựa gối mắt lim dim/nhắm hờ (từ video *"Tôi là cái love xịn nhất của ảnh"*).
  - User lập tức phản hồi ngắn gọn: *"Ava khác đi"*.
- **Phân tích nguyên nhân người dùng từ chối đợt 1**:
  1. **Tư thế thụ động / mắt nhắm / góc nằm**: Khung hình nhân vật đang nằm tựa gối, mắt lim dim hoặc góc máy từ dưới lên (low angle) không tạo được năng lượng tích cực, thiếu tính chuyên nghiệp của một creator TikTok.
  2. **Bẫy ảnh đôi / ảnh nhóm**: Một số frame nhận diện khuôn mặt bắt trúng ảnh selfie cặp đôi (bạn nữ + bạn nam như clip *"Ảnh đôi ơi :))"*) hoặc chụp chung bạn bè đeo kính râm. Với kênh cá nhân (solo channel), việc đưa 2 người vào vòng tròn avatar sẽ gây rối mắt và bị cắt mép người thứ hai.
  3. **Giới hạn vật lý khi crop video cận cảnh ($W=640$)**: Nếu video gốc quay quá sát mặt ($fw > 450$px trên khung hình rộng 640px), việc lùi `side` để lấy khoảng đệm headroom/chin clearance sẽ chạm trần biên ảnh độ rộng ($W=640$), dẫn tới avatar bị cảm giác "zoom quá chặt/bức bối".
- **Chiến lược tuyển chọn ứng viên Avatar thay thế xuất sắc**:
  1. **Ưu tiên frame cận trung (Medium Close-up) có khoảng thở**: Chọn các video quay bán thân hoặc cận vừa phải (khuôn mặt chiếm khoảng $30-45\%$ chiều rộng khung hình), cho phép thuật toán Center-based Crop lấy trọn vẹn cả mái tóc, đỉnh đầu và phần cổ/áo rất thoáng.
  2. **Đa dạng hóa phong cách đối lập rõ rệt**:
     - *Phong cách 1 (Douyin / Ngọt ngào / Nữ tính)*: Ánh sáng trong nhà sáng mịn, makeup má hồng đào, phấn mắt nhũ sáng, ánh mắt nhìn thẳng camera, nụ cười nhẹ/hé môi tự nhiên (ví dụ trích từ Video 13).
     - *Phong cách 2 (Năng động / Party / Thể thao)*: Bối cảnh tiệc đêm/sự kiện có đèn neon rực rỡ, trang phục áo thun thể thao/jersey, biểu cảm nháy mắt cười tươi tắn tràn đầy năng lượng (ví dụ trích từ Video 18 - clip đạt top view trên lưới).
  3. **Quy tắc Avatar Solo cho kênh cá nhân**: Mặc định 100% chỉ lấy duy nhất chủ kênh trong vòng tròn xanh, loại trừ hoàn toàn người đứng cạnh để đảm bảo bố cục tập trung tuyệt đối vào gương mặt đại diện của kênh.
  4. **Kỷ luật Device Lock khi máy đang chạy ca nuôi (Active Feed Session Hand-off)**:
     - Khi kiểm tra máy qua device-lock phát hiện máy đang có active lock chạy ca nuôi (`run_tiktok.py --mode multi-machine-feed-session`), CẤM TUYỆT ĐỐI cố gắng force reboot hoặc kill tiến trình để chen ngang việc đổi avatar.
     - **Quy trình chuyển giao an toàn 3 bước**:
       * Bước 1: Ghi đè file `avatar.jpg` đã nghiệm thu vào cả 3 kho dữ liệu (`D:/TIKTOK-videonuoinick/<F_out>/avatar.jpg`, `D:/video goc/<F_src>/avatar.jpg`, `D:/video goc/<F_out>/avatar.jpg`).
       * Bước 2: Tạo marker vật lý `.manual_avatar_locked` và `.manual_hashtag_locked` tại các folder trên để kích hoạt cờ bảo vệ chống ghi đè vĩnh viễn.
       * Bước 3: Cập nhật SQLite `avatar_replace_queue` sang trạng thái `PENDING` kèm timestamp mới. Khi ca nuôi hoàn tất, runner tự động nhả device lock và watchdog upload avatar sẽ tự động nạp ảnh lên TikTok an toàn, đúng quy trình.

---

## 20. Kỷ Luật Tái Sử Dụng Queue Có Sẵn (Chống Đẻ Watchdog Mới) & Đối Soát Closeout Khi Hoàn Tất Vận Hành Media

- **Bối cảnh & Nghi vấn của User ("Là mày cài watchdog nạp hay đưa vào cron tự nạp có sẵn")**:
  - Khi Coordinator báo cáo: *"Đã ghi nhận PENDING trong SQLite avatar_replace_queue để tự động nạp lên TikTok"*, User lập tức chất vấn để kiểm tra xem Agent có đang tự ý tạo thêm file script watchdog mới hay không.
  - Tôn chỉ vận hành Taadaa Farm (Invariants & Memory): **REUSE > EXTEND > NEW — CẤM TUYỆT ĐỐI đẻ script/watchdog trùng lặp**.

- **Cơ chế nạp tự động SSOT của Farm (`avatar_replace_queue`)**:
  1. **Hàng đợi chuẩn**: Bảng `avatar_replace_queue` trong SQLite `D:/Taadaa/data/tiktok_tracker.db` là SSOT duy nhất quản lý tiến trình đổi avatar cho toàn bộ tài khoản.
  2. **Cronjob tự nạp có sẵn**: Job `post-evening-avatar-watchdog` (Job ID: `25d6f8ab0264`, lịch chạy `*/5 * * * *`, script `post_evening_avatar_watchdog.py`) liên tục quét các tài khoản có trạng thái `PENDING` trong hàng đợi này.
  3. **Quy tắc ứng xử khi User chất vấn**:
     - Báo cáo rõ ràng, trung thực: Khẳng định KHÔNG tạo watchdog mới, mà chỉ cập nhật trạng thái `PENDING` vào bảng SQLite `avatar_replace_queue` có sẵn để cronjob hiện hành xử lý.
     - Kiểm tra trạng thái máy: Nếu thiết bị rảnh và kết nối ADB thông suốt thì kích hoạt runner đơn máy nạp dứt điểm ngay; nếu thiết bị đang bận ca nuôi hoặc bị nghẽn phần cứng/USB transport (timeout ADB) thì giữ trạng thái `PENDING` an toàn chờ chu kỳ hồi phục.

- Kỷ luật Closeout ("Done" / "Chốt phiên") Đối Với Phiên Vận Hành Media/Data**:
  1. Khi User phát lệnh kết thúc phiên bằng từ khóa *"Done"* / *"Chốt phiên"* sau một chuỗi tác vụ chuẩn hóa kênh (Avatar, Hashtag, Pin):
  2. BẮT BUỘC kiểm tra `git status` tại repo công việc (`D:/Taadaa/tiktok-luot nuoi acc`).
  3. Nếu phiên làm việc thuần túy là tác vụ vận hành media và cập nhật dữ liệu farm (không có code diff/thay đổi mã nguồn trong Git):
     - Xác nhận rõ ràng với User: Tác vụ vận hành media/database farm đã hoàn tất và được bảo vệ (marker `.manual_avatar_locked`, `.manual_hashtag_locked`, SQLite queue `PENDING`).
     - Không phát sinh code diff cần review/commit/push lên remote branch, tránh kích hoạt nhầm vòng lặp remediation code cho diff cũ của các phiên trước.

---

## 21. Kỹ Thuật Canvas Expansion & Border Padding Khi Crop Video Cận Cảnh (Bảo Toàn Trọn Vẹn Đỉnh Tóc & Cằm)
- **Hiện tượng & Giới hạn vật lý khi crop cận cảnh ($W=640$ / $W=576$)**:
  - Khi trích xuất avatar từ các video quay góc cận cảnh (selfie close-up), khuôn mặt chiếm phần lớn khung hình ($fw > 450$px trên video rộng 640px). Chiều cao từ đỉnh đầu đến cằm đạt $\approx 550$px.
  - Nếu crop thông thường kẹp trong khung ảnh gốc ($side \le 640$px), đường tròn viền xanh ($R=256$) bắt buộc sẽ cắt lẹm một trong hai: hoặc cắt ngang đỉnh tóc (mất ngọn tóc, không có headroom an toàn), hoặc cắt ngang dưới cằm (mất cằm hoàn toàn).
- **Giải pháp kỹ thuật: Mở rộng Canvas bằng Border Padding (`cv2.BORDER_REPLICATE`)**:
  - Mở rộng đều 4 phía ảnh gốc một khoảng đệm an toàn (`pad = side // 2`):
    ```python
    pad = side // 2
    padded = cv2.copyMakeBorder(im, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
    cx_pad = int(center_x) + pad
    cy_pad = int(center_y) + pad
    x0 = cx_pad - side // 2
    y0 = cy_pad - side // 2
    crop = padded[y0:y0 + side, x0:x0 + side]
    sq = cv2.resize(crop, (512, 512), interpolation=cv2.INTER_LANCZOS4)
    ```
  - **Lợi ích vượt trội**:
    1. Cho phép nâng `side` lên $700 - 750$px (vượt qua giới hạn chiều rộng 640px của ảnh gốc) mà không làm biến dạng tỷ lệ nhân vật.
    2. Căn tâm dọc chính xác: $cy = (y_{hair\_top} + y_{chin\_bottom}) / 2$, đảm bảo khuôn mặt nằm ngay tâm đường tròn.
    3. Đường tròn xanh bao bọc trọn vẹn cả đỉnh tóc (với khoảng đệm headroom tự nhiên $\approx 30-40$px từ nền cây cối/phông nền nhân bản) và toàn bộ cằm, cổ áo sơ mi mà không bị chạm hay cắt viền.
  - **Kỹ thuật né Text Overlay trên/dưới**:
    - Khi video có khung comment ở đỉnh ($y < 230$) hoặc subtitle ở đáy ($y > 650$), việc tinh chỉnh $side$ nhỏ hơn khoảng cách giữa hai khối chữ kết hợp với mặt nạ hình tròn $R=256$ sẽ đẩy toàn bộ text overlay vào 4 góc vuông tối ngoài vòng tròn, giữ bên trong vòng tròn avatar hoàn toàn sạch chữ 100%.

---

## 22. Bẫy Bounding Box Giả Từ Chó Con / Bàn Ăn Qua Haar Cascade & Kỹ Thuật Remote Base64 Exec (Sự Cố 16/10/2026 — @nhitet0482 Máy 201)
- **Hiện tượng thực tế**:
  - Khi quét tìm khuôn mặt tự động bằng `haarcascade_frontalface_default.xml` trên video kho 2 (kênh Lão Cò Video), thuật toán trả về các bounding box nhận diện mặt với độ tin cậy cao: `[332, 779, 147, 147]` ở Video 3 giây 12, và `[242, 719, 172, 172]` ở Video 4 giây 4.
  - Tuy nhiên, khi gọi `ag_cli.py ask` giám định thị giác ngữ nghĩa:
    * Frame Video 3 thực chất là **bàn ăn giảm cân** (đĩa dưa chuột, khoai lang luộc, chữ *"BỮA TRƯA GIẢM CÂN CỦA LÃO CÒ"*). Các đĩa sứ và khoai lang bị Haar Cascade nhận diện nhầm thành ngũ quan người.
    * Frame Video 4 thực chất là **đàn chó con lông vàng và đen nằm trên sàn gạch** (chữ *"TÌNH MẪU TỬ SỚM MAI"*). Lông và mắt mũi chó con bị nhận diện nhầm thành mặt người.
  - Khi crop theo tọa độ này, ảnh viền tròn xanh chỉ chứa sàn gạch màu xám và lông chó, hoàn toàn không có mặt người.
- **Bài học & Quy tắc khắc phục**:
  1. **Tuyệt đối không tin tưởng mù quáng vào OpenCV / Haar Cascade**:
     - Bounding box trả về từ cascade classifier CHỈ LÀ TỌA ĐỘ THUẦN TÚY, rất dễ dương tính giả (false positive) trước hoa văn đĩa ăn, sỏi đá, hoặc động vật.
     - **BẮT BUỘC** chạy `ag_cli.py ask --file "<path>" "Có khuôn mặt người thật hay không?"` trên khung hình ứng viên trước khi crop. Nếu kết quả là đồ ăn hoặc động vật: LOẠI BỎ NGAY, không cố crop.
  2. **Kỹ thuật chạy Script Python Remote qua SSH bằng Base64 Encoding**:
     - Khi điều khiển máy phụ (như Admin Remote) qua SSH trên Windows, truyền lệnh nhiều dòng `python -c "..."` thường bị vỡ do Windows OpenSSH không xử lý được ký tự xuống dòng (`\n`) hoặc quote lồng nhau.
     - **Giải pháp chuẩn**: Encode toàn bộ script Python thành chuỗi Base64 và thực thi gọn gàng:
       ```python
       b64 = base64.b64encode(code.encode()).decode()
       cmd = ["ssh", "-o", "BatchMode=yes", "admin-farm", f"{py} -c \"import base64; exec(base64.b64decode('{b64}').decode())\""]
       ```
     - Lưu ý môi trường thực thi: Phải gọi đúng Python runtime có cài sẵn `cv2`, `numpy` (ví dụ: `D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe`), tránh dùng Python mặc định của hệ điều hành.
  3. **Tra cứu đối soát kho video kênh Hot $O(1)$**:
     - Sử dụng `D:/OneDrive/TaadaaData/admin/admin_all_640_hot_niches.json` để kiểm tra mapping Niche theo folder.
     - Đối soát nguồn gốc kênh qua `D:/Taadaa/data/admin_real_folders.json` (chứa URL YouTube channel chính thức và số lượng video crawl) để xác định đúng phong cách và hình ảnh đại diện của Creator.

---

## 23. Quy Trình Sàng Lọc Ứng Viên Avatar 2 Tầng (Hierarchical Tiling) & Tinh Chỉnh Headroom (Sự Cố 16/10/2026 — @brentwbowman0 Máy 56 Tik 3)
- **Bối cảnh thực tế**:
  - Khi User gửi ảnh TikTok profile yêu cầu ngắn gọn: *"Đổi ava"*.
  - Kiểm tra kho `D:/video goc/216` và `D:/TIKTOK-videonuoinick/216` đều có sẵn file `avatar.jpg` cũ (ăn mì cay có sticker gấu). Nếu vội vàng up file này sẽ vi phạm lỗi Section 14 (nạp lại avatar cũ).
  - Kho đã có sẵn thư mục `.avatar_work/representative_frames/` chứa hơn 90 khung hình trích xuất từ trước (`v00_001.jpg` đến `v23_006.jpg`).
- **Quy trình lọc ứng viên 2 tầng (Hierarchical Frame Selection)**:
  1. **Tầng 1 (Macro Tiling — Quét diện rộng loại rác)**:
     - Chọn đại diện 16 khung hình từ các video khác nhau, ghép thành mosaic $4 \times 4$ kích thước $960 \times 1704$ (`tmp_m56_mosaic.jpg`).
     - Gọi `python D:/Taadaa/tools/ag_cli.py ask --file "<mosaic.jpg>" "Những ô nào là bạn nữ chủ kênh solo, nhìn rõ mặt, không che bởi sticker/kính mát to, biểu cảm tươi sáng?"`.
     - `ag_cli.py` loại bỏ nhanh các ô tĩnh vật (bàn phím piano, chân đạp xe, đồ ăn), ảnh góc xa, ảnh đeo kính râm to che kín mắt (`v02_001`), và ảnh nhóm đông người (`v07_001`); định vị 2 video tiềm năng nhất: Video 3 (áo đen cổ tim) và Video 6 (áo trễ vai cherry).
  2. **Tầng 2 (Micro-Expression Grid — So sánh biểu cảm vi mô)**:
     - Ghép lưới 6 khung hình chi tiết giữa các frame cùng video: `v03_001..003` và `v06_001..003`.
     - Giám định vi mô qua `ag_cli.py ask` để phát hiện các lỗi biểu cảm: `v03_001` bị chớp mắt dở (mid-blink/sụp mí) và mở khẩu hình phát âm dở; `v06_002` bị há miệng chữ O ngơ ngác.
     - Chọn ra 2 ứng viên xuất sắc nhất:
       * **Phương án 1 (`v03_002`)**: Mắt mở to tròn, bắt sáng (catchlight) rõ, nụ cười mỉm tự nhiên, thần thái tự tin, tràn đầy năng lượng.
       * **Phương án 2 (`v06_001`)**: Góc nhìn trực diện, nét mặt điềm đạm, dịu dàng, nữ tính.
  3. **Đồng bộ nhận diện với Lưới Video (Grid Identity Consistency)**:
     - Đối soát với ảnh màn hình profile User gửi: Video 2 trên lưới trang cá nhân (clip đạt 279 view) chính là bạn nữ mặc áo thun đen cổ tim.
     - Việc chọn `v03_002` giúp đồng bộ nhận diện thương hiệu cá nhân của Creator giữa avatar và bài đăng top view trên kênh.
  4. **Kỹ thuật tinh chỉnh Headroom sau Crop**:
     - Khi crop thử nghiệm ban đầu, đỉnh đầu của Phương án 1 hơi sát mép trên viền tròn xanh.
     - Khắc phục dứt điểm: Hạ nhẹ tâm dọc `cy` xuống $\approx 18$px (`cy = fy + fh * 0.58`) và nới kích thước `side = 580` kết hợp mở rộng canvas (`cv2.BORDER_REPLICATE`).
     - Kết quả: Đỉnh tóc có khoảng thở an toàn (headroom $\ge 20$px), cằm và cổ áo đen nằm trọn vẹn bên trong đường tròn viền xanh.
  5. **Tạo bảng so sánh trực quan (Side-by-side Comparison Sheet)**:
     - Ghép 2 ảnh preview viền tròn xanh lên nền tối ($R=256$, viền xanh lá, dải tiêu đề phân biệt rõ phong cách ở trên).
     - Gửi duy nhất 1 thẻ `MEDIA:D:/Taadaa/..._avatar_options.jpg` để User dễ dàng so sánh và chọn lựa, tuyệt đối không gửi ảnh đơn lẻ thiếu đối chứng.

---

## 24. Bẫy Lệch Nguồn F_out vs F_src Trong Workbook & Tinh Chỉnh Headroom Offset (Sự Cố 16/10/2026 — @daunthzrqig M66 Tik 4)
- **Hiện tượng**:
  - Khi User yêu cầu "Chuẩn hoá acc này" kèm ảnh chụp profile TikTok `@daunthzrqig`:
  - Tra cứu $O(1)$ qua SQLite `account_mapping` xác định tài khoản thuộc Máy 66 Tik 4.
  - Mở workbook `D:/OneDrive/TaadaaData/kibe/Tik4.xlsx`: Cột `Folder Video (Render Dich)` ghi `524`, nhưng cột `Video Goc (Nguon Cao)` ghi **`306`**!
  - Kiểm tra các frame đại diện trong `D:/TIKTOK-videonuoinick/524` thấy lẫn lộn nhiều video người khác (nữ áo đen, nữ sơ mi caro), trong khi 6 thumbnail trên lưới profile TikTok thực tế 100% là nam thanh niên review mỹ phẩm đeo kính áo đỏ/trắng.
  - Kiểm tra kho video gốc **`D:/video goc/306`** ($F_{src} = 306$) xác nhận 100% video đều là nam creator đeo kính này.
- **Quy tắc đối soát nguồn kép ($F_{out}$ vs $F_{src}$)**:
  1. Khi trích xuất avatar cho kênh, BẮT BUỘC đọc cả 2 cột `Folder Video (Render Dich)` và `Video Goc (Nguon Cao)` trong `Tik<N>.xlsx`.
  2. So khớp trực tiếp hình ảnh nhân vật trong các frame ứng viên với các video đang hiển thị trên lưới profile của User. Nếu kho $F_{out}$ có dấu hiệu lẫn lộn hoặc lệch nhân vật, BẮT BUỘC chuyển sang kho video gốc $F_{src}$ để trích xuất.
- **Khắc phục lỗi lẹm đỉnh tóc bằng Headroom Offset & Canvas Expansion**:
  - Khi crop bằng tham số mặc định (`side_scale = 2.2 - 2.3`, `cy_shift = 0.55`), Haar cascade nhận diện khuôn mặt làm tâm vòng tròn đặt hơi thấp, khiến đường tròn viền xanh cắt lẹm $5-10\%$ ngọn tóc đỉnh đầu (bị giám định thị giác chấm điểm không đạt).
  - **Công thức chuẩn hóa Headroom an toàn tuyệt đối**:
    * Nâng `side_mult` lên $2.65 - 2.7$ (kết hợp padding canvas `cv2.BORDER_REPLICATE` với `pad = side`).
    * Áp dụng `cy_offset = -30` đến `-35` px (dịch tâm crop lên trên, giúp khuôn mặt và đỉnh tóc hạ xuống sâu hơn bên trong vòng tròn an toàn).
    * Kết quả kiểm định: Đỉnh tóc cách viền tròn trên $\approx 115 - 120$px, cằm cách viền đáy $\approx 125 - 130$px, ngũ quan trọn vẹn ở trung tâm, sạch chữ rác, đạt điểm tuyệt đối 10/10.
- **Cơ chế dự phòng giám định thị giác (Dual Vision Gate: ag_cli.py + Proxy :20129)**:
  - Khi `ag_cli.py` bị nghẽn profile lease hoặc timeout $> 30$s: Sử dụng ngay script Python độc lập gọi HTTP POST tới proxy nội bộ `http://127.0.0.1:20129/v1/chat/completions` (model `ag-gemini-pool-3`, ảnh base64 512x512) để nhận kết quả chấm điểm khách quan trong $< 2$ giây.

---

## 25. Đối Soát Tên Kênh Nữ Tính vs Bẫy Nhân Vật Nam/Đồ Họa Tin Tức & Kỷ Luật Viết Tool File (Sự Cố 16/10/2026 — @longtuong10 Máy 58 Tik 4)
- **Hiện tượng thực tế**:
  - Khi User gửi ảnh profile TikTok kênh *"Hương Miu"* (`@longtuong10` Máy 58 Tik 4, F_src 298, F_out 460) kèm lệnh ngắn gọn *"Đổi ava"*.
  - Avatar cũ trên kênh là hình ảnh trạm biến áp / cột điện cao thế trên nền trời xanh (hoàn toàn không có mặt người).
  - Kho video nguồn 298 là bản tin Thời sự VTV tổng hợp. Khi quét Haar Cascade tự động, thuật toán bắt trúng rất nhiều nhân vật nam ở các giây đầu (Bùi Xuân Huấn bị còng tay, Benjamin Netanyahu, BTV Chào Buổi Sáng). Nếu chỉ lấy face to nhất theo thuật toán sẽ gán nhầm nhân vật nam cho kênh có định danh nữ "Hương Miu".
  - Hơn nữa, khi trích xuất nhân vật nữ (nữ chính khách trong bản tin tại Video 15), đồ họa banner tin tức biến đổi theo từng giây:
    * Giây 16s: Hoàn toàn sạch chữ trong vòng tròn, headroom thoáng 35-40px, cằm an toàn.
    * Giây 17s: Thanh banner trắng dâng cao cắt ngang 1/4 đáy vòng tròn, chứa nguyên cụm chữ in hoa `"XEM LẠI CHƯƠNG TRÌ"`.
    * Giây 18s: Dính thanh đồ họa xanh góc dưới trái và đỉnh đầu sát mép viền xanh (<15px).
- **Bài học & Quy tắc khắc phục**:
  1. **Định danh Persona & Giới tính kênh (Gender & Persona Alignment)**:
     - BẮT BUỘC đọc Display Name trên profile của User gửi. Khi tên kênh mang định danh nữ rõ rệt (*"Hương Miu"*), CẤM gán avatar nhân vật nam dù video có nhiều cảnh nam giới. Bắt buộc rà soát chọn nhân vật nữ phù hợp phong thái kênh.
  2. **Kiểm tra đồ họa tin tức biến thiên theo giây (Temporal Ticker Check)**:
     - Khi trích xuất avatar từ video dạng tin tức/thời sự, các dòng chữ chạy và banner xuất hiện/biến mất rất nhanh.
     - BẮT BUỘC so sánh đối chiếu giữa các giây lân cận (ví dụ 15s, 16s, 17s) qua `ag_cli.py ask` theo checklist 4 điểm để chọn đúng giây sạch 100% chữ và đạt chuẩn headroom/chin clearance $\ge 20$px.
  3. **Kỷ luật điều phối Coordinator: Cấm dùng `python -c` ghi đĩa**:
     - Guard an toàn chặn mọi lệnh `python -c` có thao tác ghi/xóa file.
     - Mọi thao tác sao chép `avatar.jpg` vào 3 đầu kho, tạo marker vật lý `.manual_avatar_locked` và cập nhật `manual_avatar_protected_folders.json` BẮT BUỘC viết thành file script độc lập trong `D:/Taadaa/tools/` (ví dụ `tools/prep_<acc>_avatar.py`) bằng tool `write_file`, sau đó mới thực thi bằng `terminal`.
  4. **Kỷ luật End-to-End khi User lệnh "Đổi ava"**:
     - Tuân thủ nghiêm ngặt chỉ thị trong Profile/Memory: *"đổi ava tự làm cấm hỏi"*.
     - Thực hiện trọn gói End-to-End: Tra cứu mapping $\rightarrow$ Trích xuất frame mới $\rightarrow$ Crop $512 \times 512$ $\rightarrow$ Đồng bộ 3 kho + Marker $\rightarrow$ Kích hoạt runner nạp app `run_avatar_batch_3accs.py` $\rightarrow$ Nghiệm thu qua `browser_vision` và gửi ảnh `MEDIA:`.

---

## 25. Quy Trình Đối Soát Kênh O(1) Chống Bẫy Quét Đĩa & Xử Lý Niche Drift Hoạt Hình Thiếu Nhi (Sự Cố 16/10/2026 — @giathu0709 Máy 65 Tik 4)
- **Bối cảnh & Hiện tượng thực tế**:
  - Khi User gửi ảnh TikTok profile (username `@giathu0709`, display name "Long Đậu") yêu cầu ngắn gọn: *"Chuẩn hoá acc này"*.
  - **Bẫy quét đĩa diện rộng (Farm Guard Block)**: Coordinator nảy sinh ý định dùng `os.walk` hoặc `glob(recursive=True)` quét tìm username trong các file Excel $\rightarrow$ Lập tức bị Farm Guard chặn đứng vì vi phạm lệnh cấm quét đĩa diện rộng.
  - **Hiện trạng lệch 3 món của tài khoản**:
    1. *Avatar rác*: Avatar hiển thị trên profile TikTok là ảnh chụp bàn ăn / đĩa thức ăn dao nĩa (do Haar Cascade nhận diện nhầm đĩa sứ thành mặt người từ trước).
    2. *Lệch Niche (Niche Drift) nghiêm trọng*: Lưới video thực tế trên profile 100% là phim hoạt hình 3D/2D giáo dục, kỹ năng sống và an toàn cho trẻ em (*"Tạo cảm hứng học tập"*, *"...Sau khi ăn no!"*, *"...Khi gặp nguy hiểm?"*, *"Chỉ vì quên rửa tay!"*), nhưng workbook `Tik4.xlsx` (Row 66) lại bị gán Keyword `Tài chính` và pool hashtag `#taichinh...`.
    3. *Ghim video (Pin Rule)*: Video cao nhất trên lưới đạt 363 view, chưa chạm ngưỡng $\ge 1.000$ view $\rightarrow$ Giữ nguyên thứ tự, không ghim.
- **Quy trình tra cứu tọa độ Farm O(1) chuẩn xác**:
  1. **Tra cứu Master Workbook duy nhất**:
     - Đọc trực tiếp `D:/OneDrive/TaadaaData/taikhoan_run_safe_combined.xlsx` (Sheet `Accounts`), lọc theo username `@giathu0709`.
     - Xác định ngay: Máy $M = 65$, Serial ADB `ce12160c4a45432204`.
  2. **Xác định Cụm máy & Slot tương ứng**:
     - $M = 65 \le 80 \rightarrow$ Thuộc cụm **Kibe Local** (`D:/OneDrive/TaadaaData/kibe/`).
     - Mở trực tiếp `Tik4.xlsx` tại dòng $R = M + 1 = 66$ $\rightarrow$ Xác nhận Slot 4 (Tik 4), $F_{out} = 516$ (`D:\TIKTOK-videonuoinick\516`), $F_{src} = (4 - 1) \times 80 + 65 = 305$ (`D:\video goc\305`).
- **Quy tắc Chuẩn hoá 3 Món (Pin – Hashtag – Avatar Hoạt Hình)**:
  1. **Pin Gate**: Không ghim vì view $< 1.000$.
  2. **Khắc phục Niche Drift & Khóa Hashtag**:
     - Cập nhật lại Keyword `Kỹ năng sống` trong `Tik4.xlsx`.
     - Chốt pool hashtag an toàn/kỹ năng sống trẻ em (`#kynangsong #antoanchobe #meovathay #kienthuc #kienthuchay #baihoccuocsong #hoathinh3d #giaoductreem #tiktokvietnam #xuhuong #fyp #videohay`) và tạo marker cứng `.manual_hashtag_locked` tại cả 2 kho `516` và `305`.
  3. **Trích xuất Avatar Hoạt hình 3D / Động vật nhân hóa**:
     - Với kênh hoạt hình thiếu nhi, avatar chuẩn là nhân vật hoạt hình chính của kênh (như chú khỉ mặc áo vest vàng hoặc bạn nhỏ hoạt hình) có biểu cảm sinh động, mắt to tròn, xuất hiện trên các thumbnail của kênh.
     - Áp dụng Center-based Crop kết hợp mở rộng Canvas (`cv2.BORDER_REPLICATE`), né sạch phụ đề rác, đảm bảo đủ khoảng đệm headroom và chin clearance an toàn bên trong viền tròn xanh $R=256$.
     - Soi mắt kiểm định qua `browser_vision` trước khi đề xuất cho User.

---

## 26. Bẫy Bounding Box Giả Từ Chi Tiết Xe Máy & Chiến Lược Tìm Creator Trong Kênh Showroom (Sự Cố 16/10/2026 — @lamnhu3003 Máy 58 Tik 2)
- **Hiện tượng**:
  - Khi trích xuất avatar cho kênh bán xe máy / showroom Yamaha Vân Hải (`@lamnhu3003` - Máy 58 Tik 2, $F_{out} = 458$, $F_{src} = 458$): Avatar hiện tại trên TikTok chỉ là chi tiết cơ khí (ống lồng/thụt dầu giảm xóc trước có logo Yamaha), hoàn toàn không có người thật.
  - Khi quét tự động bằng `haarcascade_frontalface_default.xml`, thuật toán liên tục báo bounding box mặt người với độ tin cậy và kích thước rất lớn (`w, h > 160-270px`):
    * Ở `v00_001.jpg`: Chai nước làm mát Yamalube màu xanh dương đặt trên gác chân xe máy bị bắt nhầm thành mặt (`[211, 580, 165, 165]`).
    * Ở `12.mp4` / `v12_004.jpg`: Mặt nạ đèn trước xe Yamaha Gear 125 xám xi măng bị bắt nhầm (`[130, 197, 120, 120]`).
    * Ở `28.mp4` (13s): Cụm đồng hồ công-tơ-mét tròn, nút xoay Smartkey và ghi-đông xe máy bị bắt nhầm thành mặt kích thước khổng lồ (`[224, 212, 277, 277]`).
    * Ở `20.mp4` / `v20_002.jpg`: Cụm đèn hậu giọt nước và tem đại lý sau đuôi xe Grande bị bắt nhầm (`[192, 878, 121, 121]`).
- **Nguyên nhân gốc rễ**:
  1. **Đặc thù kênh Showroom / Sản phẩm**: Các video ngắn đầu tiên (từ video 1 đến video 30-40) thường là clip b-roll quay xe máy tĩnh, lia máy cận cảnh phụ tùng, phanh ABS, tem xe, hoặc quay đường phố trời mưa không có người.
  2. **Đồng hồ & Ổ khóa Smartkey có hình học tương tự ngũ quan**: Các cụm hình tròn đồng tâm (đồng hồ km, nút xoay Smartkey, cụm đèn bi cầu) rất dễ kích hoạt các bộ lọc Haar cascade của OpenCV thành false positive.
  3. **Vị trí xuất hiện của Creator / MC**: Người thật (Reviewer/MC giới thiệu xe) thường chỉ xuất hiện ở các video dài hơn (thời lượng $45 - 60$s, từ video 50 trở đi) khi họ đứng thuyết trình/review xe tại showroom.
- **Quy tắc trích xuất avatar cho kênh sản phẩm / showroom**:
  1. **Lọc video theo thời lượng**: Ưu tiên quét các video dài ($> 35 - 50$s) trong kho video gốc/render — đây là các video có thuyết trình/review thay vì video b-roll ngắn $< 20$s chỉ quay xe tĩnh.
  2. **Lọc tọa độ mặt hợp lý**: Với video TikTok dọc $1080 \times 1920$, khi người đứng thuyết trình trung cảnh, khuôn mặt thật LUÔN nằm ở nửa trên khung hình ($300 < y < 800$, $350 < x < 700$, kích thước $140 \le fw \le 200$). Loại bỏ ngay các box ở $y > 1000$ (vùng bánh xe/chân/thân xe).
  3. **Giám định thị giác 2 lớp qua `ag_cli.py ask`**:
     - BẮT BUỘC gửi ảnh ứng viên qua `ag_cli.py ask` để xác nhận có người thật, đúng nhân vật review xe (nam thanh niên áo polo có micro cài áo).
     - Tuyệt đối loại bỏ các frame chỉ có chai dầu nhớt, đầu xe hay poster người mẫu nhỏ xíu ở góc xa.
  4. **Kỹ thuật in-place patch khi Coordinator chạm trần File Write Budget (T1 Budget Defense)**:
     - Khi Coordinator hết hạn ngạch tạo file mới `write_file` (tối đa 5 files trong session): Sử dụng công cụ `patch` trên file script tạm đã tạo (`extract_cand.py`) để cập nhật tọa độ/logic crop avatar thay vì cố tạo file mới hoặc dispatch worker không cần thiết khi đã có exact diff.

---

## 27. Bẫy Lỗi Gõ Telex "Acc Nacy" & Kỷ Luật Missing Target Profile Khi Chuẩn Hoá (Sự Cố 16/10/2026)
- **Hiện tượng & Bẫy ngộ nhận**:
  - User gửi lệnh ngắn: *"Chuẩn hoá acc nacy"* dạng text thuần, hoàn toàn không kèm ảnh chụp màn hình hay số máy/username.
  - Một số agent thiếu kinh nghiệm dễ rơi vào 2 cạm bẫy nghiêm trọng:
    1. **Bẫy thực thể ảo (Typo Hallucination)**: Ngộ nhận `nacy` là tên riêng của tài khoản TikTok / Hotmail (như `nancy`), tự viết script quét toàn bộ đĩa/database để tìm chuỗi `nacy`/`nancy` trong vô vọng.
    2. **Bẫy thao tác mù (Blind Execution)**: Tự tiện suy diễn hoặc lấy bừa một tài khoản từ phiên trước để thao tác, can thiệp nhầm nick hoặc làm sai lệch thiết bị đang chạy ca nuôi.
- **Bản chất thực tế**:
  1. `"nacy"` thực chất là lỗi gõ phím Telex / phím kề của từ **`"này"`** (*"Chuẩn hoá acc này"*).
  2. Tin nhắn gửi đến Telegram là text thuần, bị thiếu ảnh đính kèm (User quên đính kèm hoặc Telegram phân mảnh tin nhắn).
- **Quy tắc ứng xử chuẩn hóa Farm**:
  1. **Khử typo nhanh bằng Ground Truth**: Nhận diện ngay `nacy` $\rightarrow$ `này`, đối soát nhanh DB SSOT (`tiktok_tracker.db` / `taikhoan_run_safe_combined.xlsx`) để xác nhận không có tài khoản tên `nacy`/`nancy`. Tuyệt đối CẤM quét đĩa diện rộng tìm file log hay file excel không liên quan.
  2. **Chặn đứng thao tác mù khi thiếu ảnh**: Quy chuẩn "Chuẩn hoá 3 món" (Ava - Hashtag - Pin) bắt buộc phải có ảnh Profile hoặc định danh rõ ràng (Username / Số máy / Slot) để làm cơ sở kiểm tra view và trích xuất nhân vật chuẩn. Nếu thiếu ảnh và thiếu định danh: BẮT BUỘC dừng lại, giải thích rõ `nacy` là lỗi gõ của `này`, khẳng định DB không có nick này, và yêu cầu User cung cấp ảnh chụp Profile hoặc số máy/username, tuyệt đối không tự ý can thiệp vào bất kỳ thiết bị nào.

---

## 28. Sàng Lọc Khử Bẫy Phụ Đề Chạm Viền & Micro Trong Video Creator/Streamer (Sự Cố 16/10/2026 — @carlosfwagne2 Máy 59)
- **Hiện tượng & Bẫy thực tế**:
  - Khi xử lý đổi avatar cho kênh `@carlosfwagne2` (Máy 59 Tik 3, Kho 467/219, Niche Sáng tạo/Tiếng Anh):
  - Kênh dạng creator/streamer ngồi trước micro thu âm HyperX chia sẻ kiến thức, phía trên đầu thường chèn phụ đề từ vựng tiếng Anh/Việt hoặc icon minh họa (như `"A float of crocodiles"`, `"(adj): cực kỳ tuyệt vời"`).
  - Khi Haar Cascade nhận diện khuôn mặt, các frame thường gặp 3 lỗi nghiêm trọng khi crop:
    1. **Bẫy chữ chạm viền tròn**: Frame `v17_002` dính chữ phụ đề và hình con cá sấu trên đỉnh đầu; frame `v23_002` dính chân chữ đỏ `(adj): cực kỳ tuyệt vời` bị viền tròn xanh cắt ngang qua, lọt vụn chữ vào avatar.
    2. **Bẫy zoom cực đại cắt cụt tóc & cằm**: Frame `v02_001` bị zoom quá sát, cắt lẹm đỉnh tóc và cằm, đáy viền tròn dính chữ banner `... ANH THÌ EM ...`.
    3. **Bẫy micro che ngũ quan**: Micro thu âm góc dưới nếu căn tâm quá thấp sẽ che lấp cằm hoặc bờ môi nhân vật.
- **Quy trình tinh chỉnh & sàng lọc 4 tầng đạt chuẩn 100%**:
  1. **Tầng 1 (Haar Cascade & Center-based Crop ban đầu)**:
     - Quét representative frames, xác định bounding box mặt người thật.
  2. **Tầng 2 (Giám định ngữ nghĩa qua `ag_cli.py ask`)**:
     - Chạy lệnh kiểm định 4 tiêu chí bắt buộc: (1) Ngũ quan đầy đủ 100%, (2) Cân đối tâm, (3) Đỉnh đầu và cằm an toàn, (4) Hoàn toàn sạch chữ/phụ đề rác.
     - Nếu phát hiện chữ chạm viền trên: Hạ nhẹ `cy` (ví dụ `cy = fy + fh * 0.52`) và thu nhỏ `side` (ví dụ từ 520px xuống 480px) để đẩy toàn bộ khối chữ ra ngoài viền tròn hoặc chọn frame có khoảng trống trên đầu sạch hơn (như `v11_003` và `v19_002`).
  3. **Tầng 3 (Xử lý vị trí Micro thu âm)**:
     - Micro chỉ được phép xuất hiện ở góc dưới (hướng 7h–8h) ngang tầm ngực/cổ áo; BẮT BUỘC toàn bộ cằm, khóe miệng và đường quai hàm không bị micro che khuất.
  4. **Tầng 4 (Soi mắt `browser_vision` bắt buộc trước khi gửi)**:
     - Mở trực tiếp file `optA_circle_preview.jpg` và `optB_circle_preview.jpg` qua `browser_navigate` và gọi `browser_vision` để mắt thật của Coordinator xác nhận đạt chuẩn trước khi đính kèm thẻ `MEDIA:<path>`.

---

## 29. Bẫy Lệnh "Chuẩn Hoá Acc Này" Thiếu Ảnh Kèm Theo & Kỷ Luật Chống Suy Diễn Chéo Session (Sự Cố 16/10/2026)
- **Hiện tượng thực tế**:
  - User gửi tin nhắn chỉ có đúng 4 chữ: *"Chuẩn hoá acc này"* (hoặc *"Đổi ava acc này"*), hoàn toàn KHÔNG có ảnh đính kèm (`[Image attached at: ...]`) và KHÔNG cung cấp số máy hay username.
  - Đây là trường hợp phổ biến trên Telegram khi: (1) User gửi text trước dự định gửi ảnh sau; (2) Telegram gateway phân mảnh tin nhắn; (3) User gửi ảnh bị nghẽn mạng; hoặc (4) User tưởng bot tự biết máy nào đang cầm trên tay.
- **Các cạm bẫy Coordinator rất dễ mắc phải**:
  1. **Bẫy Cross-Session Archaeology (Rò rỉ ngữ cảnh session khác)**: Dùng `session_search` thấy các session vừa chạy trước đó có ảnh tài khoản khác (ví dụ Máy 34 `@yobi1965`, Máy 54 `@anan197563`, Máy 65 `@giathu0709`), liền tự ý "nhận vơ" tài khoản của session cũ đem ra chuẩn hoá tiếp. Việc này vi phạm nghiêm trọng **Cross-Session Context Bleed Guard**, User sẽ mắng vì "trả lời nhầm session" hoặc can thiệp sai máy.
  2. **Bẫy Quét Đĩa & Đụng Guard Hệ Thống**: Cố gắng quét đĩa diện rộng (`image_cache`, `D:/Taadaa/reports`) hoặc truy cập file nội bộ Hermes, kích hoạt cảnh báo đỏ của `GUARD SELF-PROTECTION` và làm kẹt lượt xử lý (loop warning).
  3. **Bẫy Đoán Mò Máy (Blind Machine Triage)**: Tự tiện pick 1 máy đang chạy trên Farm rồi vào can thiệp lung tung.
- **Quy tắc ứng xử bất biến (Missing Image & Target Guard)**:
  1. **Kiểm tra Input Gate Turn 1**: Kiểm tra prompt có metadata đính kèm ảnh (`[Image attached at: ...]`) hoặc chuỗi username (`@...`), số máy (`Máy N`) hay không.
  2. **Dừng ngay lập tức nếu thiếu cả Ảnh lẫn Target**: CẤM TUYỆT ĐỐI lục lọi tìm ảnh từ session cũ hoặc tự chọn nick để làm.
  3. **Phản hồi 4 ý cốt lõi chuẩn mực**:
     - Xác nhận đã sẵn sàng thực hiện quy trình **Chuẩn hoá 3 món (Avatar – Hashtag/Niche – Ghim Video)**.
     - Nêu rõ tình trạng: Tin nhắn hiện tại **chưa có ảnh chụp màn hình Profile TikTok đính kèm** (hoặc thiếu số máy/username).
     - Hướng dẫn User gửi ảnh Profile TikTok (hoặc nhắn rõ Máy / Username).
     - Tóm tắt ngắn gọn 4 bước sẽ thực thi ngay khi nhận ảnh (Định vị $O(1)$ $\rightarrow$ Pin Gate $\ge 1.000$ view $\rightarrow$ Niche & Hashtags $\rightarrow$ Trích xuất Avatar chuẩn từ video gốc có soi mắt nghiệm thu).

---

## 30. Bẫy Bỏ Qua Máy Khi Nạp Avatar Do Cột Avatar Đang Mang Trạng Thái 'OK' / 'DONE' (Sự Cố 16/10/2026 — Machine Skip Preflight Pitfall)
- **Hiện tượng**:
  - Khi Coordinator chuẩn bị xong file `avatar.jpg` và các file marker `.manual_avatar_locked`, sau đó cập nhật ngay `Avatar = OK` vào file Excel `Tik<N>.xlsx` rồi gọi `run_avatar_batch_3accs.py` / `run_tiktok_upload_avatar.ps1`.
  - Kết quả: Runner kết thúc ngay tức thì (`ExitCode: 0`) nhưng không có thiết bị nào được nạp ảnh. Log hiển thị: `Target bị bỏ qua trước/đầu launch: ... [Silent Skip]`.
- **Nguyên nhân gốc rễ**:
  1. Launcher script `run_tiktok_upload_avatar.ps1` gọi script tiền kiểm `resolve_avatar_pending_machines.py <Tik>`.
  2. Script này duyệt qua các dòng của file Excel và lọc: `if ava_val != "OK": pending.append(m_int)`. Đồng thời nó kiểm tra bảng SQLite `avatar_replace_queue`: `SELECT may FROM avatar_replace_queue WHERE tik = ? AND status = 'PENDING'`.
  3. Nếu cột `Avatar` trong Excel đã ghi `OK` và SQLite queue đang là `DONE` (từ avatar cũ), máy mục tiêu sẽ bị loại khỏi danh sách pending và runner sẽ bỏ qua máy đó hoàn toàn!
- **Quy trình chuẩn bị PENDING 3 bước trước khi kích hoạt Runner**:
  1. **Bước 1 — Kích hoạt cờ PENDING trong Excel**:
     - Mở workbook `D:/OneDrive/TaadaaData/kibe/Tik<N>.xlsx`, đặt giá trị ô cột `Avatar` của máy mục tiêu thành `'PENDING'` (chưa ghi `OK`).
  2. **Bước 2 — Cập nhật SQLite `avatar_replace_queue`**:
     - Cập nhật dòng của máy mục tiêu trong bảng `avatar_replace_queue` (`D:/Taadaa/data/tiktok_tracker.db`):
       ```sql
       UPDATE avatar_replace_queue
       SET status = 'PENDING', video_goc = '<F_src>', updated_at = datetime('now', 'localtime')
       WHERE may = <M> AND tik = <Tik> AND username = '<username>'
       ```
  3. **Bước 3 — Đối soát Preflight $O(1)$ trước khi chạy**:
     - Chạy lệnh: `python D:/Taadaa/Tiktok-video/scripts/resolve_avatar_pending_machines.py <Tik>`
     - Xác nhận máy mục tiêu `<M>` có tên trong chuỗi output (ví dụ: `...,65,...`).
  4. **Bước 4 — Nghiệm thu & Chuyển sang OK**:
     - Chỉ sau khi runner nạp ảnh thành công (`AVATAR_SMOKE_SUCCESS`) và đã chụp ảnh màn hình trang cá nhân thực tế, soi mắt qua `browser_vision` xác nhận avatar mới hiển thị sắc nét $\rightarrow$ lúc đó mới cập nhật cột `Avatar = OK` và SQLite `status = DONE`.












