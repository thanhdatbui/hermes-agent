# TikTok 46.x Avatar Upload Flow & Left-Aligned Profile Switcher (2026-09-02)

## 1. Avatar Upload & UI Layout on TikTok 46.x

### A. Vị trí nút Sửa hồ sơ / Avatar:
1. **Layout tiêu chuẩn có nút bút chì cạnh Username:**
   - Nút bút chì nằm cạnh username header `id/su7` tại `bounds=[777,510][921,594]` (center `849, 552`) hoặc `[799,510][943,594]` (center `871, 552`).
2. **Layout vòng tròn Avatar (Direct Tap):**
   - Vòng tròn Avatar `id/bm2` hoặc `id/blk` nằm tại `[708,246][1080,582]` (center `850, 400`).
   - Tap vào vòng tròn Avatar sẽ mở Bottom Sheet:
     - "Chụp ảnh" `[48,1475][1032,1535]`
     - "Chọn từ Thư viện" `[48,1632][1032,1692]` (center `540, 1662`).
3. **Bẫy Deep-Link `snssdk1233://profile/edit` trên tài khoản phụ:**
   - Khi mở Sửa hồ sơ bằng deep-link trên tài khoản không phải tài khoản đầu tiên tạo trên máy, TikTok sẽ hiển thị popup chặn: *"Hoạt động không có sẵn. Để tiếp tục tham gia vào các hoạt động, hãy chuyển sang tài khoản ban đầu mà bạn đã dùng trên thiết bị này."*
   - **Quy tắc:** Bắt buộc vào Sửa hồ sơ qua UI tap trên màn hình Hồ sơ, KHÔNG dùng intent deep-link.

### B. Bẫy cuộn trang sau khi Scan Video Grid (`ACCOUNT_READY`):
- Khi state `ACCOUNT_READY` chạy scan lưới video để đếm baseline video, trang Profile bị cuộn lửng xuống dưới khiến các nút trên header/avatar bị trôi khỏi màn hình.
- **Fix bắt buộc:** Khi vào state `ENSURE_AVATAR`, luôn thực hiện 2 lần vuốt xuống đỉnh trang:
  `input swipe 540 400 540 1500 300` trước khi tìm selector nút Sửa hồ sơ / Avatar.

### C. Luồng chọn ảnh và Lưu:
1. **Photo Picker Tile:**
   - Tile ảnh đầu tiên nằm tại `bounds=[0,228][274,502]` (center `137, 355`).
   - Nút "Tiếp (1)" nằm tại `[780,1788][1044,1896]` (center `912, 1842` hoặc `924, 1842`).
2. **Crop Screen (Cắt ảnh):**
   - Checkbox "Đăng ảnh này lên Nhật ký" nằm tại `[48,1554][120,1626]` (center `84, 1590`) -> Bắt buộc tap để bỏ tích (uncheck) tránh spam story nhật ký.
   - Nút "Lưu" hoặc "Lưu và đăng" nằm tại `[552,1728][1032,1860]` (center `792, 1794`) hoặc `[96,1698][984,1830]` (center `540, 1764`).

---

## 2. Left-Aligned Profile Layout & Switcher Anchor

- Trên giao diện TikTok 46.x dạng Left-Aligned (ví dụ Máy 4, Máy 25):
  - Tên hiển thị `id/sv6` / `id/su7` nằm lệch góc trên bên trái: `[36, 249][223, 330]` (center `130, 290` hoặc `148, 322`).
  - Tap vào tọa độ này sẽ mở Bottom Sheet "Chuyển đổi tài khoản" (`is_switcher_open`).
- **Hook `coordinate_fallback` trong Consumer `TikTokAdapter`:**
  - `TikTokAdapter` phải implement hook `coordinate_fallback(self, action=None)` trả về `(540, 552)` hoặc `(140, 300)` khi `action == "switcher"` để khi core `find_switcher_anchor` gặp anchor bị ẩn hoặc mơ hồ do thẻ onboarding, adapter sẽ fallback mở switcher chuẩn xác, tránh lỗi `SWITCHER_ANCHOR_AMBIGUOUS` hay `SWITCHER_NOT_CONFIRMED`.

---

## 3. Windows PowerShell & Python Venv Pitfalls

1. **PYTHONPATH Isolation khi gọi standalone python venv:**
   - Khi chạy script bằng `D:/Taadaa/python-envs/.../Scripts/python.exe`, nếu môi trường shell có `PYTHONPATH` trỏ tới venv khác (như hermes-agent venv), C-extensions của thư viện như `PIL` sẽ bị import collision (`ImportError: cannot import name '_imaging' from 'PIL'`).
   - **Cách gọi chuẩn:** Luôn bọc `env -u PYTHONPATH <python.exe> <script.py>`.
2. **Batch MaxParallel Parameter Range:**
   - `run_tiktok_upload_batch.ps1` cần được set `[ValidateRange(1, 40)]` để đáp ứng yêu cầu chạy tối đa 40 worker song song của farm.
