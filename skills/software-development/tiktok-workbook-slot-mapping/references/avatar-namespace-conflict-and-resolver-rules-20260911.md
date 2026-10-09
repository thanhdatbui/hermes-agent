# Avatar Namespace Conflict & Resolver Rules (Hit 2026-09-11)

## 1. Triệu chứng sự cố
- Các tài khoản ở Row mới (ví dụ Row 5: `buithudung2011` Máy 1, `huehoafi23` Máy 7) bị up nhầm avatar giống hệt các tài khoản đã up từ lâu ở Row 1 (`khnh.vyyyy6` Máy 5 hình bà mập, `lipsellczaw` Máy 1 thằng đeo kính).
- User bức xúc: "sao có các tài khoảng giống ava nhau dù khac row? giỡn mặt tao r đó".

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Xung đột Namespace thư mục nguồn vs output trong `path_resolver.py`**:
   - `Folder Video` là thư mục render output (`D:\TIKTOK-videonuoinick\<Folder Video>`), công thức `(m-1)*8 + row_idx`. Ví dụ Máy 1 Row 5 có `Folder Video = 5`, Máy 7 Row 5 có `Folder Video = 53`.
   - `video gốc` là thư mục nguồn (`D:\video goc\<video_goc>`), công thức `(row_idx - 1)*80 + m`.
   - Trong `path_resolver.py`, hàm `resolve_avatar_path` cũ quét cả `search_roots = [media_source_root, Path(r"D:\TIKTOK-videonuoinick"), Path(r"D:\video goc")]`.
   - Khi tìm avatar cho nick có `Folder Video = 5`, resolver quét trúng `D:\video goc\5\avatar.jpg` (vốn là thư mục nguồn video của Máy 5 Row 1 - bà mập) và bốc ảnh này up cho nick Máy 1 Row 5!
   - Tương tự, `Folder Video = 53` bị quét trúng `D:\video goc\53\avatar.jpg` (thư mục nguồn của Máy 53 Row 1).

2. **Dính cache MediaStore / Gallery cũ trên thiết bị Android**:
   - Cùng 1 máy vật lý (như Máy 1), nếu trước đó nick Row 1 đã tải ảnh vào `/sdcard/DCIM/Camera/` hoặc `/sdcard/Pictures/` mà script không dọn sạch trước khi push ảnh mới, TikTok Media Picker có thể index ảnh cũ lên đầu album.

3. **Lỗi cú pháp CLI khi bọc launcher PowerShell**:
   - `run_tiktok_upload_batch.ps1` khai báo `[switch]$AvatarOnly`. Khi `run_tiktok_upload_avatar.ps1` pass `@splat` chứa `AvatarOnly = $true` qua `powershell.exe -File`, PowerShell serialize thành chuỗi `-AvatarOnly True` gây lỗi `ParameterArgumentTransformationError`. Bắt buộc truyền bare switch `-AvatarOnly`.
   - File workbook của Row 3 là `tik3.xlsx` (viết thường), trong khi các Row khác là `TikN.xlsx` (viết hoa chữ T). Đoạn script inline hardcode `Tik{N}.xlsx` sẽ fail trên Row 3.

## 3. Quy tắc bắt buộc
1. **CẤM quét `D:\video goc` trong `resolve_avatar_path`**:
   - Chỉ tìm avatar trong `media_source_root` và `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg`.
2. **Dọn sạch cache media trên thiết bị trước khi up avatar**:
   - Dọn sạch `/sdcard/DCIM/Camera/*`, `/sdcard/Pictures/*`, `/sdcard/Download/*`, `/sdcard/_ss*` trước khi push ảnh mới và scan MediaStore.
3. **Phân biệt đúng tên file workbook**:
   - Row 3: `tik3.xlsx` (chữ thường).
   - Row 1, 2, 4, 5, 6: `Tik1.xlsx`, `Tik2.xlsx`, `Tik4.xlsx`, `Tik5.xlsx`, `Tik6.xlsx`.
