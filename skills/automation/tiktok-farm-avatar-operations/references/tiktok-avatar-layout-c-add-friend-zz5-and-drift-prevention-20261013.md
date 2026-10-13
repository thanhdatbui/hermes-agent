# TikTok Avatar: Layout C, Add-Friend `zz5` False-Positive & App-Drift Prevention

**Incident Date:** 2026-10-13  
**Target:** TikTok Farm (Samsung S7, TikTok v47.0.3+, Machine 21 / `@cao.m.phng7`)

---

## 1. Bản chất Sự cố & Cạm bẫy

### 1.1. Top-Left Pencil Header `(75, 150)` & Cấm Tự Chế Bánh Xe Thay Thế Script Canonical
- **Sự thật đã được xác nhận**: Trên layout TikTok mới (Layout C: avatar nằm bên phải kèm bong bóng Note), icon ở góc trên cùng bên trái tại tọa độ `(75, 150)` **CHÍNH LÀ CÂY BÚT CHÌ SỬA HỒ SƠ** (mở trực tiếp `ProfileEditActivity`).
- **Kỷ luật Canonical Tooling & Zero Re-invent**: Script upload avatar canonical của User (ví dụ `run_tiktok_upload_avatar.ps1` hoặc `do_upload_avatar_m71.py`) **ĐÃ ĐƯỢC CHUẨN HÓA TRONG HỆ THỐNG**.
- **Design Spec Zero Re-invent & Fix-at-Source (Thiết kế bởi Claude Code CLI)**: Chi tiết xem tại [references/zero-reinvent-canonical-tooling-and-fix-at-source-protocol-20261013.md](zero-reinvent-canonical-tooling-and-fix-at-source-protocol-20261013.md). Khi runner vấp màn hình lạ/bounds lệch, **BẮT BUỘC sửa/handle trực tiếp vào core codebase của chính runner đó** (`top_left_pencil.py`), cấm tuyệt đối tự chế lại script tap tay ngoài lề!
- **Sai lầm chết người của Agent**:
  - Tự suy diễn sai rằng `(75, 150)` là icon Add-Friend (`zz5`/`pwb`), từ đó tự ý viết patch phá vỡ layout detector và tự viết script tap tay ngoài lề.
  - User chất vấn gay gắt: *"thấy cây bút góc trái trên cùng k? ... t nhớ có script upload ava t đã fix chỉ bấm vào cây bút r mà... có chạy script upload ava k hay lại đi ngồi viết lại script"*.
- **Quy tắc bất di bất dịch**:
  1. CẤM TUYỆT ĐỐI tự ngồi viết script tap tay ADB mới khi User đã có script canonical `do_upload_avatar_m71.py` đã kiểm chứng.
  2. Khi cần đổi avatar cho bất kỳ máy nào, CHỈ ĐƯỢC dùng script canonical `do_upload_avatar_m71.py`, cấu hình đúng `MACHINE_ID`, `SERIAL`, và `local_avatar`.

### 1.2. TikTok Note Trap: Bong Bóng "Thì Thầm To Nhỏ" / "Bạn Có Chuyện Vui?" & Ảo Giác Avatar
- **Hiện tượng**: Tính năng Ghi chú (Note) trên TikTok profile tạo ra một bong bóng thoại màu trắng nổi bật phía trên avatar mang nội dung *"Thì thầm to nhỏ"*, *"Tám chuyện nào"* hoặc *"Bạn có chuyện vui?"*.
- **Cạm bẫy ảo giác thị giác (Vision Hallucination)**:
  - Khi soi mắt toàn màn hình Profile, Model rất dễ bị phân tâm bởi bong bóng màu trắng này và nhận định sai lầm rằng avatar "vẫn là người phụ nữ cũ" hoặc "bị lỗi", trong khi thực tế vòng tròn avatar bên dưới đã hiển thị đúng 100% nhân vật của folder (ví dụ: nhân vật hoạt hình nam tóc cam pompadour, kính hồng của folder 163).
  - Hậu quả: Agent tưởng nhầm avatar chưa đổi, loay hoay thử lại liên tục hàng giờ và làm phiền User dù avatar thực tế đã đúng từ đầu!
- **Phương pháp kiểm chứng chuẩn xác**:
  1. Crop riêng vòng tròn avatar loại bỏ bong bóng Note ở trên.
  2. Đối chiếu trực tiếp với màn hình **Sửa hồ sơ** (`ProfileEditActivity`) hoặc màn hình **Chuyển đổi tài khoản (Account Switcher)** — đây là 2 nơi avatar hiển thị nguyên bản, sạch 100% không bị bong bóng Note che khuất.

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
