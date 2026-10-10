# TikTok Channel Rename Via make_tiktok_name & Top-Left Pencil S7 Variation (2026-10-10)

## 1. Bối cảnh & Chỉ thị của Operator
Khi Operator gửi ảnh màn hình kênh TikTok và ra lệnh:
- *"Đổi ava kênh này"*
- *"Làm đi. Đổi cả tên kênh"*
- *"Theo hàm đặt tên đã có trong script"*

Đây là lệnh thực thi đổi đồng thời cả Avatar lẫn Tên hiển thị (Display Name) của tài khoản mà không được hỏi lại hay tự nghĩ ra tên bừa bãi.

---

## 2. Nguồn SSOT cho Hàm Đặt Tên (`make_tiktok_name`)
Hàm đặt tên chuẩn của farm nằm tại:
`D:/Taadaa/Tiktok_Reg/social_reg_v1.py` -> `make_tiktok_name(email)`

### Phân bổ phong cách đặt tên tự nhiên:
- **Họ + Đệm + Tên (25%):** *Trần Minh Đạt, Nguyễn Hoài An, Huỳnh Quang Lan, Phạm Hải Hương*
- **Họ + Tên (25%):** *Lê Linh, Vũ Nam, Ngô Long, Đoàn Phong*
- **Đệm + Tên (20%):** *Ngọc Linh, Thanh Thảo, Khánh Vy, Gia Ngân, Như Tâm*
- **Tên + Biệt danh đời thường (20%):** *Linh Bông, Đạt Còi, Vy Miu, An Kem* (kết hợp `_TEN_LIST` + `_NICK_SUFFIX`)
- **Tên lặp / Duo dễ thương (10%):** *An An, Gạo Gạo, Miu Miu, Vy Vy, Linh Linh* (`_CUTE_DUO`)

### Cách gọi:
```python
import sys
sys.path.insert(0, r"D:\Taadaa\Tiktok_Reg")
from social_reg_v1 import make_tiktok_name

new_name = make_tiktok_name(target_email)
```

---

## 3. Cạm bẫy Hardcode Bộ Đếm Ký Tự N/30 trong State Machine OCR
### Hiện tượng:
Các script mẫu cũ như `do_rename_m20.py` hardcode kiểm tra `11/30` (do tên Phương Thảo có 11 ký tự), hoặc `do_rename_m8.py` hardcode `6/30` (do tên Hải Sa có 6 ký tự).
Nếu tên sinh mới có độ dài khác (ví dụ: `Vy Vy` có 5 ký tự, `Phạm Hải Hương` có 14 ký tự), script cũ sẽ ném `Abort: OCR khong xac nhan o nhap = ... (11/30) -> Huy, KHONG Luu`.

### Quy tắc chuẩn hóa động:
```python
expected_len = len(new_name)
count_match = re.search(r"(\d{1,2})\s*/\s*30", box)
ok_count = (
    count_match is not None
    and abs(int(count_match.group(1)) - expected_len) <= 1
) or f"{expected_len}/30" in box
```

---

## 4. Biến thể UI Profile S7: Top-Left Pencil Icon
Trên nhiều dòng Samsung S7 (Android 8.0), màn hình Profile không có nút text "Sửa hồ sơ" ở giữa:
- **Đường dẫn vào:** Tap icon cây bút chì ở góc trên bên trái header `(75, 150)` (bounds `[24, 96][126, 204]`).
- **Màn Sửa hồ sơ:**
  - Avatar tròn ở phía trên: Tap "Thay đổi ảnh" `(538, 580)` để bung bottom sheet ("Tải ảnh lên").
  - Dòng "Tên" ở hàng đầu tiên: Tap dòng Tên `(600, 752)` để vào màn sửa Display Name.

---

## 5. Cạm bẫy Screencap Rác Đẩy Trôi Tile trong Photo Picker
- Khi chụp screencap qua `screencap -p /sdcard/...` lưu vào `/sdcard/Pictures/` hoặc `/sdcard/Screenshots/`, MediaStore có thể index các ảnh chụp màn hình này thành ảnh gần đây.
- Khi picker TikTok mở ra, các ảnh chụp màn hình vừa chụp sẽ xuất hiện ở Hàng 1 (Row 1), đẩy file `avatar.jpg` vừa push xuống Hàng 2 (Row 2).
- **Quy tắc:** Lưu screencap tạm vào `/sdcard/` root (ví dụ `/sdcard/temp.png`) thay vì `/sdcard/Pictures/` hoặc `/sdcard/DCIM/` để không làm ô nhiễm thư viện ảnh của Photo Picker.

---

## 6. Kỷ luật Đồng bộ Thiết bị & Device Lock
- Khi máy đang nằm trong hàng đợi ca nuôi (`status == 'queued_v2'`), bọc lệnh can thiệp bằng `with_device_lock.py`:
  ```bash
  python D:/Taadaa/tools/with_device_lock.py --machine <N> --timeout 300 -- python D:/Taadaa/tools/do_rename_m<N>.py
  ```
- Luôn chạy nền event-driven (`background=True, notify_on_complete=True, timeout=300`) đối với các tác vụ thao tác UI thiết bị kéo dài >60s.
