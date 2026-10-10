# Dual Standardization: Avatar & Hashtag Niche Realignment (2026-10-10)

## Context & Operator Order Pattern
Khi Operator gửi ảnh screenshot Profile TikTok từ điện thoại cá nhân (ví dụ: `@annapmfdh0a` "Ngô Bảo Long" Máy 44 Tik 6 Kibe) kèm chỉ thị:
> *"Chuẩn hoá ava hashtag kênh này"*

Đây là lệnh kép yêu cầu xử lý đồng bộ cả 2 tầng của kênh:
1. **Tầng Thị giác (Visual Avatar):** Nhận diện niche thực tế của các video đã đăng trên lưới profile, tìm và trích xuất avatar độc bản chuẩn nét từ chính video của kênh, thay thế avatar cũ lệch ngách (ví dụ: kênh thú cưng/mèo nhưng avatar cũ là hình cô gái trẻ).
2. **Tầng Thuật toán (Algorithm Metadata):** Đồng bộ `Keyword Video` và `Hashtag Pool` trong sổ cái Excel (`Tik<N>.xlsx`) và `state.db` về đúng 1 trong 12 Niche Hot (ví dụ: chuyển từ nhãn chung chung `Hài hước` sang `Thú cưng cute` kèm bộ hashtag chuyên biệt để TikTok AI phân phối đúng tệp khán giả mục tiêu).

---

## 5-Step End-to-End Workflow

### Bước 1: Định danh O(1) Máy, Slot Tik & Khám nghiệm Video
1. **Truy vấn định danh O(1):**
   ```python
   # Tra cứu username từ ảnh profile trong tiktok_tracker.db
   SELECT may, tik, folder_video, video_goc FROM avatar_replace_queue WHERE username = 'annapmfdh0a';
   # Kết quả: Máy 44, Tik 6, Folder 350
   ```
2. **Khám nghiệm video thực tế:**
   - Đọc các video trong `D:/TIKTOK-videonuoinick/<Folder>/` (`1.mp4` – `54.mp4`) và đối chiếu với số video đã đăng trên profile (ví dụ: 7 clip).
   - Dùng WinRT OCR trích xuất phụ đề/tiêu đề các clip để xác định nhân vật chính của kênh (ví dụ: Mèo Dứa, Mèo Mi Mi, Mèo Mun $\to$ Niche `thucung` / Thú cưng cute).

---

### Bước 2: Trích xuất Avatar Độc bản bằng OpenCV Cat Face Cascade
1. **Sử dụng bộ nhận diện tích hợp:**
   - Trong `cv2.data.haarcascades`, OpenCV có sẵn `haarcascade_frontalcatface.xml` và `haarcascade_frontalcatface_extended.xml`.
   ```python
   import cv2
   cat_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalcatface.xml')
   faces = cat_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=2)
   ```
2. **Quy chuẩn tỷ lệ vàng khung tròn TikTok:**
   - **Tâm mặt:** Cân bằng đối xứng trục ngang (độ lệch ngang $< 5\text{px}$ so với tâm 256).
   - **Headroom (Khoảng thở đỉnh đầu):** Đạt $8\text{--}12\%$ (khoảng $45\text{--}60\text{px}$ từ đỉnh tai đến mép trên ảnh 512).
   - **Diện tích mặt:** Chiếm $70\text{--}85\%$ khung hình vuông, giúp khi hiển thị trong hình tròn TikTok mini (~40-80px trên feed) khuôn mặt vẫn nổi bật rõ nét.
   - **Độ sạch:** Kiểm tra WinRT OCR đạt 0 ký tự chữ/phụ đề lẹm trên ảnh crop.

---

### Bước 3: Dựng Bảng Đối chiếu 2x2 Showcase Card & Kiểm tra Gate 6
Tránh ghép dẹt ngang (panoramic) làm co rút trên mobile Telegram. Dựng bảng vuông $1024\times 1024$ (4 ô $512\times 512$):
- **Ô 1 (Top-Left):** Avatar cũ lệch ngách (crop trực tiếp từ screenshot profile của Operator).
- **Ô 2 (Top-Right):** Avatar mới chuẩn ngách (ảnh vuông 512x512 sắc nét, nhân vật chính).
- **Ô 3 (Bottom-Left):** Option dự phòng (nhân vật từ clip viral nhiều view nhất của kênh).
- **Ô 4 (Bottom-Right):** Mô phỏng khung tròn TikTok Circular Mask (nền trắng bao quanh) chứng minh tai/mắt/cằm không bị lẹm viền.
- Dùng WinRT OCR xác nhận các nhãn text trên ảnh đọc được rõ ràng trước khi gửi `MEDIA:`.

---

### Bước 4: Khóa Nguồn & Đồng bộ 4 Tầng Dữ liệu
1. **Đồng bộ file ảnh nguyên tử 2 đầu kho:**
   - Ghi đè qua file trung gian `.tmp.jpg` $\to$ `os.replace` vào cả 2 đầu:
     * `D:/TIKTOK-videonuoinick/<Folder>/avatar.jpg`
     * `D:/video goc/<Folder>/avatar.jpg`
   - Xác nhận mã băm MD5 ở 2 đầu kho hoàn toàn trùng khớp.
2. **Khóa cứng sổ cái `Tik<N>.xlsx`:**
   - Khóa cột `video gốc = Folder Video` (chống trôi lệch không gian số).
   - Cập nhật `Keyword Video = 'Thú cưng cute'`.
   - Cập nhật `Hashtag Pool = '#thucung #thucungcute #meocung #meohaihuoc #boss #sen #thucungdangyeu #petvietnam #tiktokvietnam #xuhuong #fyp #videohay'`.
   - Đặt cột `Avatar = 'PENDING'`.
   *(Lưu ý: Mở workbook với `openpyxl.load_workbook(path)` KHÔNG dùng `data_only=True` khi ghi)*.
3. **Đồng bộ Database Tracker & State:**
   - `UPDATE avatar_replace_queue SET video_goc = '<Folder>', status = 'PENDING', last_error = NULL, updated_at = datetime('now', 'localtime') WHERE username = '<handle>';`
   - `UPDATE folders SET niche = 'thucung' WHERE folder_num = <Folder>;` trên cả 2 database `state.db` (ổ C: và D:).

---

### Bước 5: Kích hoạt Runner Chạy nền Event-Driven
1. **Viết script launcher độc lập qua `write_file`:**
   - Tránh gõ lệnh inline nhiều dòng trong terminal MSYS bash để không bị lỗi `open: embedded null character in path`.
2. **Chạy qua canonical avatar runner:**
   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 -Tik <Tik> -MaxParallel 1 -HostConfigPath D:\Taadaa\machine-config\kibe.yaml -ForceAvatarMachineList "<May>"
   ```
3. **Event-driven wakeup:** Kích hoạt với `terminal(command=..., background=True, notify_on_complete=True, timeout=300)`. Kết thúc lượt trả lời để harness tự đánh thức và nghiệm thu 3 lớp khi tiến trình hoàn tất.
