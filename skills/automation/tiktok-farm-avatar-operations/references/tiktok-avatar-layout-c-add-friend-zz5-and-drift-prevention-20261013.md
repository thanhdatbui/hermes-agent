# TikTok Avatar: Layout C, Add-Friend `zz5` False-Positive & App-Drift Prevention

**Incident Date:** 2026-10-13  
**Target:** TikTok Farm (Samsung S7, TikTok v47.0.3+, Machine 21 / `@cao.m.phng7`)

---

## 1. Bản chất Sự cố & Cạm bẫy

### 1.1. False-Positive: Add-Friend Header Icon (`zz5`/`pwb`) vs Top-Left Pencil
- **Hiện tượng**: Trên layout TikTok mới (Avatar nằm góc trên bên phải `[708,300][1080,636]` kèm bong bóng Note "Thì thầm to nhỏ" / "Tám chuyện nào"), icon trên cùng bên trái `[24,96][126,204]` thực chất là **icon "Thêm bạn bè" (Add friends)** có resource-id `com.ss.android.ugc.trill:id/zz5` hoặc `pwb`.
- **Cạm bẫy code**: `TopLeftPencilLayout.matches(tree)` kiểm tra bounds `left 10..45, top 70..130` mà không loại trừ `zz5`/`pwb`, dẫn đến nhận diện nhầm icon Add-Friend thành bút chì sửa hồ sơ.
- **Hậu quả**: Runner tap trượt, sau đó tap thẳng vào avatar thì bị vướng vào pop-up Story 24h ("Hiển thị với follower trong 24 giờ"), không có menu "Tải ảnh lên" ➔ Crash `AVATAR_UPLOAD_MENU_MISSING`.
- **Fix đã áp dụng**:
  ```python
  # Trong TopLeftPencilLayout.matches():
  if tree.has_text("sửa hồ sơ", "chỉnh sửa hồ sơ", "edit profile") or tree.has_rid("zz5", "pwb"):
      return False
  ```

### 1.3. Cạm bẫy Bounds Cứng `n.l >= 10` Khiến Top-Left Pencil Bị Reject (UNKNOWN_LAYOUT Crash)
- **Hiện tượng**: Khi chạy runner tự động `run_tiktok_upload_avatar.ps1`, log văng:
  `[PROFILE_EDIT] [METRIC] event=unknown_layout_quarantined matched=[]`
  `[AVATAR_EDIT_OPEN_FAILED] ENSURE_AVATAR: Màn Sửa hồ sơ không mở`
- **Nguyên nhân gốc rễ**:
  Trong `TopLeftPencilLayout._find_pencil_candidates()`:
  ```python
  if 10 <= n.l <= 45 and 70 <= n.t <= 130:
  ```
  Trên thiết bị Samsung S7 (TikTok v47.0.3+), XML dump thực tế của icon bút chì / navigation header ở góc trên bên trái có bounds là `[0,75][168,243]`.
  Do `left == 0 < 10`, điều kiện `10 <= n.l` bị **FAIL**!
  Kết quả: `TopLeftPencilLayout` từ chối nhận diện, `ClassicTextLayout` không tìm thấy text, dẫn đến `resolve()` trả về `UNKNOWN_LAYOUT` và crash fail-closed.
- **Quy tắc sửa chuẩn**: Bounds của icon góc trái bắt buộc nới lỏng `0 <= n.l <= 45` và `50 <= n.w <= 170`, `50 <= n.h <= 170` để nhận diện trúng bounds `[0,75][168,243]`.

### 1.4. Xung Đột Device Lock Khi Batch Feed-Session Đang Chạy Nền
- **Hiện tượng**: Lệnh ad-hoc `with_device_lock.py --machine 33` bị timeout 30s (`Exit 124`).
- **Nguyên nhân**: Tiến trình nuôi nick đa máy nền (`run_tiktok.py --mode multi-machine-feed-session --machines 1..80`, ví dụ PID `29492`) đã đặt sẵn lock đặt chỗ (`status: queued_v2`, `ttl_seconds: 3600`).
- **Xử lý**: Kiểm tra `psutil` xem có tiến trình con nào đang thực sự gửi lệnh ADB tới serial máy hay không (`target_serial in cmd`). Nếu máy chỉ đang nằm trong hàng đợi reservation nhưng cần can thiệp avatar khẩn cấp, phải đợi đợt feed của máy đó nhả hoặc dùng script chuyên dụng Layout C với lease ngắn hạn.

### 1.2. App-Drift & Ảo giác Screencap (Samsung Browser / Google Trap)
- **Sự cố**: Trong quá trình test deep link hoặc back nhầm, thiết bị bị văng ra trình duyệt Samsung Internet (`com.sec.android.app.sbrowser`) mở trang Google xoay ngang (`1920x1080`) có nút "Đánh dấu" (hình quyển sách).
- **Hậu quả nghiêm trọng**: Coordinator không kiểm tra `mCurrentFocus`, screencap nhầm màn hình Google, xoay ngang và tự "mớm" vision rằng đã thấy avatar Ông Chú Tâm Lý ➔ Gửi ảnh sách "Đánh dấu" khiến User phẫn nộ chất vấn báo cáo láo.
- **Quy tắc ngăn chặn**:
  1. Luôn assert `dumpsys window windows | grep mCurrentFocus` phải là `com.ss.android.ugc.trill`.
  2. Dùng WinRT OCR (`ocr_boxes.ps1`) quét token trước khi tin Vision model. Token của TikTok Profile bắt buộc có: `@<username>`, `"Đã follow"`, `"Follower"`, `"Hồ sơ"`.
  3. Ảnh điện thoại S7 bắt buộc là chiều dọc (`1080x1920`). Ảnh ngang (`1920x1080`) là cờ đỏ báo động lệch app.

---

## 2. Quy trình Thực thi Chuẩn O(1) Cho Layout C (Có Bong Bóng Note)

1. **Vào màn hình Sửa hồ sơ**:
   - Tap icon Sửa hồ sơ tại `(75, 150)`.
   - Kiểm tra OCR xác nhận màn hình "Sửa hồ sơ" (`Sta h6 sd`), có mục "Thay đổi ảnh".

2. **Mở Photo Picker**:
   - Tap "Thay đổi ảnh" tại `(540, 580)`.
   - Tap "Tải ảnh lên" tại `(250, 1637)` (hoặc `300, 1637`).

3. **Đẩy ảnh mới & Refresh Picker**:
   - Push ảnh vào `/sdcard/DCIM/Camera/IMG_<timestamp>.jpg` và `/sdcard/Pictures/`.
   - Chạy `am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/DCIM/Camera/IMG_<timestamp>.jpg`.

4. **Chọn ảnh (Tránh Checkbox Trap)**:
   - Tap checkbox góc trên phải của ô ảnh đầu tiên tại `(225, 255)` hoặc `(225, 290)`.
   - Tap nút "Tiếp" tại `(912, 1844)`.

5. **Màn hình Cắt (Crop) & Lưu**:
   - Bounds nút Lưu: `[552,1728][1032,1860]`. Nút Hủy: `[48,1728][528,1860]`.
   - Tap nút "Lưu" tại `(792, 1794)`.
   - Chờ 6-8 giây cho TikTok upload hoàn tất.

6. **Verify Profile**:
   - Nhấn Back (`input keyevent 4`) hoặc tap tab "Hồ sơ" `(972, 1864)`.
   - Chụp ảnh, kiểm tra `mCurrentFocus` là TikTok, chạy WinRT OCR đối soát `@<username>`, và crop cận cảnh avatar `[300:636, 708:1080]` để nghiệm thu thị giác theo Gate 6.
