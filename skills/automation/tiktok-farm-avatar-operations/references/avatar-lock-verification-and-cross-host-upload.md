# Avatar Lock Verification and Cross-Host Upload Rules

## 1. Nguyên Tắc Upload Trực Tiếp Ngay Sau Khi Duyệt
- Khi avatar người thật đã được duyệt: CẤM chỉ nạp ảnh vào đĩa rồi ghi `PENDING` vào Excel để chờ cron tối.
- BẮT BUỘC kích hoạt tiến trình upload trực tiếp ngay lập tức (`run_upload_avatar.py` hoặc trigger qua Admin SSH nếu là máy dải Admin >= 200).
- Excel chỉ là nơi đối soát trạng thái hậu kiểm (`Avatar = OK`), không phải đích đến thay thế cho việc upload thực tế.

## 2. Quy Tắc Khóa Cờ Kép Sau Khi Upload (Double Lock)
Khi upload thành công lên TikTok app:
1. **Khóa thư mục trên đĩa (`.manual_avatar_locked`):**
   - Đảm bảo cờ `.manual_avatar_locked` tồn tại trong cả 3 vị trí:
     * `D:/video goc/{folder}/.manual_avatar_locked`
     * `D:/TIKTOK-videonuoinick/{folder}/.manual_avatar_locked` (Kibe)
     * `D:/TIKTOK-videonuoinick-admin/{folder}/.manual_avatar_locked` (Admin)
   - Đăng ký folder ID vào `manual_avatar_protected_folders.json`.
   - Ngăn chặn triệt để các script healer, batch render, audit avatar tự động quét và ghi đè file `avatar.jpg`.
2. **Khóa trạng thái vận hành (`Avatar = OK`):**
   - Runner tự động cập nhật atomic vào `Tik*.xlsx` cột `Avatar = OK`.
   - Khi đã là `OK`, các ca nuôi nick / đăng video định kỳ sẽ tự động nhận diện và skip qua bước đổi avatar, không tác động hay quấy rầy tài khoản nữa.

3. **Kỷ Luật Sao Chép Thư Mục & Tránh Lỗi SameFileError (Python)**
   - Khi sao chép `avatar.jpg` sang cả 2 kho `F_src` (video gốc) và `F_vid` (render đích), nếu file nguồn được chọn nằm sẵn trong một trong hai thư mục, lệnh `shutil.copy2` sẽ văng lỗi `shutil.SameFileError`.
   - BẮT BUỘC kiểm tra đường dẫn chuẩn hóa trước khi sao chép:
     ```python
     dst_f = os.path.join(d, "avatar.jpg")
     if os.path.abspath(src).lower() != os.path.abspath(dst_f).lower():
         shutil.copy2(src, dst_f)
     ```
   - Đồng thời cắm cờ kép `.manual_avatar_locked` và `.manual_hashtag_locked`, ghi nhận folder ID vào cả hai registry `manual_avatar_protected_folders.json` và `manual_hashtag_protected_folders.json`.

4. **Kiểm Tra Trạng Thái Idempotent Trên Thiết Bị Trước Khi Đổi Tên / Bio**
   - Trước khi kích hoạt script đổi tên / bio tự động trên máy, BẮT BUỘC dùng Vision / WinRT OCR chụp và soi màn hình Profile trước.
   - Nếu tài khoản đã có tên người thật tiếng Việt chuẩn và Bio đúng ngách (do đã được cập nhật trước đó), xác nhận ngay trạng thái đạt chuẩn, tránh việc bấm mù hay kích hoạt lại luồng UI có thể bị kẹt do các banner chiến dịch (ví dụ banner quyên góp/WWF làm xê dịch tọa độ nút "Sửa hồ sơ").

5. Quy Trình Upload Cross-Host (Máy Admin dải >= 200)
- Thiết bị dải >= 200 cắm USB trực tiếp vào Admin-PC (`192.168.110.119`), không nhìn thấy qua ADB local của Kibe.
- `run_upload_avatar.py` tự động phát hiện `machine >= 200` để trỏ `-HostConfigPath` sang `D:\Taadaa\machine-config\admin.yaml`.
- Đồng bộ file ảnh chuẩn sang Admin-PC trước khi chạy: `D:/TIKTOK-videonuoinick-admin/{folder}/avatar.jpg` và cắm cờ `.manual_avatar_locked`.
- Lệnh kích hoạt chuẩn qua SSH:
  ```powershell
  python D:/Taadaa/tools/admin_ssh.py --powershell --timeout 1200 "Set-Location D:\Taadaa\Tiktok-video; echo RUN | powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run_tiktok_upload_avatar.ps1 -Tik <N> -MaxParallel 1 -ForceAvatarMachineList <M> -HostConfigPath D:\Taadaa\machine-config\admin.yaml"
  ```
- **Xử lý trễ MediaStore (`AVATAR_PICKER_NO_MATCH`):** Sau khi push file vào `/sdcard/Pictures/`, nếu album báo trống do MediaStore chưa index kịp, runner retry lần 2 sẽ nhận diện được tile ảnh đầu tiên để crop và lưu.
