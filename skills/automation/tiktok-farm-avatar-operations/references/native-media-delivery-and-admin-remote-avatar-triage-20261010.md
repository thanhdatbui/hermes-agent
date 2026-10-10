# Native Media Delivery & Admin Remote Avatar Triage (2026-10-10)

## 1. Kỷ luật Gửi Ảnh Native MEDIA: (Tránh Lỗi Gửi Link Văn Bản & Méo Hiển Thị)

### Hiện tượng & Phản ứng của Operator
- Khi Operator yêu cầu chuẩn hóa avatar cho tài khoản (`@holinh1003`), Coordinator tạo ảnh composite đối chiếu 3 cột ngang (1280x560) lưu tại `C:/Users/Kibe/avatar_investigation/avatar_comparison_holinh1003.jpg`.
- Khi gửi thẻ `MEDIA:C:/Users/Kibe/avatar_investigation/avatar_comparison_holinh1003.jpg`, trên giao diện Telegram trên điện thoại của Operator, ảnh bị gửi dưới dạng link đường dẫn / tài liệu văn bản hoặc hiển thị méo mó, chữ bị co cụm vỡ nét.
- Operator chấn chỉnh gay gắt:
  > *"Gửi ảnh lỗi r đm cứ gửi lỗi hoài"*
  > *"R ok. Nãy mày gửi link đường dẫn chứ k phải ảnh. H thì ok r"*

### Nguyên nhân Kỹ thuật
1. **Tỷ lệ ảnh panorama bất thường:** Khung hình 1280x560 có tỷ lệ quá dẹt. Khi gửi qua Telegram Bot API, tùy theo kích thước và định dạng stream, adapter có thể chuyển sang gửi dạng document hoặc hiển thị co lại thành một dải hẹp khó đọc trên mobile.
2. **Kích thước chuẩn của Avatar:** Avatar TikTok là hình vuông 1:1 (chuẩn 512x512). Người dùng cần nhìn thấy trực tiếp khuôn mặt chân dung ở kích thước hiển thị native chuẩn của ứng dụng chat.

### Quy tắc Bắt buộc (Invariant)
- **Ưu tiên gửi trực tiếp file ảnh vuông 512x512:** Luôn gửi trực tiếp file avatar chuẩn hóa:
  ```text
  MEDIA:D:/TIKTOK-videonuoinick/<Folder Video>/avatar.jpg
  ```
- **Quy chuẩn thẻ MEDIA:**
  - Nằm ở một dòng riêng biệt tuyệt đối, không thụt đầu dòng.
  - Tuyệt đối CẤM bọc trong code block (```` ``` ````).
  - Dùng dấu gạch xuôi `/` cho đường dẫn file (ngay cả trên Windows).
  - Soi mắt kiểm tra trước qua Vision API (`ag/gemini-2.5-flash` hoặc `gemini-3.7-flash` stream False) để xác nhận khuôn mặt rõ nét, đủ ánh sáng, không dính sub hay viền đen.

---

## 2. Tham số `ForceAvatarMachineList` trên PowerShell Runner

### Hiện tượng Lỗi
Khi gọi runner up avatar qua SSH hoặc PowerShell:
```powershell
ssh admin-farm "powershell -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 -Tik 2 -MaxParallel 1 -ForceAvatarMachineList '226'"
```
Runner văng lỗi:
```text
Danh sách máy force avatar không hợp lệ: '226'
At D:\Taadaa\Tiktok-video\run_tiktok_upload_batch.ps1:152 char:13
+             throw "Danh sách máy force avatar không hợp lệ: $ForceAva ...
```

### Nguyên nhân
- Trong `run_tiktok_upload_batch.ps1`, tham số được kiểm tra qua regex:
  ```powershell
  if ($value -notmatch '^\d+$' -or [int]$value -lt 1) {
      throw "Danh sách máy force avatar không hợp lệ: $ForceAvatarMachineList"
  }
  ```
- Việc bọc chuỗi nháy lồng nhau khiến giá trị của biến `$ForceAvatarMachineList` chứa ký tự nháy đơn literal (`'226'`), không khớp regex số thuần túy `^\d+$`.

### Cú pháp Chuẩn
Truyền giá trị số trần hoặc chuỗi số không lồng dấu nháy:
```powershell
ssh admin-farm "powershell -NoProfile -ExecutionPolicy Bypass -Command \"& D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 -Tik 2 -MaxParallel 1 -ForceAvatarMachineList 226\""
```

---

## 3. Bẫy Avatar-Only Thiếu Kiểm Tra Cờ `avatar_smoke` tại `_handle_account_ready`

### Hiện tượng Hiện trường
Khi chạy đổi avatar trên Samsung S7 (Admin Remote M226):
- Runner chuyển sang Profile, xác nhận tài khoản đúng `holinh1003`.
- Bất ngờ bước tiếp theo báo lỗi:
  ```text
  [AVATAR_EDIT_OPEN_FAILED] ENSURE_AVATAR: Màn Sửa hồ sơ không mở
  ```
- Kiểm tra `popup_before.xml` và screenshot hiện trường: màn hình thiết bị đang ở ngoài trang **Following / Friends / Feed** (hiển thị bài đăng `Trinh Hyy`), hoàn toàn bị trôi khỏi Profile root.

### Căn nguyên
- Trong `scripts/tiktok_workflow/state_machine.py`, hàm `_handle_account_ready` có đoạn:
  ```python
  if self.context.config.get("profile_smoke") is not True:
      current_baseline = self._count_profile_video_tiles_across_grid(profile_xml)
  ```
- Đoạn code này chỉ kiểm tra cờ `profile_smoke`, **bỏ quên cờ `avatar_smoke`**!
- Trong chế độ Avatar-Only (`--avatar-smoke`), hệ thống vẫn gọi `_count_profile_video_tiles_across_grid`, cuộn 6 lần trên lưới video. Trên thiết bị S7, thao tác vuốt vô tình chạm vào 1 video tile làm bung trình phát video feed.
- Khi bước sang `ENSURE_AVATAR`, script phát hiện không ở Profile root, thực hiện vòng lặp `back()` và văng app.

### Quy tắc Phòng vệ
Trong chế độ Avatar-Only, màn hình Profile phải được giữ tĩnh 100%. Kiểm tra đầy đủ:
```python
is_smoke = bool(
    self.context.config.get("profile_smoke")
    or self.context.config.get("avatar_smoke")
)
if not is_smoke:
    current_baseline = self._count_profile_video_tiles_across_grid(profile_xml)
```

---

## 4. Bộ 5 Bài Test Hồi Quy Tự Động cho Operational Closeout Gate (No-Code Tasks)

Khi chốt phiên vận hành (đồng bộ Excel, SQLite queue, sync media remote farm), Reviewer Sol AI (`closeout_gate.py --input <file.md>`) yêu cầu artifact kỹ thuật định lượng và bằng chứng kiểm chứng độc lập.

BẮT BUỘC tạo script kiểm thử hồi quy tự động 5 bài test và đính kèm stdout vào gói audit:

1. **`test_target_row_values`:** Xác nhận dòng mục tiêu trong Excel (Row 27 Máy 226) chứa đúng Keyword mới (`Douyin Nam thần`) và bộ Hashtag chuẩn ngách.
2. **`test_sqlite_queue_status`:** Truy vấn trực tiếp SQLite xác nhận dòng tài khoản trong `avatar_replace_queue` có đúng `status = 'PENDING'`, `last_error = NULL`, đúng `may`, `tik`, `folder_video`.
3. **`test_md5_sync_cross_host`:** Tính mã băm MD5 của file `avatar.jpg` trên trạm Kibe và truy vấn MD5 trên máy chủ Admin qua SSH/SCP, xác nhận trùng khớp 100% (`5d89e72b... == 5d89e72b...`).
4. **`test_media_files_count`:** Đếm số lượng video clip trong folder giữa Kibe và Admin, xác nhận đầy đủ $\ge 40$ video và khớp số lượng giữa 2 trạm.
5. **`test_rollback_safety`:** Kiểm tra sự tồn tại và tính toàn vẹn của file backup Excel (`.bak`), đảm bảo có đầy đủ dữ liệu nguyên bản để khôi phục khi cần.
