# Quy Chuẩn Preflight Reboot Retry & Chốt Chặn 10 Phút Trước Ca (Taadaa Farm)

## 1. Bối cảnh & Hiện tượng lỗi
- Farm chạy 3 ca chính: **06:00 (Ca 1)**, **12:00 (Ca 2)**, **18:00 (Ca 3)**.
- Task Scheduler kích hoạt reboot định kỳ lúc: **05:20**, **11:20**, **17:20** (trước ca 40 phút).
- Khi có một batch (như batch 2FA, Reg Gmail hoặc đổi tên) xuất phát lúc :05 và chạy kéo dài qua :20, máy giữ `pinned user lock` (`machine_N.lock.json`).
- Nếu Task Scheduler chỉ kích hoạt one-shot đúng :20, `farm_preflight_daily_reset.py` thấy active lock sẽ trả về `skipped_active_device_lock` và thoát 0 ngay. Hậu quả: Toàn bộ ca reboot bị hủy bỏ, bus USB và RAM không được làm sạch.

## 2. Giải pháp kỹ thuật 2 tầng

### Tầng 1: Task Scheduler Retry mỗi 5 phút trong khung :20 đến :50
- File cấu hình: `C:\Taadaa_Service\setup_daily_reboot_task.ps1`
- `$expectedTimes` bao gồm 7 mốc trigger mỗi ca:
  * Sáng: `05:20, 05:25, 05:30, 05:35, 05:40, 05:45, 05:50`
  * Trưa: `11:20, 11:25, 11:30, 11:35, 11:40, 11:45, 11:50`
  * Chiều: `17:20, 17:25, 17:30, 17:35, 17:40, 17:45, 17:50`
- Tính chất Idempotency qua Sentinel:
  * Khi máy nhả lock ở bất kỳ mốc nào (ví dụ 05:35), lệnh reboot dispatch thành công và ghi file sentinel:
    `reboot_sentinel_<date>_<shift>_admin.flag` và `_kibe.flag`.
  * Các lần trigger kế tiếp (05:40, 05:45, 05:50) lập tức kiểm tra sentinel, thấy `admin_done and kibe_done` -> thoát 0 ngay (`skipped_shift_complete`) trong < 0.1s.

### Tầng 2: Chốt chặn an toàn 10 phút trước ca (Reboot Cutoff Deadline)
- File thực thi: `farm_preflight_daily_reset.py`
- Hàm: `is_reboot_cutoff_active() -> tuple[bool, str]`
- Mốc cutoff: **10 phút trước khi ca mới bắt đầu**:
  * Trước Ca 1 (06:00): Chặn từ `05:51` đến `05:59` (phút 351–359 trong ngày).
  * Trước Ca 2 (12:00): Chặn từ `11:51` đến `11:59` (phút 711–719 trong ngày).
  * Trước Ca 3 (18:00): Chặn từ `17:51` đến `17:59` (phút 1071–1079 trong ngày).
- Hành vi: Ghi log `[SKIP] Sat gio Ca N (< 10 phut). Tu choi reboot de dam bao fleet san sang.` với `summary["outcome"] = "skipped_reboot_cutoff"`.
- Bỏ qua cutoff: Chỉ khi có tham số `--check-only`.
