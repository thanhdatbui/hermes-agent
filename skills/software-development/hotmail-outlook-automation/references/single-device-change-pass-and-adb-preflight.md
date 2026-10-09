# Hotmail Single Device Password Change & ADB Preflight

## Cú pháp thực thi trên Windows MSYS Bash
- **Lỗi thường gặp**: Truyền trực tiếp đường dẫn dạng POSIX `/d/Taadaa/...` làm đối số file cho trình thông dịch Python Windows sẽ bị MSYS tự động chuyển thành `C:\d\Taadaa\...`, dẫn đến lỗi `[Errno 2] No such file or directory`.
- **Cú pháp chuẩn**:
  ```bash
  cd /d/Taadaa/Hotmail && "D:/Taadaa/python-envs/automation/Scripts/python.exe" "scripts/run_change_pass_single.py" --device <SERIAL> --machine <M> --email <EMAIL> --current-password "<OLD>" --new-password "<NEW>" --live
  ```

## Preflight ADB & Tra cứu Serial
1. **Kiểm tra thiết bị online**:
   Luôn chạy `adb devices` kiểm tra serial mục tiêu trước khi khởi chạy script đổi mật khẩu. Nếu serial không có trong danh sách thiết bị (offline/tuột cáp/mất nguồn), phải dừng lại và báo cáo phần cứng thay vì chạy lặp lại mù quáng.
2. **Tra cứu mapping nhanh**:
   Tránh chạy `grep -rn` toàn bộ thư mục `D:\Taadaa\` (dễ bị timeout 180s do cây thư mục lớn). Sử dụng script Python với `openpyxl` để đọc trực tiếp sheet `Tài Khoản` trong `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`:
   ```python
   import openpyxl
   wb = openpyxl.load_workbook(r"D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx", data_only=True)
   ws = wb["Tài Khoản"]
   # Đọc dòng cần kiểm tra
   ```
3. **Quy tắc an toàn cập nhật Excel**:
   Tuyệt đối không cập nhật password vào file Excel (`taikhoan_dat_v2_updated .xlsx` / `gmail_clean_v2.xlsx`) khi script chưa xác nhận thành công và chưa có hình ảnh bằng chứng (evidence snapshot).
