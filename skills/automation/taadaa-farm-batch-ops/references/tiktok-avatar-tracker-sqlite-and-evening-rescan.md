# Kiến trúc Quản lý Trạng thái Avatar & Báo cáo Realtime Farm TikTok

## 1. Nguồn Dữ Liệu Avatar (Source of Truth): SQLite vs Excel
- **Source of Truth thực tế của TikTok:** Là bảng `snapshots` trong `D:\Taadaa\data\tiktok_tracker.db` (dữ liệu bóc tách HTML từ profile TikTok qua `tiktok_account_tracker.py` / Dashboard port 1905).
- **Tránh sai lệch Excel:** Cột `Avatar` trong Excel (`TikN.xlsx`) có thể bị ghi nhận "OK" ảo hoặc lệch trạng thái khi TikTok nhả avatar / chưa crawl. Ngược lại, database crawler kiểm tra chính xác tag `has_avatar` từ avatar URL thực tế (loại trừ default avatar `musically-maliva-obj`).
- **Phân tách Host (Kibe vs Admin):**
  - Bảng `farm_account_info` lưu tập trung cả tài khoản của máy Kibe (`1..80`) và Admin (`201..280`).
  - Khi query CTE `Ranked` theo `tik = ?`, **BẮT BUỘC** lọc theo dải máy hoặc `host_id`:
    * Host `admin`: `WHERE m.tik = ? AND (m.host_id = 'admin' OR m.may >= 200)`
    * Host `kibe`: `WHERE m.tik = ? AND (m.host_id = 'kibe' OR m.host_id IS NULL OR m.host_id = '') AND m.may < 200`
  - Nếu thiếu điều kiện này, các Tik như Tik 7 sẽ bị trộn lẫn 65 máy Kibe và 67 máy Admin thành 132 máy.

## 2. Vấn Đề Stale Snapshot 07:00 Sáng & Giải Pháp Auto-Rescan
- **Hiện tượng lệch pha:** Cron toàn farm `daily-tiktok-farm-tracker` chỉ chạy 1 lần lúc **07:00 sáng**. Các batch upload avatar chạy vào ca tối (21:00 – 23:45) dù thành công trên máy thật thì database vẫn lưu snapshot cũ lúc 7h sáng.
- **Hậu quả:** Khi ca tối kết thúc (sau 23:30), watchdog xuất báo cáo tổng kết đọc DB cũ vẫn thấy các máy đó thiếu avatar $\rightarrow$ Báo cáo bị sai và hôm sau watchdog tiếp tục kích hoạt lại các máy đã up.
- **Giải pháp chuẩn hóa (In-Session Re-scan):**
  - Ngay khi mỗi batch upload avatar hoàn tất trong `check_batch_status`:
    Lấy danh sách máy vừa upload `running.get("machines", [])`.
    Gọi hàm `rescan_completed_machines(machines)` thực thi `tiktok_account_tracker.py --machines ... --workers 10` qua proxy pool để cập nhật snapshot mới (`has_avatar = 1`) vào SQLite ngay trong đêm.
  - Trước khi xuất báo cáo tổng kết cuối ca (`report_final_summary`), kiểm tra và trigger rescan các máy đã chạy trong session.

## 3. Lịch Trình Cron Khớp Cửa Sổ Báo Cáo
- Hàm `is_after_evening_window(now)` trong watchdog thường mở từ sau 23:45 đến 04:00 sáng.
- Nếu cronjob schedule chỉ đặt `*/5 20,21,22,23 * * *`, lần tick cuối là lúc 23:55. Nếu batch cuối cùng chạy qua 00:00 (ví dụ 23:35 đến 23:56), scheduler sẽ không tick nữa dẫn đến báo cáo tổng kết bị nuốt (im lặng hoàn toàn).
- **Quy tắc:** Schedule của cronjob bắt buộc phải bao quát toàn bộ khung giờ mà script logic cho phép chạy báo cáo (ví dụ: `*/5 20,21,22,23,0,1,2,3 * * *`).
