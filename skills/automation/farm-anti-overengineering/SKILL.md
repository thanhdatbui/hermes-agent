---
name: farm-anti-overengineering
description: Kỷ luật thực thi chống over-engineering và cấm viết lại script canonical trên Taadaa Farm.
---
# Farm Anti-Overengineering Discipline

## Core Invariants
1. **Cắt đứt phụ thuộc file Excel trong runtime loop**:
   - Tuyệt đối cấm dùng `openpyxl` đọc/ghi file Excel trong các vòng lặp watchdog/worker tự động (tránh lỗi `PermissionError`, lock file OneDrive, và độ trễ 3-5s/round).
   - Mọi trạng thái runtime (Gmail DIE, gán Hotmail) BẮT BUỘC cập nhật và truy vấn trực tiếp từ SQLite SSOT (`D:/Taadaa/data/farm_master.db`). Excel chỉ đóng vai trò mirror một chiều cho con người xem.
2. **Cấm Coordinator tự chế lại bánh xe (Reinventing Automation Scripts)**:
   - Khi đã có sẵn canonical scripts trong `TikTok_Reg/` (`tiktok_reg_live_email_v1.py`, `tiktok_login_v1.py`, `do_logout_account.py`), cấm Coordinator dùng `write_file` tạo script tạm lẻ tẻ điều khiển ADB input.
   - Bắt buộc tái sử dụng canonical scripts hoặc mở rộng script hợp lệ thông qua `unified_patch_pipeline.py`.
3. **Kỷ luật chống khóc lóc & phân trần thoái thác**:
   - Khi bị Guard chặn, cấm viết văn xin lỗi, phân bua dông dài. Bắt buộc báo cáo thẳng nguyên nhân kỹ thuật $O(1)$ và thực thi lệnh tiếp theo dứt điểm.
4. **Cấm khẳng định khống khi chưa có biên lai Worker (Receipt Enforcer Guard)**:
   - CẤM TUYỆT ĐỐI dùng từ ngữ khẳng định "Đã dispatch", "Đã xử lý" khi chỉ kích hoạt trigger cronjob nền mà không có `task_id` từ worker thực thi. Gateway sẽ tự động phát hiện và dán nhãn `⚠️ [HỆ THỐNG CẢNH BÁO — CHƯA CÓ WORKER NÀO CHẠY THẬT]`.
   - Phân biệt rành mạch giữa **Supervisor đăng ký mới (`batch_gpm_5profiles_supervisor.py`)** và **Script cứu/refresh cookie session token (`chatgpt-web`)**. Acc đã `DONE` trong state thì supervisor bỏ qua hoàn toàn, cấm trigger bừa bãi.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> - Cơ chế Receipt Enforcer Hook, bẫy khẳng định khống qua trigger cronjob và cạm bẫy phân biệt script reg mới vs refresh cookie ChatGPT-Web: `skill_view(name='farm-anti-overengineering', file_path='references/receipt-enforcer-hook-and-false-cronjob-execution-20261102.md')`.
> - Kèo nuôi ngâm TikTok Lite song song, thực nghiệm Google SSO vs Manual Hotmail/Gmail, cạm bẫy Instant-Ban, luồng Login-First bypass, cắt đứt Excel sang SQLite SSOT và kỷ luật chống khóc lóc/chế bánh xe: `skill_view(name='farm-anti-overengineering', file_path='references/tiktok-lite-google-sso-vs-manual-mail-reg-20261101.md')`.
> - Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
