# Native Media Delivery vs URL Links & Single-Machine Launcher Syntax (2026-10-10)

## 1. Operator Frustration & Critical Feedback
Trong phiên làm việc về chuẩn hóa avatar và hashtag cho tài khoản `@holinh1003` (Máy 226 Tik 2 Admin), Operator phản ứng gay gắt:
> *"Gửi ảnh lỗi r đm cứ gửi lỗi hoài"*
> *"R ok. Nãy mày gửi link đường dẫn chứ k phải ảnh. H thì ok r"*

### Nguyên nhân lỗi:
1. **Lỗi định dạng ảnh composite hoặc cú pháp gửi:** 
   - Khi Agent cố gắng ghép ảnh so sánh 3 cột (Current App vs New Square vs TikTok Circular simulation), kích thước ảnh bị dẹt ngang (1280x560), font chữ nhỏ, hoặc adapter Telegram parse thẻ gửi kèm caption quá dài/lỗi layout khiến trên client Telegram của điện thoại bị hiển thị thành đường link text/attachment lỗi thay vì hình ảnh native bung trực tiếp trên màn hình chat.
   - Khi gửi ảnh avatar nghiệm thu hoặc avatar đề xuất, Operator cần **xem trực tiếp file ảnh chân dung vuông gốc 512x512 (`MEDIA:D:/.../avatar.jpg`)** hiển thị native photo trên Telegram, không phải xem ảnh composite dẹt ngang hay link text.

2. **Quy tắc bất biến khi gửi ảnh cho Operator:**
   - Dòng `MEDIA:<absolute_path_ảnh>` BẮT BUỘC nằm ở dòng riêng biệt, không bọc trong code block (```` ``` ````), không nằm lẫn trong bảng biểu Markdown.
   - Luôn ưu tiên gửi file ảnh gốc chất lượng cao vuông (512x512 JPEG/PNG) thay vì ảnh composite dài ngoằng dễ bị co dãn trên màn hình mobile.
   - BẮT BUỘC soi mắt kiểm tra qua Vision trước khi gửi, đảm bảo file tồn tại, không lỗi mã hóa, không bị Telegram nuốt thành link văn bản.

---

## 2. Bẫy cú pháp tham số `-ForceAvatarMachineList` trong PowerShell Runner
Khi kích hoạt script runner `run_tiktok_upload_avatar.ps1` hoặc `run_tiktok_upload_batch.ps1`:

### Triệu chứng:
Lệnh gọi:
```bash
ssh admin-farm "powershell -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 -Tik 2 -MaxParallel 1 -ForceAvatarMachineList '226'"
```
Bị văng lỗi:
```text
Danh sách máy force avatar không hợp lệ: '226'
At D:\Taadaa\Tiktok-video\run_tiktok_upload_batch.ps1:152 char:13
+             throw "Danh sách máy force avatar không hợp lệ: $ForceAva ...
```

### Nguyên nhân:
Trong PowerShell parser qua SSH/Bash:
- Chuỗi tham số lồng dấu nháy đơn trong nháy kép `"'226'"` làm PowerShell giữ nguyên cả cặp dấu nháy đơn `'` bên trong chuỗi string (`$value = "'226'"`).
- Biểu thức regex kiểm tra trong `run_tiktok_upload_batch.ps1`:
  `if ($value -notmatch '^\d+$' -or [int]$value -lt 1)`
  gặp chuỗi `'226'` (có dấu nháy) không khớp `^\d+$`, dẫn đến ném ngoại lệ dừng luồng.

### Cú pháp chuẩn xác:
Truyền số trần không bọc nháy đơn lồng nhau, hoặc dùng `-Command`:
```powershell
# Cách 1: Truyền trực tiếp số nguyên
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 -Tik 2 -MaxParallel 1 -ForceAvatarMachineList 226

# Cách 2: Gọi qua -Command có script block
powershell -NoProfile -ExecutionPolicy Bypass -Command "& D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 -Tik 2 -MaxParallel 1 -ForceAvatarMachineList 226"
```

---

## 3. Khắc phục lỗi Màn Sửa Hồ Sơ Không Mở (`AVATAR_EDIT_OPEN_FAILED`)
Khi runner chạy trên máy S7 bị lỗi:
`[AVATAR_EDIT_OPEN_FAILED] ENSURE_AVATAR: Màn Sửa hồ sơ không mở`

### Căn nguyên:
Trong `_handle_account_ready` của `state_machine.py`, việc đếm lưới video `_count_profile_video_tiles_across_grid` vô tình cuộn màn hình và tap trúng video/feed. Khi chuyển sang `ENSURE_AVATAR`, máy đang ở màn hình Feed/Video player thay vì Profile root, khiến thao tác tìm nút "Sửa hồ sơ" hoặc icon bút chì bị thất bại.
- Luôn đảm bảo trong chế độ Avatar-Only (`is_smoke = True`), không thực hiện vuốt cuộn lưới video, giữ màn hình tĩnh ở Profile root để tap thẳng vào nút chỉnh sửa hồ sơ.
