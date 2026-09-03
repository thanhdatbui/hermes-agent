# Chẩn đoán & Xử lý Lỗi Tràn Bộ nhớ Ảo (Out of Virtual Memory), Lỗi 0xc0000142 & OneDrive Zombie Process

## 1. Hiện tượng & Cơ chế lỗi (Finding 2026-08-18)
- **Nguyên nhân gốc**: Khi một script cày cuốc (như download video đa luồng `download_by_niche.py`, browser automation, v.v.) bị memory leak hoặc phình RAM ảo vượt trần Commit Charge của Windows (hơn 100-150 GB Private Memory):
  1. Windows bắn popup cảnh báo: `Application popup: Windows - Out of Virtual Memory`.
  2. Toàn bộ các tiến trình khởi tạo mới (`adb.exe`, `conhost.exe`, `cmd.exe`) không thể nạp DLL hoặc cấp phát heap ban đầu -> bị crash ngay tại bước khởi động với mã lỗi **`0xc0000142` (STATUS_DLL_INIT_FAILED)** hoặc **`0xc0000409`** trên `ucrtbase.dll`.
  3. Tiến trình nền đồng bộ `OneDrive.exe` (đang giữ filter driver `cldflt.sys`) bị lỗi ngắt cấp phát bộ nhớ đột ngột và rơi vào trạng thái **Zombie Process trong Kernel Space** (`ThreadState = 5` - Wait IRP).

## 2. Đặc điểm của Zombie Process trên Windows & Hậu quả đối với OneDrive
- Khi `OneDrive.exe` bị kẹt ở Kernel I/O:
  - Lệnh `taskkill /F /PID <PID>` hoặc PowerShell `Stop-Process -Force` **HOÀN TOÀN BẤT LỰC** (trả về `ERROR: The process could not be terminated` hoặc no-op) do Windows không bao giờ cho phép User Mode kill một thread đang chờ Kernel IRP.
  - Khi mở giao diện OneDrive mới để đăng nhập lại: Tiến trình mới sẽ bị tranh chấp tài nguyên với tiến trình Zombie cũ -> gây ra hiện tượng:
    - Vòng xoay tải vô tận: *"Đang đăng nhập..."* (Signing in).
    - Báo lỗi đồng bộ: *"Chúng tôi không thể đồng bộ thư mục 'OneDrive' của bạn"* / *"Rất tiếc, hiện chúng tôi không thể thêm thư mục 'OneDrive' của bạn"*.
    - Báo lỗi tắt ứng dụng: *"Rất tiếc, chúng tôi không thể tắt OneDrive. Vui lòng tắt OneDrive theo cách thủ công..."*.

## 3. Quy tắc Vận hành An toàn cho Farm & Không làm gián đoạn việc
1. **Kiểm tra & Kill ngay tiến trình chiếm RAM**:
   - Dùng PowerShell truy tìm tiến trình ăn RAM ảo nhiều nhất:
     ```powershell
     Get-Process | Sort-Object -Property PrivateMemorySize64 -Descending | Select-Object -First 10 ProcessName, Id, @{Name='PrivateMB';Expression={[math]::round($_.PrivateMemorySize64/1MB,2)}}
     ```
   - Kill ngay PID thủ phạm bằng `Stop-Process -Id <PID> -Force` để giải phóng RAM ảo ngay lập tức. Sau khi kill, các tiến trình `adb.exe` và subprocess sẽ khởi chạy lại bình thường.

2. **Dữ liệu Local NTFS trên `D:\OneDrive\` hoàn toàn an toàn**:
   - Mặc dù cloud sync của OneDrive bị kẹt, hệ thống tệp cục bộ (Local NTFS) tại `D:\OneDrive\...` (như file workbook mapping `PROXYgandienthoai.xlsx`, các repo code, runtime) **vẫn đọc/ghi bình thường 100%**.
   - Mọi tiến trình automation (TikTok login, feed, follow, video download, reg...) **KHÔNG HỀ BỊ ẢNH HƯỞNG**, tuyệt đối không dừng hay kill các luồng batch đang chạy dở.

3. **Hướng xử lý chuẩn**:
   - Cứ để yên các batch công việc chạy cho đến khi hoàn tất.
   - Khi máy hoàn toàn rảnh việc, chỉ cần **Restart PC một lần** để giải phóng hoàn toàn kernel thread bị kẹt, sau đó mở lại OneDrive và đăng nhập bình thường.
