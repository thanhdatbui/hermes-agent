# Admin Remote Fast Artifact Sync via OneDrive Live Junction

## 1. Vấn Đề Khi Trích Xuất Artifact Từ Máy Admin Remote (M201-280)
- Các máy Admin (IP `192.168.110.119:5037`, serial cụm Admin) lưu trữ logs và screenshots tại:
  `D:\CodexRuntime\tiktok-video\runs\run_<serial>_<date>_<time>\`
- Tool `pull_screenshot_from_admin.py` dùng phương thức cắt lát Base64 (15KB/chunk) qua `admin_ssh.py`. Với ảnh độ phân giải cao > 500KB, việc này tốn 40+ lượt gọi SSH tuần tự, chạm timeout 60s và làm nghẽn tiến trình điều phối.

## 2. Kỹ Thuật O(1): Fast Sync Qua OneDrive Live Folder
- Thư mục `D:\OneDrive\TaadaaData\admin` được đồng bộ thời gian thực 2 chiều giữa Admin-PC và Kibe-PC thông qua Microsoft OneDrive.
- Thay vì kéo file qua đường hầm SSH base64, Coordinator yêu cầu Admin copy file sang thư mục OneDrive bằng 1 lệnh thực thi nhanh:
  ```bash
  python D:/Taadaa/tools/admin_ssh.py 'python -c "import shutil; shutil.copyfile(r\"D:\CodexRuntime\tiktok-video\runs\<run_id>\<file_anh>.png\", r\"D:\OneDrive\TaadaaData\admin\<ten_anh>.png\"); print(\"DONE\")"'
  ```
  *(Lưu ý: `python` nằm trong `ALLOWED_COMMAND_PREFIXES` của `admin_ssh.py`, hoàn tất trong ~0.5 giây).*

## 3. Quy Trình 3 Bước Nghiệm Thu Ảnh Chuẩn Gate 6 & WinRT OCR
1. **Copy O(1) sang OneDrive trên Admin:**
   Chạy lệnh copy remote như mục 2. File sẽ đồng bộ về ổ cứng Kibe tại `D:\OneDrive\TaadaaData\admin\<ten_anh>.png` tức thì.
2. **Soi mắt & Ký Receipt WinRT OCR tại Kibe Local:**
   ```bash
   python D:/Taadaa/tools/run_winrt_ocr.py "D:\OneDrive\TaadaaData\admin\<ten_anh>.png"
   ```
   *Lưu ý quan trọng:* Đường dẫn truyền vào PowerShell WinRT OCR bắt buộc dùng dấu gạch chéo ngược Windows (`D:\...`), tránh dùng forward slash (`D:/...`) để không bị lỗi `NullReferenceException` khi gọi `GetFileFromPathAsync`.
   Lệnh này tự động gọi OCR trích xuất chữ và ký receipt vào `DEFAULT_RECEIPT_STORE` (thỏa mãn `guard_media_vision_gate.py`).
3. **Báo cáo Telegram kèm MEDIA:**
   Đính kèm đường dẫn cục bộ vào tin nhắn báo cáo:
   `MEDIA:D:\OneDrive\TaadaaData\admin\<ten_anh>.png`
   Đảm bảo tuân thủ tiêu chuẩn: MEDIA ở dòng 1, dòng 2 `### [MÁY XX]`, và mô tả hiện trường đã soi tận mắt qua OCR.
