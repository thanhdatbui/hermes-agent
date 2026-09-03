# TOÀN BỘ KIẾN TRÚC PREFLIGHT LOCK GATE, VPN GATE & WATCHDOG TOÀN FARM (20/08/2026)

## 1. BỐI CẢNH & NGUYÊN NHÂN SỰ CỐ
- **Sự cố tranh chấp Máy 44 (22:40 ngày 20/08/2026)**: Máy 44 đang được điều khiển chạy Hotmail login (chọn tài khoản Outlook). Cùng lúc đó ca cron nuôi acc 22:30 (`row-2-223032`) kích hoạt, quét thư mục lock không thấy lock máy 44 $\rightarrow$ mở TikTok đè lên app Outlook $\rightarrow$ mất focus và dừng phiên giữ hiện trường.
- **Nguyên nhân cốt lõi**: Cơ chế lock và VPN preflight chưa được code-enforce đồng bộ ở tất cả entrypoint của các repo consumer (`tiktok-follow`, `tiktok-log-in`, `tiktok-add-bao-mat-f2a`, `Tiktok_Reg`...).

---

## 2. QUY TRÌNH PREFLIGHT 3 BƯỚC BẮT BUỘC TOÀN FARM

Mọi script/flow trên mọi repo automation (`D:\Taadaa\...`) bắt buộc tuân thủ thứ tự preflight sau trước khi thực hiện bất kỳ tương tác ADB/UI nào trên thiết bị:

```text
Khởi chạy Task
   │
   ▼
[1. DEVICE LOCK GATE] ──(Có lock active)──► BÁO CÁO & SAFE-SKIP NGAY (CẤM đụng ADB / CẤM mở app)
   │ (Máy hoàn toàn rảnh)
   ▼
[2. VPN GATE] ─────────(Mất VPN / Proxy chết)──► Chặn đứng, dừng an toàn (Fail-closed)
   │ (VPN tun0 UP & Live IP verified)
   ▼
[3. LOCK PORTRAIT] ────► Khóa kép xoay dọc màn hình (Dual-layer lock)
   │
   ▼
[4. CHẠY TASK CHÍNH]
```

### Chi tiết từng Gate:

1. **Bước 1 — Device Lock Gate (`acquire_device_lock(user_authorized=False)` / `check_device_lock_preflight`):**
   - Kiểm tra `machine_<STT>.lock.json` và `serial_<SERIAL>.lock.json` trong `~/.codex/device-locks/`.
   - Nếu có lock active với `status in ["running", "blocked", "queued"]`:
     - BẮT BUỘC raise `DeviceLockNeedsUserDecision` / trả về mã chặn (`exit 2`).
     - Ghi nhận lý do rõ ràng: `BLOCKED: [device-lock] máy XX đang được User khóa bởi <Project> (PID <pid>) — safe-skip, KHÔNG can thiệp`.
     - Tuyệt đối không can thiệp, không tự takeover, không auto-recovery.

2. **Bước 2 — VPN Gate (`require_android_vpn(adb, required=required)`):**
   - Đọc mapping host qua `resolve_proxy_mapping_path()` (fail-closed, không hardcode path).
   - Kiểm tra `serial_is_mapped_in_workbook(...)`:
     - Nếu máy có proxy gán trong workbook $\rightarrow$ `required=True`: bắt buộc VPN `tun0` UP + ViChanger `GET_IP` trả IP thật hợp lệ. Nếu mất VPN $\rightarrow$ Chặn đứng (`ConsumerPreflightError`), không bao giờ lướt lộ IP thật.
     - Nếu máy không có proxy (Direct IP / unmapped bypass) $\rightarrow$ `required=False`: pass through an toàn.

3. **Bước 3 — Lock Portrait (`prepare_device` / `lock_portrait_rotation`):**
   - Khóa kép xoay màn hình 0 độ portrait (cả `settings put` lẫn `content insert`).

---

## 3. DANH SÁCH ENTRYPOINT ĐÃ ENFORCE Ở TỪNG REPO

| Repo | Branch | File Entrypoint đã tích hợp | Test Status |
|---|---|---|---|
| **`automation-core`** | `master` | `src/automation_core/preflight.py` (`check_device_lock_preflight`) | 594/594 passed |
| **`tiktok-follow`** | `master` | `follow_runner/run_follow.py` (CLI entrypoint gate) | 106/106 passed |
| **`tiktok-log-in`** | `main` | `account_inventory.py`, `password_change.py`, `collect_apk_evidence.py`, `executor.py` | 190/190 passed |
| **`tiktok-add-bao-mat-f2a`** | `main` | `run_capture_phase_a.py`, `run_capture_phase_b.py`, `run_phase_b_pilot.py`, `run_batch_live_2fa.py` | 173/173 passed |
| **`Tiktok_Reg`** | `main` | `social_reg_v1.py`, `tiktok_login_v1.py`, `tiktok_login_live_email_v1.py`, `tiktok_reg_live_email_v1.py` | Verified & Passed |
| **`register gmail`** | `main` | `gmail_reg_v10.py`, `guarded_device_reboot.py` | Verified & Passed |
| **`Hotmail`** | `master` | `flows/hotmail_login.py`, `flows/hotmail_change_info.py`, `flows/login_outlook_one_machine.py` | Verified & Passed |
| **`add mail khoi phuc`** | `main` | `run_add_recovery.py`, `recovery_scheduler.py` | Verified & Passed |
| **`gan-proxy`** | `main` | `scripts/gan_proxy_fleet.py`, `scripts/vi_changer_runner.py` | 77/77 passed |
| **`Tiktok-video`** | `main` | `scripts/tiktok_workflow/run_post.py`, `scripts/tiktok_workflow/state_machine.py` | Verified & Passed |
| **`tiktok-luot nuoi acc`** | `master` | `python_runner/run_tiktok.py`, `flows/multi_machine_feed_session.py` | Verified & Passed |

---

## 4. HERMES CRON WATCHDOG NHẮC LOCK (CHỐNG QUÊN)
- **Script**: `D:\Taadaa\tools\watch_device_locks.py` $\leftrightarrow$ `~/.hermes/scripts/watch_device_locks.py`.
- **Cron Job**: `device-locks-watchdog` (`job_id: 71c2a1b6268c`), chu kỳ `every 2h`.
- **Kênh nhận tin**: Nhóm riêng **Report máy lock** (`chat_id: -5518578446`).
- **Nội dung**: Quét thư mục `~/.codex/device-locks/`, tổng hợp danh sách máy đang bị lock (STT, project, PID, thời gian đã lock), cảnh báo máy lock quá hạn $\ge 120$ phút để nhắc user mở khóa kịp thời.

---

## 5. KINH NGHIỆM CODE REVIEW DIFF ĐỘC LẬP (FALLBACK ROUTING)
- Khi gọi 9Router model `plan-review` (combo `gpt-5.6-terra`) gặp hiện tượng socket read timeout trên diff dài:
  - Chuyển sang gọi **`gpt-5.6-sol`** hoặc dùng trực tiếp **`Claude Code CLI (claude -p ...)`** để review diff độc lập.
  - Luôn đảm bảo nhận verdict **`APPROVED`** từ reviewer độc lập trước khi commit và push Git.
