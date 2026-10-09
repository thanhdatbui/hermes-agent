# Kỷ Luật Báo Cáo Liên Cụm Tập Trung & Quy Tắc Single-Sink Bot Kibe

## 1. Bối cảnh & Chỉ đạo dứt khoát từ User
- **User đã bãi bỏ / dẹp hoàn toàn Bot Telegram bên máy Admin (`@taadaa_admin_hermes_bot`)**:
  - Không sử dụng bot Telegram trên máy Admin để bắn thông báo, watchdog hay cảnh báo farm nữa.
  - CẤM Agent tự ý cấu hình cron trên Admin gửi tin nhắn Telegram vào bất kỳ nhóm nào (`-5188753741` hay `-5373649734`).
  - Mọi cron trên Admin (nếu chạy) chỉ được để `deliver: local` hoặc ghi dữ liệu cache vào `D:\OneDrive\TaadaaData\admin\`.

## 2. Nguyên tắc "Single-Sink Bot Kibe" (Duy nhất Bot Kibe báo cáo)
- **Tập trung báo cáo tại Kibe**:
  - Toàn bộ báo cáo định kỳ toàn Farm (Render, Download Video gốc, Feed session, Up Avatar, 2FA...) của cả 2 cụm:
    + Cụm 1: **FARM KIBE (M1 - M80)**
    + Cụm 2: **FARM ADMIN (M201 - M280)**
    BẮT BUỘC do **DUY NHẤT Bot Kibe (`@Taadaa_hermes_sever_bot`)** gửi về nhóm Farm Alerts (`-5373649734`).
  - Khi user hỏi: "Ủa sao không báo farm admin?", điều đó có nghĩa là: **Tại sao báo cáo của Bot Kibe chưa tích hợp phần số liệu của Farm Admin vào cùng tin nhắn?** (Tuyệt đối không được hiểu nhầm thành "Admin phải tự chạy bot gửi tin").

## 3. Kiến trúc thu thập số liệu liên cụm (Host-Aware Aggregation)
- **Truy vấn từ xa qua LAN (SSH `admin-farm`)**:
  - Kibe kết nối tới Admin qua SSH Alias `admin-farm` (`192.168.110.119`), timeout 3-5 giây:
    ```bash
    ssh -o ConnectTimeout=3 admin-farm "python -u C:/Users/Admin/AppData/Local/hermes/scripts/farm_render_download_watchdog.py --json"
    ```
  - Thời gian thực thi cực nhanh (~1.5s), không làm nghẽn watchdog.
- **Phòng thủ 2 lớp với OneDrive Cache Fallback**:
  - Khi SSH thành công: Ghi đè file cache mới nhất tại `D:\OneDrive\TaadaaData\admin\last_render_stats.json`.
  - Khi máy Admin tắt, sleep hoặc rớt mạng LAN: Watchdog trên Kibe tự động đọc số liệu gần nhất từ file cache trên OneDrive và gắn nhãn cảnh báo `⚠️ Farm Admin (M201-280): Không kết nối được qua mạng LAN (dùng số liệu cache gần nhất)`.
- **Cấu trúc tin nhắn tổng hợp chuẩn**:
  - Gom chung 2 cụm và hiển thị tổng clip toàn farm trong đúng 1 tin nhắn duy nhất:
    + Header: `📊 BÁO CÁO TIẾN ĐỘ RENDER TOÀN FARM - HH:MM DD/MM/YYYY`
    + Khối 1: `🏢 FARM KIBE (MÁY 1-80)` (Tik1..Tik8, video gốc nếu đang tải)
    + Khối 2: `🏢 FARM ADMIN (MÁY 201-280)` (Tik1..Tik8, video gốc nếu đang tải)
    + Footer: `🔥 TỔNG CLIP RENDER TOÀN BỘ 2 FARM: X video`
