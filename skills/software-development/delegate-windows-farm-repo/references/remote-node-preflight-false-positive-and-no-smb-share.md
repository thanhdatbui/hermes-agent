# Bẫy Preflight Kiểm Tra File Local Cho Node Từ Xa & Cấm Đề Xuất Share Mạng LAN (SMB) Trong Kiến Trúc 1-Controller Phone Farm (2026-10-05)

## 1. Hiện tượng & Phản ứng Người Dùng
- **Hiện tượng:**
  - Watchdog báo lỗi hàng loạt "Hết video/Cần cào" (`video_not_rendered`) cho cụm máy node phụ (ví dụ: máy Admin 201-280), trong khi video đã render đầy đủ và nằm sẵn trên node phụ (`D:\TIKTOK-videonuoinick-admin`).
  - Coordinator kết luận vội vàng và đề xuất giải pháp ngớ ngẩn:
    *"Tao có cần share thư mục TIKTOK-videonuoinick-admin từ máy Admin qua mạng LAN (hoặc điều chỉnh preflight check qua ADB/SSH) để Kibe nhận diện đúng video không?"*
  - **Phản ứng gay gắt của User:**
    *"Là sao tự nhiên share thư mục admin qua kibe để nhận diện đúng video là cái lồn gì"* -> *"Sửa tiếp cho tao đn"*
- **Bài học cốt lõi:**
  - Phone Farm Taadaa có kiến trúc: **1 máy Kibe làm controller duy nhất điều khiển toàn bộ phone farm**.
  - Các tài nguyên render/kho video của node nào thì nằm cục bộ trên ổ đĩa của node đó (`D:\TIKTOK-videonuoinick` trên Kibe, `D:\TIKTOK-videonuoinick-admin` trên Admin).
  - **CẤM TUYỆT ĐỐI** đề xuất mount SMB, chia sẻ thư mục Windows mạng LAN, hoặc copy đồng bộ kho video khổng lồ giữa các máy farm.

## 2. Root Cause
1. **Cross-Host File Existence Check:**
   - Script điều phối feed session (`multi_machine_feed_session.py`) chạy trên máy Controller (Kibe).
   - Hàm preflight upload hook (`_run_upload_hook`) lại dùng `Path.is_file()` local để kiểm tra đường dẫn tài nguyên của node phụ (`D:\TIKTOK-videonuoinick-admin`).
   - Do đường dẫn chỉ tồn tại cục bộ trên máy phụ, check local trên controller luôn trả về `False` $\rightarrow$ sinh ra false-positive `video_not_rendered` hàng loạt (41 máy).
2. **Subprocess Local Run Sai Host:**
   - Sau preflight, lệnh subprocess upload lại chạy local trên Kibe và truyền đường dẫn local của Kibe, không thể tương tác trực tiếp với file video trên máy Admin.

## 3. Biện pháp Khắc phục Chuẩn Hoá (Remote Execution on Target Node)

### A. Phân Nhánh Preflight Theo Target Machine / Host
- Với máy thuộc node phụ (`account.machine >= 200` hoặc host Admin):
  - **BỎ QUA** việc gọi `Path.is_file()` / `glob()` local trên máy Controller (Kibe).
  - Giữ `video_file` chỉ làm label/metadata cho report/telemetry.

### B. Thực Thi Upload Workflow Từ Xa Qua SSH
- Gọi thực thi trực tiếp trên node đích bằng lệnh SSH có sẵn (`ssh admin-farm`) sử dụng:
  - Đúng môi trường Python của node phụ: `D:/Taadaa/python-envs/automation/Scripts/python.exe`
  - Đúng repo path trên node phụ: `D:/Taadaa/Tiktok-video`
  - Đúng config: `D:/Taadaa/Tiktok-video/config-admin.yaml`
  - Đúng workbook tương ứng với batch/session: `D:/OneDrive/TaadaaData/admin/{workbook_path.name}` (Tik1.xlsx, Tik2.xlsx...)
  - Đúng source root cục bộ: `D:/TIKTOK-videonuoinick-admin`
  - Exact target serial & video number.
- **TUYỆT ĐỐI KHÔNG** truyền biến môi trường `ADB_SERVER_SOCKET` remote của Controller vào tiến trình chạy cục bộ trên node đích.

### C. Giữ Vững Cơ Chế Fail-Closed & Ledger Semantics
- Kết quả trả về qua stdout remote (`Post verification PASSED`, `Workflow completed successfully`) vẫn được kiểm chứng nghiêm ngặt.
- Mọi exit code khác 0, veto từ report JSON, hoặc thiếu marker thành công đều fail-closed như quy chuẩn cũ.
- Máy Kibe (1–80) giữ nguyên nhánh chạy local hoàn toàn.
