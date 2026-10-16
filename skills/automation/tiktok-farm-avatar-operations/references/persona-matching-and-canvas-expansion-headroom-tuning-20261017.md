# Persona Alignment & Canvas Expansion Headroom Tuning (2026-10-17)

## 1. Sự Cố "Chọn Ava Khác Đi" & Định Danh Nhân Vật Khớp Với Tên Kênh (Persona Alignment Trap)
- **Bối cảnh thực tế (Kênh Hương Miu `@longtuong10` - Máy 58 Tik 4)**:
  - Khi được yêu cầu "Đổi ava", thuật toán Haar Cascade quét folder $F_{src} = 298$ (Niche: *Câu chuyện cuộc sống / Thời sự*) và tìm thấy khuôn mặt nữ rõ nét nhất ở `15.mp4` (giây 16).
  - Nhân vật là nữ chính khách Nhật Bản (bà Sanae Takaichi) mặc vest xám đậm, đeo chuỗi ngọc trai phát biểu trong bản tin thời sự.
  - Sau khi đưa phương án, User lập tức chỉ đạo: *"Chuẩn hoá luôn kênh đi. Và chọn ava khác"*.
- **Nguyên nhân gốc rễ**:
  - **Lệch Persona (Hình tượng nhân vật vs Tên kênh)**: Kênh mang tên cá nhân/nữ tính **"Hương Miu"**. Mặc dù bà Sanae Takaichi là nữ và ảnh rất nét, nhưng hình ảnh một nữ chính khách nước ngoài đứng tuổi phát biểu trong bản tin thời sự hoàn toàn lệch pha với cảm giác một kênh creator/tâm sự của bạn trẻ Việt Nam.
  - **Quy tắc Persona Alignment**:
    1. Khi kênh có tên riêng trẻ trung / nữ tính (ví dụ: *Hương Miu, Vy Miu, Linh Ka, Bé...*): CẤM lấy hình ảnh chính khách đứng tuổi, BTV tin tức cứng nhắc, hoặc người nước ngoài trong phóng sự tin tức.
    2. BẮT BUỘC rà soát các video khác trong folder nguồn để tìm đúng hình tượng: Nữ trẻ (20–26 tuổi), nụ cười rạng rỡ, bối cảnh gần gũi (podcast tâm sự như clip 53 *"Bạn Kể TÔI NGHE"*, vlog đời thường).

---

## 2. Kỹ Thuật Canvas Expansion & Headroom Tuning Khắc Phục Lẹm Đỉnh Tóc
- **Hiện tượng**:
  - Khi crop nhân vật nữ ở clip `53.mp4` (33s), thuật toán crop mặt thông thường đặt viền tròn quá sát đỉnh đầu.
  - Giám định `ag_cli.py ask` phát hiện: *"Phần đỉnh đầu/ngọn tóc trên cùng chạm sát và lẹm nhẹ vào mép viền tròn xanh lá cây (không có khoảng đệm an toàn phía trên)."*
- **Kỹ thuật xử lý chuẩn 10/10**:
  - Không thể chỉ dịch `y0` lên vì sẽ chạm biên trên của khung hình gốc hoặc làm lệch cằm.
  - Sử dụng **Border Padding (`cv2.copyMakeBorder`)** kết hợp mở rộng kích thước `side`:
    ```python
    side = 1000  # Mở rộng side để lấy khoảng thở tự nhiên
    cx, cy = 534, 570  # Căn tâm dịch nhẹ xuống dưới để đỉnh tóc có khoảng đệm rộng
    pad = side // 2
    padded = cv2.copyMakeBorder(frame, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
    
    cx_pad, cy_pad = cx + pad, cy + pad
    x0 = cx_pad - side // 2
    y0 = cy_pad - side // 2
    crop = padded[y0:y0+side, x0:x0+side]
    sq = cv2.resize(crop, (512, 512), interpolation=cv2.INTER_LANCZOS4)
    ```
  - **Kết quả nghiệm thu qua Antigravity Headless**:
    * Đỉnh đầu cách viền xanh $\approx 30\text{px}$ (Headroom tỷ lệ vàng).
    * Cằm cách đáy viền an toàn, trọn vẹn ngũ quan, kính mắt, nụ cười rạng rỡ.
    * Đạt điểm tuyệt đối 10/10 trước khi nạp lên máy thật.

---

## 3. Cạm Bẫy TypeError Khi Cập Nhật Registry `protected_folders`
- **Triệu chứng lỗi**:
  - Khi ghi danh sách thư mục được bảo vệ vào `manual_avatar_protected_folders.json` hoặc `manual_hashtag_protected_folders.json`:
    ```python
    d['protected_folders'] = sorted(list(protected))
    ```
  - Bị crash: `TypeError: '<' not supported between instances of 'str' and 'int'`.
- **Nguyên nhân**:
  - File JSON qua nhiều phiên làm việc có thể chứa lẫn lộn cả số nguyên (`298`) và chuỗi ký tự (`"326"`).
- **Quy tắc phòng ngừa (Type Safety Normalization)**:
  - BẮT BUỘC chuẩn hóa toàn bộ về kiểu số nguyên `int` trước khi sort:
    ```python
    protected = set(int(x) for x in d.get('protected_folders', []) if str(x).isdigit())
    protected.add(int(folder_id))
    d['protected_folders'] = sorted(list(protected))
    ```

---

## 4. Quy Trình Chuẩn Hoá 3 Món Trọn Gói (Khi User Nói "Chuẩn hoá luôn kênh đi")
Khi User đưa ra chỉ thị *"Chuẩn hoá luôn kênh đi"*:
1. **Món 1: Avatar**:
   - Trích xuất nhân vật mới chuẩn Persona và tỷ lệ vàng Headroom $\ge 25\text{px}$.
   - Nạp lên máy thật qua `run_avatar_batch_3accs.py`. Soi mắt nghiệm thu `avatar-uploaded-confirmed.png` & `avatar-save-surface-guard.png`.
   - Tạo marker vật lý `.manual_avatar_locked` tại cả 3 đầu kho (`TIKTOK-videonuoinick/<F_out>`, `video goc/<F_src>`, `video goc/<F_out>`).
2. **Món 2: Hashtag & Niche**:
   - Đối soát Niche và Hashtag Pool trong workbook Tik.
   - Tạo marker vật lý `.manual_hashtag_locked` tại 3 đầu kho.
   - Cập nhật cả 2 file `manual_hashtag_protected_folders.json`.
3. **Món 3: Ghim Video (Pin Gate $\ge 1.000$ view)**:
   - Quét lượt xem trên lưới video của profile.
   - Nếu max view $< 1.000$ (ví dụ 339 view): **KHÔNG GHIM**, giữ thứ tự tự nhiên.
   - Nếu có video $\ge 1.000$ view: Ghim 1-3 video view cao nhất lên đầu trang.
