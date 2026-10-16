# Triage Thiếu Video Gốc vs Lệch Render Kho Nguồn Cũ & Bẫy Proxy 502 Loopback Admin (16/10/2026)

## 1. Bản Chất Khi User Hỏi: "Nguồn Cũ Chứ Không Phải Niche Cũ"
- **Sự khác biệt cốt lõi:**
  * **Cùng Niche (Chung chung):** Cùng thể loại nội dung (ví dụ cùng là ẩm thực, cùng là thú cưng, cùng là thiết bị điện tử).
  * **Cùng Nguồn (Cũ/Chính xác - User Requirement):** BẮT BUỘC phải là **cùng 1 channel / cùng 1 creator profile** đã cấp cho tài khoản đó từ ban đầu (để đảm bảo tính đồng nhất về khuôn mặt, giọng nói, phong cách, không biến tài khoản thành nồi lẩu thập cẩm).
- **Cơ chế kiểm soát 1 FOLDER = 1 KÊNH DUY NHẤT:**
  * Kiểm tra thư mục gốc `D:\video goc\<F_src>`: Toàn bộ file video đều tải từ cùng một channel/tác giả.
  * Khi nick báo thiếu video để upload (ví dụ Máy 60 Tik 4, folder render 476, nguồn 300):
    * **Bẫy ngộ nhận thiếu nguồn cào:** Thư mục render `D:\TIKTOK-videonuoinick\476` chỉ có `1.mp4..10.mp4` và `27.mp4..61.mp4`, khuyết `11.mp4..26.mp4`.
    * **Kiểm tra kho gốc $F_{src}$ trước:** Trong `D:\video goc\300` thực tế ĐÃ CÓ ĐỦ từ `1.mp4..65.mp4` tải từ ngày 17/08/2026 từ cùng một kênh. Sự thiếu hụt chỉ là do tiến trình render cũ bị ngắt quãng.
    * **Xử lý O(1):** Dùng `random_batch_render.py` với `--file-list` trỏ đúng các file bị khuyết trong kho gốc `D:\video goc\300` và `--start-seq 11`, render bù vào thư mục render đích. Không cần tải mới từ Internet, bảo tồn 100% đúng nguồn creator cũ.

---

## 2. Bẫy Downloader Kẹt 502 Bad Gateway Trên Host Admin (`proxy_pool_69.txt`)
- **Hiện tượng:**
  * Trên Admin-farm, tiến trình `download_by_niche.py` (PID 3300 / 15000) và `run_admin_downloader_service.py` vẫn đang chạy trong RAM (nhìn thấy qua `tasklist`).
  * Tuy nhiên, kiểm tra file log `D:\CodexRuntime\tiktok-video-machine2\download_admin_p10.log` thấy liên tục quăng lỗi:
    `ProxyError: ('Unable to connect to proxy', OSError('Tunnel connection failed: 502 Bad Gateway'))`
  * Hậu quả: Downloader chạy vòng lặp ngầm nhưng `folders_repaired = 0`, không tải được bất kỳ video mới nào về đĩa.
- **Nguyên nhân cốt lõi:**
  * File `proxy_pool_69.txt` trên Admin chứa danh sách proxy cấu hình bằng domain ngoài: `mirotik1.taadaa.click:10001..10035`.
  * Máy Admin (`192.168.110.119`) nằm cùng dải mạng LAN nội bộ với router MikroTik (`192.168.110.2`). Khi máy con trong LAN gọi loopback ra domain DDNS WAN (`mirotik1.taadaa.click`), router MikroTik chặn hoặc trả mã `502 Bad Gateway`.
- **Kiểm chứng & Khắc phục:**
  1. Kiểm tra kết nối trực tiếp LAN IP qua PowerShell trên Admin:
     `Test-NetConnection -ComputerName 192.168.110.2 -Port 10001` $\rightarrow$ `TcpTestSucceeded : True`.
  2. Chuẩn hóa `proxy_pool_69.txt` trên Admin sang IP LAN MikroTik:
     Thay `mirotik1.taadaa.click:100xx` $\rightarrow$ `192.168.110.2:100xx`.
  3. Tree-kill tiến trình downloader cũ trên Admin và khởi chạy lại dịch vụ để nạp danh sách proxy mới vào RAM.

---

## 3. Bộ Ba Kiểm Chứng Khi User Hỏi "R Cào Chưa?"
- CẤM TUYỆT ĐỐI chỉ nhìn vào `tasklist` thấy `python.exe` đang chạy rồi vội vàng trả lời "đang cào bình thường".
- BẮT BUỘC đối soát 3 yếu tố (Verification Triad):
  1. **Process live:** `Get-CimInstance Win32_Process` xác nhận dòng lệnh `download_by_niche.py` đang chạy.
  2. **Log liveness & No error:** Đọc 25 dòng cuối của log downloader (`download_admin_p10.log` hoặc `download_run.log`), xác nhận không bị dính bão lỗi `ProxyError 502 Bad Gateway` hay `Bot-check`.
  3. **File tăng thực tế:** Số lượng file `.mp4` trong thư mục nguồn (`D:\video goc may 2\<F_src>`) hoặc số byte của file log thực sự tăng trưởng.
