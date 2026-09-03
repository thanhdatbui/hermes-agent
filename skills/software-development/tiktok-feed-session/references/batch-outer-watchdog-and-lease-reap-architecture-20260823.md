# Batch Hard Outer Watchdog & Cron Lease Auto-Reap Architecture (2026-08-23)

## 1. Bản chất sự cố Cron Feed bị treo / "Already Running — Skipping"

Khi vận hành farm quy mô lớn (74+ máy) qua Hermes Cron (`phase9-runner-tiktok-feed` mỗi 15 phút):
- **Hiện tượng:** Sau ca chiều/tối, Hermes Cron liên tục báo `Job 'phase9-runner-tiktok-feed' already running — skipping` trong log `agent.log`, không có batch mới nào được kích hoạt suốt nhiều giờ.
- **Root Cause cốt lõi:**
  1. Một hoặc vài thiết bị Android S7 bị kẹt cứng (deadlock) trong các hàm socket ADB/ATX JSON-RPC cấp thấp hoặc vòng lặp wait driver khiến tiến trình worker con không thể thoát.
  2. Ở tầng Flow `multi_machine_feed_session.py`, `ThreadPoolExecutor` gom kết quả qua `as_completed(futures)` và gọi `future.result()`. Do hàm này chờ vô hạn (blocking indefinite wait) cho đến khi toàn bộ futures hoàn tất, chỉ cần **1 máy bị kẹt** là toàn bộ tiến trình batch cha (PowerShell / Python) bị treo vĩnh viễn.
  3. Ở tầng Cron Runner `tiktok_runner.py`, cơ chế `_lease_alive()` đọc file lease `runner-live-lease/<day>.json` (có hạn mặc định 4 giờ). Vì PID tiến trình batch cha vẫn còn sống trong danh sách process của Windows, runner liên tục trả về `0` (no-op), khiến toàn bộ các ca cron sau bị chặn đứng.

---

## 2. Kiến trúc giải pháp 2 Lớp (Two-Tier Guard)

### Lớp 1: Hard Outer Watchdog ở tầng ThreadPoolExecutor (`multi_machine_feed_session.py`)
Thay thế hoàn toàn cơ chế `as_completed(futures)` chờ vô hạn bằng vòng lặp polling thời gian thực:
```python
futures: dict[Any, tuple[MachineAccount, Any, float]] = {}
for account, delay_ms in zip(reserved_accounts, launch_plan.delays_ms):
    ...
    future = executor.submit(_run_child, ctx, account, resolved_adb or fallback_adb, reservation)
    futures[future] = (account, reservation, time.monotonic())

worker_hard_timeout = float(
    ctx.config.get("_device_hard_timeout_seconds")
    or (float(ctx.config.get("_device_timeout_seconds") or DEFAULT_DEVICE_TIMEOUT_SECONDS) + 300.0)
)
pending_futures = set(futures.keys())
while pending_futures:
    # 1. Bounded wait 5s cho các máy hoàn tất bình thường
    done_batch, _ = wait(pending_futures, timeout=5.0, return_when=FIRST_COMPLETED)
    for future in list(done_batch):
        pending_futures.remove(future)
        ... # xử lý result bình thường

    # 2. Quét hard timeout cho các máy bị deadlock ADB/ATX
    now_mono = time.monotonic()
    timed_out_futures = [
        f for f in list(pending_futures)
        if (now_mono - futures[f][2]) > worker_hard_timeout
    ]
    for future in timed_out_futures:
        pending_futures.remove(future)
        account, reservation, start_mono = futures[future]
        elapsed_m = round((now_mono - start_mono) / 60.0, 1)
        err_msg = f"hard outer watchdog timeout exceeded ({elapsed_m}m > {round(worker_hard_timeout/60.0, 1)}m)"
        reservation.set_status("handoff")
        child = _write_fallback_child_artifacts(
            ctx,
            account,
            resolved_adb or fallback_adb,
            message=f"[WATCHDOG] machine {account.machine} aborted: {err_msg}",
            stop_reason=err_msg,
            final_status="failed",
        )
        rows.append(child.as_dict())
        ... # log & gửi alert Farm Alerts
```
**Lợi ích:** Dù thiết bị có bị đơ phần cứng hay treo ADB socket, máy đó sẽ bị ngắt sau đúng trần hard timeout (30 phút), xuất đầy đủ fallback artifact và giải phóng để tiến trình cha kết thúc trơn tru.

---

### Lớp 2: Auto-Reap Stale Lease ở tầng Cron Runner (`tiktok_runner.py`)
Nâng cấp hàm `_lease_alive(env, day, now)` để tự động giải phóng lease khi có dấu hiệu kẹt quá lâu:
1. **Max Shift Lifetime:** Một ca feed tối đa chỉ kéo dài ~60–80 phút. Nếu `started_at` của lease cũ vượt quá **90 phút (5400s)**, runner coi lease đã stale và tự động gọi `lease_path.unlink(missing_ok=True)`.
2. **Dead PID Cleanup:** Nếu PID trong lease không còn tồn tại trong OS (`os.kill(pid, 0)` quăng lỗi) hoặc PID âm/không hợp lệ, lập tức xóa lease file.

---

## 3. Quy tắc vận hành & Triage khi nghi ngờ Cron Treo
1. **Kiểm tra process sống:**
   ```powershell
   Get-Process powershell,python | Where-Object { $_.CommandLine -like "*run-feed-session*" }
   ```
2. **Kiểm tra file lease:**
   ```text
   D:\Taadaa\runtime\kibe\cron-state\runner-live-lease\<YYYY-MM-DD>.json
   ```
3. **Kiểm tra log scheduler:**
   Đọc `C:\Users\Kibe\AppData\Local\hermes\logs\agent.log` để xác nhận `already running` hay scheduler vẫn đang tick bình thường.
4. **Không bao giờ xóa bừa bãi khi batch mới bắt đầu:** Chỉ xóa lease khi thời gian start đã > 90 phút hoặc đã xác minh process ghi trong lease đã chết.
