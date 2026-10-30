# Bẫy Cạn Kiệt Đĩa D: (0.00 GB Free) Làm Tê Liệt Farm Admin & Tử Huyệt Báo Cáo Hứa Suông Không Hành Động

## 1. Hiện Tượng Đầy Đĩa D: (0.00 GB Free) Trên Admin-PC (192.168.1.200)
- **Triệu chứng kỹ thuật:**
  - Lệnh copy file qua PowerShell/Python văng lỗi I/O:
    ```text
    Exception calling "Copy": "There is not enough space on the disk."
    ```
  - Lệnh ghi log hoặc snapshot XML tạo ra các file rỗng 0 byte (`Length = 0`).
  - Các script Python/PowerShell nền bị kẹt vô thời hạn hoặc timeout sau 300s (`subprocess.TimeoutExpired`) do hệ điều hành Windows block các lời gọi ghi đĩa `WriteFile`.
- **Kiểm chứng dung lượng:**
  ```powershell
  Get-PSDrive D
  # Name: D, Used: 931.51 GB, Free: 0.00 GB
  ```
- **Các thư mục gây nghẽn đĩa chính trên Admin-PC:**
  - `D:\GoogleDriveCache` (bộ nhớ đệm đồng bộ video/avatar)
  - `D:\CodexRuntime` (chứa hàng trăm thư mục run/log/screenshots cũ tích lũy từ các tháng trước)
  - `D:\TIKTOK-videonuoinick-admin` và `D:\video goc may 2`

---

## 2. Tử Huyệt Điều Phối: Báo Cáo Hứa Suông (Turn-based Stall)
- **Cơ chế bẫy:**
  - Mô hình Coordinator hoạt động theo từng turn (lượt tin nhắn).
  - Khi Coordinator kết thúc câu trả lời bằng câu hứa hẹn suông:
    *"Em đang chuẩn bị đẩy bản patch này vào gmail_reg_v10.py, đồng bộ sang Admin-PC và chạy canary kiểm chứng ngay trên máy 246. Anh chờ em vài phút để chạy thử và nghiệm thu bằng ảnh thực tế!"*
    nhưng KHÔNG gọi tool nào thực thi ngay trong turn đó, **hệ thống sẽ dừng lại hoàn toàn**.
  - Không có cron hay worker nào tự động chạy tiếp trong background nếu Coordinator không kích hoạt tool. Hậu quả là session bị đóng băng cả tiếng đồng hồ gây bức xúc tột cùng cho User.
- **Quy tắc bất di bất dịch:**
  - **CẤM TUYỆT ĐỐI** kết thúc turn bằng lời hứa hẹn hành động tương lai mà không có tool call tương ứng ngay trong cùng response.
  - Phải thực thi trước (gọi lệnh, patch code, trigger process) rồi báo cáo trên kết quả thật đã trả về.

---

## 3. Khắc Phục Lỗi XML Nuốt Node Bằng WinRT OCR Thay Vì Fallback Mù
- **Tử huyệt ATX XML trên Google WebView (Android 7 - Samsung S7):**
  - Cây UI XML của ATX agent / UiAutomator thường xuyên bị mất node (đặc biệt là link xanh *"Tạo tài khoản"* ở góc dưới bên trái màn hình Sign-in `bounds=[73, 1446][329, 1486]`).
  - Mắt người và WinRT OCR đọc rõ ràng dòng chữ `Tao tåi khoån` ở tọa độ `(201, 1466)`.
- **Quy chuẩn xử lý:**
  - Tuyệt đối không vội vã kết luận *"màn hình bị Google ép Sign-in Only không có nút"* khi chỉ mới đọc XML.
  - BẮT BUỘC gọi `automation_core.ui_extract.extract_ui` (hoặc WinRT OCR screencap) bóc tách chữ từ screenshot thật.
  - Luôn chuẩn bị tọa độ calibrated fallback `(201, 1466)` cho màn hình chuẩn 1080x1920 của Samsung S7.
  - Tại bước popup menu cá nhân `[05_personal]`, không được hiểu nhầm `identifierId` còn tồn tại trong XML là `bounce-back`, vì popup là một overlay đè lên trên form sign-in cũ; phải tap trực tiếp tọa độ menu cá nhân `(350, 1180)`.
