# Incident Case Study: Mất Ca Nuôi 18:00 do Stale Reconcile chiếm giữ Sequential Pool

## 1. Dấu Hiệu & Triệu Chứng (Symptoms)
- Ngày 2026-11-05, lúc 20:30 user hỏi: *"Sao 8h30 tối r vẫn chưa có report phiên 1 ca tối. Lỗi hả"*
- Kiểm tra `D:/Taadaa/runtime/kibe/live/2026-11-05` chỉ có:
  - `row-0-060015` (06:00)
  - `row-0-080023` (08:00)
  - `row-0-120011` (12:00)
  - `row-0-140033` (14:00)
  - `row-0-200102` (20:01)
  $\rightarrow$ Khung 18:00 (Ca 3 Phiên 1) mất trắng hoàn toàn không có run nào.

## 2. Truy Vết Nhật Ký Thực Thi (Execution Trace)
Kiểm tra output của Hermes Cron tại `%LOCALAPPDATA%\hermes\cron\output`:
1. `cdd43b124363` (`phase9-runner-tiktok-feed`, chu kỳ `*/15 * * * *`):
   - Chạy lúc `16:30:35`
   - Biến mất hoàn toàn ở các mốc: `16:45, 17:00, 17:15, 17:30, 17:45, 18:00, 18:15, 18:30, 18:45, 19:00, 19:15`
   - Đến `19:32:53` mới xuất hiện lại.
2. `8d6b3c18dd64` (`hourly-stale-post-receipts-reconcile`, chu kỳ `20 * * * *`):
   - Chạy lúc `17:20:00`.
   - Kết thúc lúc `19:18:56` (chạy mất **1 tiếng 58 phút** do vướng mạng SSH đồng bộ sang Admin-PC).
   - Ghi file: `2026-11-05_19-18-56.md`.
3. Ngay sau khi `8d6b3c18dd64` nhả luồng lúc `19:18:56`, hàng loạt job có `workdir` bị dồn ứ lập tức xả ra tuần tự:
   - `19:32:11`: `38e03cbbec9c` (`sync-agy-oauth-tokens`)
   - `19:32:53`: `cdd43b124363` (`phase9-runner-tiktok-feed`)
   - `19:32:53`: `d73f95a8e186` (`tiktok-order-lifecycle`)
   - `19:36:38`: `3269c6faeb03` (`cron-auto-feed-chatgpt-pool`)
   - `19:36:50`: `e61bfd81da93` (`daily-omniroute-db-cleanup`)

## 3. Bản Chất Kỹ Thuật
- `8d6b3c18dd64` có cấu hình `workdir: D:\Taadaa\tools`.
- `cdd43b124363` có cấu hình `workdir: D:\Taadaa\tiktok-luot nuoi acc`.
- Hermes Scheduler đưa cả hai vào `sequential_jobs` với `_get_sequential_pool()` (`max_workers = 1`).
- Trong 2 tiếng `8d6b3c18dd64` chạy, `_submit_with_guard` từ chối submit thêm job vào pool vì `_running_job_ids` đã bị chiếm giữ và khóa môi trường độc quyền.
- Khi runner được chạy lại lúc 19:32 thì đã quá 18:00, runner kiểm tra không khớp slot giờ chẵn (chỉ nhận 06, 08, 12, 14, 18, 20) nên thoát im lặng (`return None`). Ca nuôi chỉ thức dậy vào mốc 20:00 (`row-0-200102`).

## 4. Hành Động Phòng Ngừa
- Đã gỡ bỏ 100% thuộc tính `workdir` khỏi mọi job trong `jobs.json` (`workdir = None`).
- Toàn bộ job tự động hoá bắt buộc gọi qua đường dẫn tuyệt đối hoặc truyền `cwd` trong `subprocess`.
- Cấm thêm lại `workdir` vào bất kỳ cronjob nào của farm.
