# Audit Biệt Danh Rập Khuôn (Stereotyped Nicknames) & Quy Chuẩn Đổi Tên "User Bình Thường"

## 1. Định Nghĩa & Phân Loại Lỗi "Biệt Danh Rập Khuôn" Trên Farm

Khi vận hành đàn tài khoản TikTok số lượng lớn (hàng trăm nick trên nhiều máy/slot), tài khoản thường bị gán tên hiển thị (Display Name / Biệt danh) theo các mẫu rập khuôn từ lúc reg hoặc sync tự động. Điều này làm lộ rõ dấu hiệu tài khoản ảo/bot và dễ bị thuật toán TikTok giảm phân phối.

Ba nhóm lỗi rập khuôn chính thường gặp:
1. **Trùng 100% username hoặc tên mail shop có số (Raw Handle/Email local-part)**:
   - Ví dụ: `lieuhoan03`, `luuhuong2802`, `buithudung2011`, `bronsontruss38`, `thachkieu05`, `votam5319`.
   - Dấu hiệu: Chứa toàn bộ chuỗi username hoặc có 2–4 chữ số ở cuối, không có dấu cách, viết thường toàn bộ.
2. **Cắt cụt bỏ đuôi số nhưng dính liền không dấu cách (Truncated No-Space)**:
   - Ví dụ: `tranngan`, `vophuc7`, `ninhy0510`, `lequynh20`, `phamthy20`, `dinhlan2407`.
   - Dấu hiệu: Tên cụt không có khoảng trắng phân tách họ/tên, hoặc cắt nửa chừng để lại số lẻ.
3. **Tên cụt lủn 1 từ (Bare 1-word name)**:
   - Ví dụ: `Hà`, `Đạt`, `An`, `Linh`.
   - Vi phạm trực tiếp quy chuẩn farm: TikTok display name không bao giờ được để trơ trọi 1 từ.

---

## 2. Tiêu Chuẩn "User Bình Thường" Cho TikTok Farm

Tên người dùng đạt chuẩn "User bình thường" phải đáp ứng các điều kiện:
- **Tối thiểu 2 từ trở lên** (có khoảng trắng phân tách).
- **Có viết hoa đầu từ tự nhiên** và/hoặc có dấu tiếng Việt chuẩn.
- **Không chứa đuôi số rác** (`\d{2,}$`).

### Phân Bổ Tỷ Lệ Danh Tính Tự Nhiên:
- **30% Tên + Biệt danh đời thường / Cute Duo**:
  - Ghép `_TEN_LIST` + `_NICK_SUFFIX`: *Linh Bông, Vy Miu, An Kem, Đạt Còi, Chi Cún, Mai Bơ, Nhi Nấm, Hoàn Bơ, Thảo Nấm, Trâm Bông*.
  - Tên lặp / Duo dễ thương: *Miu Miu, An An, Gạo Gạo, Bé Heo, Út Nhỏ*.
- **70% Tên người thật (Họ + Đệm + Tên / Đệm + Tên)**:
  - *Trần Minh Đạt, Nguyễn Hoài An, Lê Linh, Vũ Nam, Ngọc Linh, Thanh Thảo, Khánh Vy*.

---

## 3. Quy Trình Rà Soát & Triển Khai Đổi Tên Cuốn Chiếu

### A. Rà soát nhanh O(1) từ Workbook Farm:
Đối soát danh sách tài khoản từ `tiktok_stats_farm.xlsx` hoặc `taikhoan_run_safe_combined.xlsx` kết hợp SQLite `tiktok_tracker.db`:
```python
def classify_display_name(username, display_name):
    u = str(username).strip().lower()
    n = str(display_name).strip()
    words = n.split()
    if len(words) < 2:
        return "BARE_ONE_WORD"
    if u == n.lower() or bool(re.search(r"\d{2,}$", n)) or (len(n) > 6 and n.lower() in u):
        return "STEREOTYPED_USERNAME"
    return "NATURAL_USER"
```

### B. Kiểm Tra Workbook `Folder Video` Trước Khi Upload Avatar:

**Bug pattern tái phát**: Cột `Folder Video` (Cột 4) trong `TikN.xlsx` bị ghi sai số folder, khiến tool bốc nhầm `avatar.jpg` từ folder lạc đề:
- Máy 2 (`@lieuhoan03`, Niche Tài chính, VideoGoc=242): bị ghi `Folder Video = 12` (Gym/xăm trổ) → nạp avatar xăm trổ.
- Máy 51 (`@luutuoi02`, Niche Kỷ yếu/Áo dài, VideoGoc=291): bị ghi `Folder Video = 404` (Thú cưng chó lông xù) → nạp avatar chó cưng.

**Triage O(1)**:
```python
import openpyxl
wb = openpyxl.load_workbook("D:/OneDrive/TaadaaData/kibe/Tik4.xlsx")
ws = wb.active
for row in ws.iter_rows():
    may, folder_video, video_goc = row[0].value, row[3].value, row[4].value
    if folder_video != video_goc:  # Nếu Folder Video != Video Goc thì đang sai
        print(f"MAY {may}: Folder={folder_video} nhưng VideoGoc={video_goc} -> sửa Folder thành {video_goc}")
```

**Fix O(1)**: Sửa cột `row[3].value = video_goc` cho các dòng lệch, save lại workbook.

**Invariant**: `Folder Video` PHẢI bằng `Video Goc` (cả hai đều là số folder dưới `D:/TIKTOK-videonuoinick/`). Nếu không bằng → cross-check lịch sử import, xác định folder nào chứa video đúng ngách trước khi sửa.

---

### B. Rào cản TikTok 7-Day Rename Cooldown:
- TikTok áp dụng giới hạn cứng trên máy chủ: **Chỉ được đổi biệt danh 1 lần / 7 ngày**.
- Khi một nick vừa đổi tên xong, màn hình Sửa hồ sơ sẽ khóa nút Lưu và hiển thị thông báo: *"Bạn chỉ có thể thay đổi biệt danh 7 ngày 1 lần. Bạn có thể tiếp tục thay đổi biệt danh sau ngày DD tháng MM, YYYY"*.
- **Chiến lược cuốn chiếu**:
  - Không chạy ồ ạt cùng lúc; lập bảng mapping danh tính mới cho toàn bộ các nick rập khuôn.
  - Tích hợp vào thời điểm máy rảnh giữa các ca nuôi (`multi-machine-feed-session`), tận dụng `operator_device_lock` để thực hiện đổi tên an toàn mà không làm gián đoạn lịch nuôi hay bị đụng tiến trình.
