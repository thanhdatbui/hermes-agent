# SQLite Master Ledger, CLI Tools, Web Dashboard & Anti-Pipe-Leak Invariant (2026-11-03)

## 1. Bản Đồ Vị Trí Lưu Trữ Toàn Bộ CSDL SQLite Trên Hệ Thống
Khi cần tra cứu dữ liệu, toàn bộ các file SQLite nằm tại các vị trí cố định sau:
1. **Dữ liệu Vận hành Phone Farm & Đơn Hàng (Chính):**
   * **`D:\Taadaa\data\farm_master.db`** *(SỔ CÁI TRUNG TÂM — SSOT)*:
     - `orders`: Toàn bộ 14 đơn hàng TikTok Shop (thông tin khách, mã vận đơn, trạng thái, timeline).
     - `tiktok_accounts`: Toàn bộ tài khoản TikTok (user, pass, 2FA secret, email liên kết, máy).
     - `machines`: 80 máy Kibe + 80 máy Admin (proxy endpoint, device serial, cụm).
     - `mailboxes`: Hòm thư Hotmail/Gmail (pass mail, OAuth refresh token Graph API, LIVE/DIE).
     - `slot_assignments`: Gán nick vào từng slot 1-8 trên 80 máy.
   * **`D:\Taadaa\data\tiktok_tracker.db`** *(69 MB — Tuổi nick & chỉ số follow)*:
     - Snowflake UID, tuổi nick tính theo ngày, lịch sử follow chéo, thống kê video.
2. **Dữ liệu AI & OmniRoute Proxy:**
   * **`C:\Users\Kibe\.omniroute\storage.sqlite`** *(1.08 GB)*:
     - Quản lý 310 tài khoản ChatGPT Web Pool, xoay vòng proxy, quota và nhật ký gọi model.
3. **Dữ liệu GPMLogin & Nuôi Gmail/ChatGPT:**
   * **`D:\Taadaa\GPM auto\chatgpt_accounts.db`**, **`chatgpt_pool.db`**, **`profiles.db`**:
     - Quản lý profile trình duyệt GPM và tài khoản ChatGPT tạo qua luồng automation.

## 2. Kỷ Luật Trải Nghiệm Người Dùng (Anti-Terminal-Command Spam)
- **User Preference:** User không muốn và không cần phải ghi nhớ hay gõ các câu lệnh SQL terminal phức tạp (`sqlite3 ... "SELECT ...;"`).
- **Giao diện trực quan ưu tiên:**
  1. **Web Farm Dashboard (`http://localhost:1905`):** Mở Chrome là xem được ngay dạng web có tab đơn hàng, ảnh chụp màn hình bóc tách, bảng máy farm, nút copy pass/2FA.
  2. **DB Browser for SQLite:** Mở file `D:\Taadaa\data\farm_master.db` trực tiếp bằng phần mềm có sẵn trên máy (`C:\Program Files\DB Browser for SQLite\DB Browser for SQLite.exe`) $\to$ tab Browse Data hiển thị dạng bảng lưới có lọc và tìm kiếm y hệt Excel mà không bị OneDrive khóa file.

## 3. Bẫy Pipe Leak Treo 60 Phút Khi Spawn GUI Foreground Trên Windows (TỐI NGUY HIỂM)
- **Cơ chế sự cố:** Trên môi trường MSYS / Git-Bash của Windows, khi Coordinator gọi lệnh foreground dạng:
  ```bash
  cmd.exe /c start "" "C:\Program Files\...\app.exe"
  ```
  tiến trình GUI kế thừa handle `stdout/stderr` của shell và giữ mở pipe. Terminal phía Hermes ngồi chờ tín hiệu EOF từ pipe đó, khiến cả session bị **đóng băng hoàn toàn suốt 60 phút** cho đến khi Gateway timeout kích hoạt.
- **Kỷ luật thực thi:**
  1. **User không dùng GUI desktop:** Ưu tiên 100% trả kết quả qua CLI (`sqlite3.exe` / `farm_db.py query`) hoặc Web Dashboard (`:1905`). Tuyệt đối không tự ý bật cửa sổ desktop nếu user không yêu cầu rõ ràng.
  2. **Nếu bắt buộc khởi chạy tiến trình Windows ngoài:** BẮT BUỘC dùng PowerShell detached hoặc redirect toàn bộ stream:
     ```bash
     powershell -Command "Start-Process 'C:\Program Files\...\app.exe' -ArgumentList '...'"
     ```
     hoặc trong cmd/bash: `<nul >nul 2>&1 &`.

## 3. Kỷ Luật Tool-Use Enforcement & Chống Hứa Hẹn Suông
- **Bẫy cam kết thụ động:** Coordinator tuyệt đối không được dùng câu thoại hứa hẹn "anh chỉ cần bảo, em sẽ bật..." mà không gọi tool, vì sẽ vi phạm trực tiếp cơ chế Tool-Use Enforcement.
- **Hành động ngay:** Khi người dùng hỏi về công cụ xem hoặc yêu cầu kiểm tra dữ liệu, Coordinator BẮT BUỘC khởi chạy ngay công cụ (hoặc gọi tool kiểm tra tiến trình `tasklist` / HTTP status) trong cùng lượt phản hồi và cung cấp bằng chứng hoàn tất.
