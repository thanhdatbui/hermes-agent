# Google Birthday & Gender Dropdown Hint Pathology & GDrive Backup Execution Order

## 1. Google Birthday & Gender Dropdown Hint Trap (Android 7 GMS WebView)
### Hiện tượng
Khi đăng ký tài khoản Gmail trên Android 7 (Samsung Galaxy S7 cụm Admin / Kibe), tại bước `[08_bday]` và `[08_bday_gender]`:
- Script chọn Tháng qua DPAD hoặc popup picker thành công.
- Script tap chọn Giới tính "Nữ" (hoặc "Female") thành công.
- Tuy nhiên hàm kiểm tra `month_field_has_value` và `gender_field_has_value` liên tục báo:
  - `[08_bday_month] Không chọn được tháng 05 bằng DPAD`
  - `[08_bday_gender] Gender still empty after selecting Nữ/Female`
- Khiến cả batch 15 máy đều dừng lại ở màn hình nhập thông tin cơ bản dù thực tế trên màn hình đã chọn xong.

### Nguyên nhân kỹ thuật
- Trong cây UI Automator / ATX XML của WebView GMS, khi một option trong Spinner được chọn, giá trị đó **KHÔNG** được ghi vào thuộc tính `text` hay `content-desc` của Spinner node (các thuộc tính này bị để rỗng `text=""`).
- Thay vào đó, WebView của Google đẩy giá trị đã chọn vào thuộc tính `hint` của Spinner:
  - `hint="Tháng 10"` hoặc `hint="Tháng 5"`
  - `hint="Giới tính <Nữ>"` hoặc `hint="Giới tính (Nữ)"`

### Giải pháp kỹ thuật chuẩn
1. Trong `month_field_has_value(device_id, target_num)`:
   - Duyệt qua các node Spinner hoặc có thuộc tính `hint`.
   - Kiểm tra trực tiếp:
     ```python
     hint = a.get("hint", "") or ""
     if hint:
         hint_flat = strip_accents(hint)
         if (f"Tháng {target_num}" in hint or f"Tháng {target_num:02d}" in hint
                 or f"thang {target_num}" in hint_flat or f"thang {target_num:02d}" in hint_flat):
             return True
     ```
2. Trong `gender_field_has_value(xml)`:
   - Duyệt qua các child node của node có `resource-id="gender"`:
     ```python
     for child in nd.iter("node"):
         hint = child.attrib.get("hint", "") or a.get("hint", "")
         if has_text_loose(hint, "Nữ", "Nu", "Female"):
             return True
     ```

---

## 2. Thứ tự thực thi Cron đẩy Google Drive trên Admin-PC (`Taadaa_Sync_GDrive_Backup`)
### Hiện tượng
- Ổ đĩa D: trên Admin-PC bị đầy 0.00 GB (100% Full Disk) dù cronjob `Taadaa_Sync_GDrive_Backup` vẫn chạy định kỳ 2 tiếng/lần.
- Thư mục `D:\TIKTOK-videonuoinick-admin` phình to lên tới 591 GB, trong khi `D:\video goc may 2` chiếm 176 GB.
- Hệ thống bị lỗi I/O hàng loạt (`There is not enough space on the disk`), không thể copy code, ghi log hay chụp ảnh màn hình.

### Nguyên nhân
File `D:\Taadaa\tools\start_sync_gdrive_hidden.vbs` trước đây đặt thứ tự:
1. `D:\Taadaa\tools\sync_and_clean_gdrive.py 640`
2. `C:\Users\Admin\manage_admin_media_gdrive.py offload 640`

Khi chạy `sync_and_clean_gdrive.py` trước, script này chỉ xóa dọn video gốc khi folder tương ứng đã render đủ >= 45 clip. Do tiến trình chạy lâu hoặc bị ngưng khi có game (`league of legends.exe`, `tftclient.exe`, `war3.exe`), bước 2 (`manage_admin_media_gdrive.py offload`) không bao giờ được chạy tới hoặc không kịp giải phóng dung lượng. Hậu quả là 591 GB video render không được đẩy lên GDrive, làm cạn sạch ổ đĩa.

### Giải pháp bắt buộc
Trong `D:\Taadaa\tools\start_sync_gdrive_hidden.vbs`, **BẮT BUỘC** đảo thứ tự chạy:
```vbs
Set WshShell = CreateObject("WScript.Shell")
' 1. Uu tien chay offload video render so lon (>= 21) len GDrive truoc de giai phong ngay lap tuc hang chuc den hang tram GB o D
WshShell.Run """C:\Users\Admin\AppData\Local\Programs\Python\Python311\pythonw.exe"" C:\Users\Admin\manage_admin_media_gdrive.py offload 640", 0, True

' 2. Sau do moi chay dong bo va don dep video goc len GDrive
WshShell.Run """C:\Users\Admin\AppData\Local\Programs\Python\Python311\pythonw.exe"" D:\Taadaa\tools\sync_and_clean_gdrive.py 640", 0, True
Set WshShell = Nothing
```
Cấu hình này đảm bảo ngay khi cron kích hoạt, các video render số lớn sẽ được chuyển lên `G:\My Drive\video_render_backup` và xóa khỏi đĩa D:, giải phóng ngay hàng chục GB dung lượng trống an toàn.
