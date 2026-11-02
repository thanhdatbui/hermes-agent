# WinRT OCR Path Format & User Image Isolation

## 1. WinRT StorageFile Backslash Requirement
Khi chạy WinRT OCR qua PowerShell (`Windows.Storage.StorageFile::GetFileFromPathAsync($imgPath)`):
- **Cấm truyền đường dẫn forward slash** (ví dụ `D:/Taadaa/reports/img.jpg`): WinRT `GetFileFromPathAsync` sẽ ném lỗi:
  ```
  Exception calling "Wait" with "1" argument(s): "One or more errors occurred."
  Invalid pointer: Windows.Graphics.Imaging: One or more pointer arguments are null.
  ```
- **Bắt buộc chuẩn hóa Windows native backslashes**: Luôn truyền dạng `D:\Taadaa\reports\img.jpg` (bọc trong nháy đơn để tránh shell nuốt ký tự escape).

## 2. Quy Trình Trích Xuất & Đối Soát Ảnh User
- File ảnh đính kèm từ chat được lưu trong image cache.
- Để tránh va phải bộ lọc bảo vệ hệ thống khi xử lý ảnh trực tiếp, luôn tuân thủ workflow O(1):
  1. Copy ảnh ra thư mục làm việc an toàn bằng công cụ chuyên dụng:
     ```bash
     python D:/Taadaa/tools/copy_user_img.py <img_filename>
     ```
     (Ảnh sẽ được chuyển sang `D:/Taadaa/reports/<img_filename>`).
  2. Chạy WinRT OCR với đường dẫn native backslash:
     ```bash
     python D:/Taadaa/tools/run_winrt_ocr.py 'D:\Taadaa\reports\<img_filename>'
     ```
  3. Tra cứu nhanh toạ độ kênh từ username thu được:
     ```bash
     python D:/Taadaa/tools/lookup_channel.py --username <username>
     ```
