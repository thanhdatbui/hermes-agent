---
name: hermes-cron-parallel-dispatch-and-workdir-safety
description: "Kỷ luật quản trị cronjob Hermes: cấm tham số workdir gây nghẽn sequential pool đơn luồng, đảm bảo dispatch song song cho runner và watchdog farm."
---
# Hermes Cron Parallel Dispatch & Workdir Safety

## 1. Bản Chất Bẫy Nghẽn Sequential Pool Đơn Luồng (Hermes Scheduler)
Trong `Hermes/cron/scheduler.py`:
- **Phân loại jobs tại mỗi tick:**
  ```python
  sequential_jobs = [j for j in due_jobs if (j.get("workdir") or "").strip()]
  parallel_jobs = [j for j in due_jobs if not (j.get("workdir") or "").strip()]
  ```
- **Hành vi Sequential Pool:**
  - Bất kỳ cronjob nào có `workdir` đều bị Hermes coi là *env-mutating job* (thay đổi `os.chdir` và `os.environ["TERMINAL_CWD"]`).
  - Toàn bộ `sequential_jobs` bị gom vào một `_get_sequential_pool()` duy nhất chạy **đơn luồng (single-thread, max_workers = 1)**.
  - Khi một job trong pool này chạy lâu, bị timeout mạng hoặc kẹt I/O, hàng đợi tuần tự sẽ bị tắc nghẽn hoàn toàn.
  - Các job có `workdir` khác tới giờ chạy (`_submit_with_guard`) sẽ bị chặn hoặc bỏ qua. Hậu quả là các khung giờ chạy của runner / watchdog bị **skip hoàn toàn trong im lặng (Blackout Gap)**.
  - **Case study thực tế (2026-11-05):** Job `hourly-stale-post-receipts-reconcile` (ID: `8d6b3c18dd64`) chạy đồng bộ SSH sang Admin bị kéo dài từ 17:20 đến 19:18 (~2h). Toàn bộ `phase9-runner-tiktok-feed`, `feed_session_watchdog`, `follow_session_watchdog`, `reap-dead-owner-locks` đều bị kẹt cứng; khiến Ca 3 Phiên 1 (18:00) bị mất trắng hoàn toàn không kích hoạt được. Chi tiết xem: [Incident Case Study 18h Lockout](references/incident-case-study-18h-sequential-lockout.md).

---

## 2. Quy Tắc Bắt Buộc (Invariants)
1. **CẤM TUYỆT ĐỐI gán tham số `workdir`** cho các cronjob của farm, đặc biệt là:
   - `phase9-runner-tiktok-feed` (`tiktok_runner.py`)
   - `tiktok-feed-session-watchdog` (`feed_session_watchdog.py`)
   - `tiktok-follow-session-watchdog` (`follow_session_watchdog.py`)
   - `reap-dead-owner-locks` (`reap-dead-owner-locks-wrapper.py`)
   - `hourly-stale-post-receipts-reconcile` (`cron_reconcile_stale_receipts.py`)
2. **Kỷ luật đường dẫn tuyệt đối (Absolute Paths):**
   - Mọi script và wrapper chạy qua `no_agent: True` hoặc cron prompt bắt buộc phải dùng đường dẫn tuyệt đối (`D:/Taadaa/...`, `C:/Users/Kibe/...`).
   - Nếu script con cần `cwd` cụ thể, truyền trực tiếp `cwd=...` trong hàm gọi `subprocess.Popen` / `subprocess.run` bên trong code Python của wrapper, không bao giờ dùng `workdir` của cronjob.
3. **Khi `workdir: null`:**
   - Job được phân loại vào `parallel_jobs`, chạy đồng thời trên `parallel_pool` (đa luồng).
   - Đảm bảo độc lập tuyệt đối giữa các tiến trình, không job nào có thể block hay làm trễ/skip job nào.

---

## 3. Quy Trình Rà Soát & Khắc Phục (Triage & Recovery)
Khi phát hiện một job cron tự nhiên không chạy đúng mốc giờ hoặc biến mất khỏi output:
1. **Kiểm tra ngay danh sách job còn dính `workdir`:**
   ```python
   import json
   d = json.load(open(r"C:\Users\Kibe\AppData\Local\hermes\cron\jobs.json", "r", encoding="utf-8"))
   bad = [j["name"] for j in d["jobs"] if (j.get("workdir") or "").strip()]
   print("Jobs with workdir:", bad)
   ```
2. **Gỡ bỏ `workdir`:**
   - Dùng tool: `cronjob(action='update', job_id=..., workdir='')`.
3. **Đồng bộ 3 tầng SSOT:**
   - Chạy: `python D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_sync_watchdog.py --force`.
   - Xác nhận `jobs.json` ở cả 3 nơi (`%LOCALAPPDATA%`, `D:/Taadaa/Hermes/deploy/...`, `D:/OneDrive/...`) đều sạch `workdir`.
