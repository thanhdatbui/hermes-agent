# TikTok Avatar: Canonical Production Flow, Account-Switch Verification & Face Extraction from Posted Videos (2026-10-13)

## 1. Cạm Bẫy Đổi Nhầm Account (Layout C Switcher Drift)

### Hiện tượng & Hậu quả
- Trên một thiết bị farm (ví dụ Samsung S7) chứa 8 tài khoản TikTok vật lý trong Switcher.
- Nếu mở app TikTok và thực hiện đổi avatar thủ công mà **không kiểm tra trước handle `@<username>`** đang active trên màn hình:
  - App có thể đang mở ở một tài khoản khác (ví dụ `@mimiiepekgq` hoặc `@kieuoanh.beauty`).
  - Thao tác tap "Sửa hồ sơ" -> chọn ảnh -> Lưu sẽ đổi avatar của **tài khoản đang mở**, trong khi tài khoản mục tiêu (ví dụ `@kieu.lam966`) trên máy chủ TikTok vẫn giữ nguyên avatar cũ.
  - Coordinator kiểm tra ảnh crop profile thấy có ảnh mới tưởng thành công, nhưng User mở kênh trên TikTok thì avatar kênh mục tiêu vẫn là avatar rác/logo cũ.

### Invariant Bắt Buộc
- **CẤM ĐỔI AVATAR MÙ:** Trước khi vào màn hình "Sửa hồ sơ", BẮT BUỘC phải đọc UI XML hoặc chạy WinRT OCR đối soát: text trên màn hình PHẢI chứa đúng `@<target_username>`.
- **Nhận diện đúng Anchor trên Layout C:**
  - Trên Layout C (Avatar góc trên bên phải `[708,300][1080,636]`), icon góc trên bên trái `[24,96][126,204]` là icon Thêm bạn bè (`zz5`).
  - Nút mở Account Switcher thực chất là Button hiển thị tên hiển thị / handle tại `[36, 280][567, 364]` (`resource-id: com.ss.android.ugc.trill:id/t7l`). Tap vào nút này để mở Switcher sheet chọn đúng nick mục tiêu.

---

## 2. Căn Nguyên "Avatar Logo GDĐT" & Trích Xuất Nhân Vật Đúng Kênh

### Căn nguyên Avatar Rác
- Các thư mục cũ trước đây từng chứa slide bài giảng ôn thi THPT, góc trên slide có chèn huy hiệu đỏ - vàng "Bộ Giáo dục và Đào tạo".
- Tool trích xuất frame tự động quét trúng huy hiệu đó và nhận diện nhầm thành avatar, dẫn đến kênh bị dính logo GDĐT.
- Khi người dùng yêu cầu đổi avatar, nếu Agent trích xuất người tùy tiện không khớp với nội dung thực tế các video đã đăng (ví dụ kênh video công sở văn phòng nhưng lấy nhầm ảnh selfie đời thường áo thun hồng hoặc anime), người dùng sẽ từ chối duyệt ("Vẫn éo có ava nào đúng").

### Quy Trình Chuẩn Bị Avatar Chuẩn Xác
1. **Đối soát lưới video trên kênh (Channel Video Grid):**
   - Đọc thumbnails của các video đã đăng trên kênh (ví dụ: bạn nữ mặc áo blazer, đeo kính cận, ngồi bàn làm việc văn phòng hai màn hình).
2. **Trích xuất từ video nguồn tương ứng:**
   - Trích xuất frame chất lượng cao từ các video chính chủ (`1.mp4`, `2.mp4`, `3.mp4`).
   - Dùng Haar cascade / OpenCV dò khuôn mặt, crop vuông `512x512` sao cho khuôn mặt nằm ở trung tâm (chiếm 40–50% diện tích hình tròn TikTok, $cy \approx 0.42 \times S$).
3. **Đồng bộ SSOT vào cả 4 thư mục:**
   - Copy `avatar.jpg` vào cả `D:/video goc/<F_src>`, `D:/video goc/<F_out>`, `D:/TIKTOK-videonuoinick/<F_src>`, `D:/TIKTOK-videonuoinick/<F_out>`.
4. **Khóa bảo vệ Registry:**
   - Đảm bảo folder được ghi nhận vào `D:/Taadaa/data/manual_avatar_protected_folders.json`.

---

## 3. Quy Trình Thực Thi Chuẩn Production (`run_workflow_cli --avatar-smoke`)

Thay vì tự viết script ADB can thiệp thô dễ phát sinh lỗi chuyển nick và nghẽn MediaStore, hãy sử dụng engine chuẩn hóa của hệ thống:

### Bước 1: Kích hoạt trạng thái PENDING trên sổ sách
```python
# 1. Cập nhật cột Avatar trong Tik<Slot>.xlsx thành PENDING (cột 13)
import openpyxl
wb = openpyxl.load_workbook(r"D:\OneDrive\TaadaaData\kibe\Tik4.xlsx")
ws = wb.active
for r in ws.iter_rows():
    if r[0].value == <machine_num>:
        r[12].value = "PENDING"
wb.save(r"D:\OneDrive\TaadaaData\kibe\Tik4.xlsx")

# 2. Cập nhật SQLite avatar_replace_queue
import sqlite3
conn = sqlite3.connect(r"D:\Taadaa\data\tiktok_tracker.db")
c = conn.cursor()
c.execute("""
    UPDATE avatar_replace_queue 
    SET status='PENDING', video_goc='<F_src>', folder_video='<F_out>', last_error=NULL, updated_at=datetime('now','localtime') 
    WHERE may=<machine_num> AND tik=<slot_num>
""")
conn.commit()
```

### Bước 2: Chạy runner chuẩn qua lệnh CLI được phê duyệt
```bash
echo AVATAR-SMOKE | python D:/Taadaa/Tiktok-video/scripts/run_workflow_cli.py \
  --config D:/CodexRuntime/tiktok-video/config-machine-62.yaml \
  --workflow-workbook D:/OneDrive/TaadaaData/kibe/Tik<Slot>.xlsx \
  --machine <machine_num> \
  --avatar-smoke \
  --force-avatar-upload \
  --force-avatar-machines <machine_num> \
  --verbose
```

### Ưu điểm vượt trội của Runner Production:
- **Tự động chuyển đúng nick:** Kiểm tra `ID TikTok` từ workbook, tự mở Switcher và switch sang đúng nick trước khi vào profile.
- **Tự dọn sạch MediaStore Gallery:** Đảm bảo không bị picker tap nhầm vào ảnh chụp màn hình cũ.
- **Tự động xác nhận upload & dọn dẹp:** Đợi upload xong, kiểm tra avatar mới, thu hồi lock thiết bị và tự động cập nhật atomic workbook (`Avatar = OK`) cùng SQLite (`status = DONE`).

---

## 4. Nghiệm Thu Thực Tế (Strict Gate 6)
- Mở ảnh `D:/CodexRuntime/tiktok-video/runs/run_<serial>_<timestamp>/avatar-uploaded-confirmed.png`.
- Gọi `browser_vision` soi mắt xác nhận:
  1. Tên hiển thị và handle đúng `@<target_username>`.
  2. Avatar tròn hiển thị rõ nét khuôn mặt nhân vật chính chủ mới.
  3. Avatar cũ/logo GDĐT hoàn toàn biến mất 100%.
- Báo cáo kèm đường dẫn ảnh `MEDIA:<path>` cho User.
