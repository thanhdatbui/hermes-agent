# Tự Động Hóa Chuẩn Hóa Avatar Toàn Farm & Cạm Bẫy Bóc Tách Khuôn Mặt (2026-10-20)

## 1. Bối Cảnh Sự Cố & Dấu Hiệu Nhận Biết
Khi vận hành Phone Farm quy mô lớn (~640 folder video gốc, 1.280 tài khoản), có khoảng 15–20% folder bị tình trạng Avatar rác hoặc lỗi:
- File `avatar.jpg` trên đĩa là ảnh đồ vật vô tri (ống lồng xe máy, thụt giảm xóc, bàn ghế, đá granite).
- File `avatar.jpg` là tranh chữ 2D/3D cào từ YouTube ("CÂU CHUYỆN SINH VIÊN", logo kênh cũ).
- File `avatar.jpg` là poster phim dính chữ phụ đề, màng che logo app.

Khi dùng thuật toán thị giác máy tính cổ điển (Haar Cascade / OpenCV) tự động quét và bóc mặt từ video gốc `.mp4`, nếu không có bộ lọc ngữ nghĩa (Semantic Filtering), hệ thống sẽ tạo ra những avatar quái đản và khó hiểu.

---

## 2. 5 Cạm Bẫy Chết Người Của Bộ Bóc Tách Khuôn Mặt Cơ Học (Haar Cascade Pitfalls)

1. **Bẫy Bàn Tay Cầm Điện Thoại (Hand-as-Face Trap)**:
   - Haar Cascade nhận nhầm các nếp gấp ngón tay, bàn tay cầm điện thoại thành khuôn mặt.
   - Hậu quả: Avatar bị crop lệch xuống ngực/bụng, tâm vòng tròn khoanh trúng chiếc smartphone và dính nguyên logo CapCut hoặc phụ đề chữ.

2. **Bẫy Filter Troll Biến Dạng Mặt (Troll Filter Trap)**:
   - Creator TikTok thường quay clip bắt trend dùng filter kéo biến dạng mặt (môi sưng to tướng, mắt xệ, mặt dị dạng hài hước).
   - Thuật toán cơ học vẫn nhận diện đó là "mặt người" và bóc ra làm avatar, tạo hình ảnh phản cảm, mất uy tín của kênh.

3. **Bẫy Sticker Hoạt Hình 2D (Sticker/Overlay Trap)**:
   - Video TikTok hay chèn sticker cute (má hồng tròn, tai thỏ, icon hoạt hình).
   - Thuật toán bắt nhầm hai má hồng của sticker hoạt hình là khuôn mặt, crop ra ảnh nửa mặt người nửa sticker dị hợm.

4. **Bẫy Thiết Bị Thu Âm Podcast / Gameshow TV (Studio Headset & Mic Collision)**:
   - Clip dạng Podcast, kể chuyện thu âm: Người nói đeo tai nghe trùm đầu cỡ lớn (studio headphone), trước mặt có màng lọc âm (pop filter) và cần micro che hết cằm và miệng.
   - Clip trích từ gameshow TV (Running Man, Forest Studio): Có chữ tiêu đề, logo nhà đài đè kín lên mặt nhân vật.

5. **Bẫy Người Ở Hậu Cảnh Xa (Far Background Pixelation Trap)**:
   - Video quay cảnh toàn (showroom xe máy, xưởng sửa chữa, góc phố): Nhân viên đứng xa ở hậu cảnh.
   - Thuật toán zoom cận vào mặt nhỏ li ti khiến ảnh avatar bị vỡ hạt, nhiễu mờ, góc mặt đờ đẫn gượng gạo.

---

## 3. Quy Chuẩn Bộ Lọc Đa Tầng (Multi-Tier Semantic Face Filter Pipeline)

Để đảm bảo 100% avatar bóc tách ra là Creator người thật sắc nét, chuẩn TikTok, bắt buộc phải áp dụng bộ lọc 4 lớp:

### Lớp 1: Ngưỡng Hình Học & Độ Nét Nghiêm Ngặt
- **Kích thước khuôn mặt tối thiểu**: $w, h \ge 140\text{px}$ – $160\text{px}$ trên khung hình dọc $576\times 1024$ hoặc $1080\times 1920$ (loại bỏ hoàn toàn người ở hậu cảnh xa).
- **Độ sắc nét ROI (Laplacian Variance)**: $\ge 90.0$ – $120.0$ trên vùng khuôn mặt (loại bỏ ảnh mờ, chuyển động nhanh bị nhòe).
- **Vùng đệm biên an toàn (Safety Margins)**: Bắt buộc $x \ge 40\text{px}$ và $x + w \le \text{frame\_width} - 40\text{px}$, $y \ge 40\text{px}$ để đảm bảo đầu không bị mép khung hình cắt cụt.

### Lớp 2: Lọc Ngữ Nghĩa Niche Kênh
- **Niche ưu tiên Creator cá nhân**: `sinhvien`, `gaixinh`, `lamdep`, `chamsocsuckhoe`, `hoctap`, `amthuc`.
- **Niche cần thận trọng**:
  * `cauchuyen` / `phim`: Tránh lấy các frame podcast có mic/tai nghe che mặt; ưu tiên frame diễn viên diễn xuất tự nhiên.
  * `xemay` / `noithat` / `congnghe`: Tránh zoom mặt nhân viên ở xa; nếu không có creator cận cảnh thì dùng logo/chi tiết sản phẩm chụp góc nghệ thuật, không cố ép zoom vỡ nét.

### Lớp 3: Cắt Cúp Tỷ Lệ Vàng Avatar (Golden Ratio Square Crop)
```python
def crop_creator_face(img, rect, scale=2.3, headroom=0.35):
    x, y, w, h = rect
    img_h, img_w = img.shape[:2]
    crop_dim = int(max(w, h) * scale)
    crop_dim = min(crop_dim, img_h, img_w)
    cx = x + w // 2
    cy = y + int(h * 0.45)
    x1 = max(0, min(img_w - crop_dim, cx - crop_dim // 2))
    y1 = max(0, min(img_h - crop_dim, y - int(crop_dim * headroom)))
    crop = img[y1:y1 + crop_dim, x1:x1 + crop_dim]
    return cv2.resize(crop, (512, 512), interpolation=cv2.INTER_LANCZOS4)
```

### Lớp 4: Kiểm Định Thị Giác (Visual Verification & Contact Sheet)
- BẮT BUỘC tạo ảnh so sánh Đối soát: Cột trái ảnh cũ (OLD lỗi) vs Cột phải ảnh mới bóc tách (NEW chuẩn có viền tròn xanh mô phỏng viền TikTok).
- BẮT BUỘC dùng Vision LLM mở ảnh soi mắt xác nhận:
  1. Mặt người thật 100%, nét mặt sáng rõ, thần thái tự nhiên.
  2. Không có tai nghe/mic che kín miệng.
  3. Không có filter troll méo mặt.
  4. Không có chữ text banner hay sticker hoạt hình đè lên mặt.

---

## 4. Kỷ Luật Vận Hành Khóa Cứng (Post-Healing Lockdown Protocol)
Sau khi User duyệt phương án avatar:
1. Ghi đè `avatar.jpg` vào cả 2 kho: kho video gốc (`D:/video goc/<F_src>/`) và kho video render (`D:/TIKTOK-videonuoinick/<F_vid>/`).
2. Cắm cờ vật lý `.manual_avatar_locked` tại cả 2 thư mục.
3. Đăng ký vào `D:/Taadaa/data/manual_avatar_protected_folders.json`.
4. Cập nhật `avatar_replace_queue` trong `tiktok_tracker.db` sang `PENDING` và cột `Avatar = PENDING` trên file Excel tương ứng để Watchdog ca tối (`post_evening_avatar_watchdog.py`) tự động nạp lên máy thật.
