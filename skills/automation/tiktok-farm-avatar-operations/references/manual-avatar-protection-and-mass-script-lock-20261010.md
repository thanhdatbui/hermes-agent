# Khóa bảo vệ Avatar đổi thủ công & Ngăn chặn Script quét đĩa hàng loạt can thiệp

## 1. Bối cảnh & Căn nguyên sự cố (Operator mandate 10/10/2026)
- **Hiện tượng:** Operator phản ánh gay gắt: *"Đổi ava kênh này lại. Từ h bất kì kênh nào t yêu cầu đổi ava = tay thì k đc script can thiệp nữa (hiện có code kiểu quét folder tạo ava lại hàng loạt, nó dùng fix mấy nick lúc trc, nhưng vô tình phá luôn nick t yêu cầu đổi = tay t chat vs m)"*.
- **Ví dụ thực tế:** Kênh `@huy010822` (Máy 18 - Tik 5) thuộc ngách Hài học đường (áo trắng, khăn quàng đỏ). Trước đây Operator đã yêu cầu đổi thủ công sang ảnh nam sinh đeo kính khăn quàng đỏ. Nhưng sau đó, một đợt chạy script tự động hàng loạt (`regenerate_unique_avatars.py` hoặc `_make_avatar.py` fallback) quét toàn bộ folder trên đĩa để fix trùng/thiếu avatar, bốc lại frame fallback và đè ảnh anime đồi cỏ lên nick, phá mất avatar đã được Operator chọn duyệt.

## 2. Kiến trúc phòng vệ 3 lớp (Anti-Mass Regeneration Guard)
Mọi tài khoản / folder đã được Operator yêu cầu đổi avatar thủ công qua chat BẮT BUỘC phải được bảo vệ bất khả xâm phạm qua 3 lớp:

### Lớp 1: Central Registry (`manual_avatar_protected_folders.json`)
- Lưu tại 2 vị trí SSOT:
  1. `D:\Taadaa\Tiktok-video\data\manual_avatar_protected_folders.json`
  2. `D:\Taadaa\data\manual_avatar_protected_folders.json`
- Chứa danh sách các folder số được bảo vệ (`protected_folders`: `[141, 338, 2, 138, 148, 266, 275, 398]`) kèm metadata chi tiết (username, machine, tik, lý do, timestamp).

### Lớp 2: Cờ khóa nguyên tử tại thư mục (`.manual_avatar_locked`)
- Ngay khi đổi avatar thủ công thành công, BẮT BUỘC tạo file marker `.manual_avatar_locked` bên trong cả 4 thư mục:
  * `D:\TIKTOK-videonuoinick\<folder>\.manual_avatar_locked`
  * `D:\video goc\<folder>\.manual_avatar_locked`
  * `D:\TIKTOK-videonuoinick\<video_goc>\.manual_avatar_locked` (nếu khác số)
  * `D:\video goc\<video_goc>\.manual_avatar_locked` (nếu khác số)

### Lớp 3: Chốt chặn Guard trong toàn bộ Script tự động
- Module SSOT `scripts/manual_avatar_guard.py` cung cấp 2 hàm:
  * `get_protected_folders() -> set[int]` (đọc cả registry JSON lẫn quét marker file trên đĩa)
  * `is_folder_avatar_protected(folder) -> bool`
- **Tích hợp vào `regenerate_unique_avatars.py`:**
  * Hàm `find_all_duplicate_folders()` tự động trừ tập hợp: `unprotected_dups = unique_folders - protected`.
  * Hàm `process_folder()` kiểm tra đầu hàm: nếu `is_folder_avatar_protected(folder)` -> trả về ngay `(folder, True, "SKIPPED_MANUAL_PROTECTED", dur)`.
- **Tích hợp vào `_make_avatar.py`:**
  * Thêm cờ `--force`. Mặc định nếu không có `--force` mà folder thuộc danh sách bảo vệ -> In cảnh báo `[GUARD]` và return 0 thoát ngay, tuyệt đối không chạy tạo lại avatar hay ghi đè frame fallback.

## 3. Quy trình thực hiện khi nhận lệnh đổi avatar thủ công
Khi Operator chat yêu cầu: *"Đổi ava nick này", "Đổi ava theo tay", "Sửa ava kênh này"*:
1. **Trích xuất & kiểm chứng Vision:** Cắt frame chuẩn niche, kiểm tra circular crop, gửi ảnh vuông 512x512 (`avatar.jpg`) cho User nghiệm thu.
2. **Đồng bộ cả 2 đầu kho:** Ghi đè vào `D:\TIKTOK-videonuoinick\<folder>\avatar.jpg` và `D:\video goc\<folder>\avatar.jpg`.
3. **Cắm chốt bảo vệ ngay lập tức:**
   * Thêm folder vào `manual_avatar_protected_folders.json`.
   * Ghi file `.manual_avatar_locked` vào thư mục của folder đó trên đĩa.
4. **Cập nhật SQLite Queue:** Set `status = 'PENDING'` trong `avatar_replace_queue`.
5. **Kích hoạt runner & nghiệm thu:** Chạy canonical runner (`run_tiktok_upload_avatar.ps1`) và kiểm chứng bằng chứng Gate 6 full screenshot Profile. Set queue về `DONE`.
