# Follow-Released-Daily-Cooldown Semantics & Device-Lock Watchdog Triage

## 1. Bản chất của `follow-released-daily-cooldown`

### Định nghĩa trong Code (`multi_machine_feed_session.py`)
Khi feed runner chuẩn bị gọi follow hook cho một nick, nó kiểm tra file `D:/Taadaa/tiktok-follow/runs/state/follow_state_<M>_row_<Row>.json`:
```python
if state_data.get("follow_failed_date") == today_str or (
    state_data.get("follow_failed") and state_data.get("budget_date") == today_str
):
    payload = {
        "machine": account.machine,
        "row": account.account_row_index,
        "status": "skipped",
        "reason": "follow-released-daily-cooldown",
        "followed_count": 0,
        "failed": 0,
        "follow_failed": False,
    }
```

### Ý nghĩa thực tế:
- **KHÔNG PHẢI** là đạt chỉ tiêu follow trong ngày rồi nghỉ.
- **LÀ:** Nick đã bị TikTok nhả follow (`FOLLOW_FAILED` — bấm follow xong reload lại profile thì mất follow / TikTok không nhận) ở phiên trước đó, hoặc đang trong chu kỳ **Cooldown 48h** (Streak 1) / 96h (Streak 2) từ ngày trước.
- **Phân loại 2 nhóm máy dính cooldown khi đối soát ca sáng:**
  1. *Nhóm dính nhả trong ngày (Group A):* Đã được mở và chạy ở Phiên 1 sáng (06:00), nhưng bị nhả follow ngay đầu phiên $\rightarrow$ `FollowState.set_follow_failed()` gán cooldown đến `23:59:59` local $\rightarrow$ Phiên 2 và Phiên 3 cùng ngày tự động skip để bảo vệ nick.
  2. *Nhóm dính nhả từ cữ trước với timestamp UTC (Group B):* Bị nhả từ cữ ngày trước (ví dụ 10:39 - 13:05 ngày N-2) với mốc `cooldown_until_at` 48h theo giờ UTC $\rightarrow$ Các phiên sáng sớm (06:00 - 08:30) ngày N chạy trước mốc trưa nên vẫn còn trong thời gian cooldown (`now_utc < cooldown_until_at`), đến Phiên 3 (trưa/chiều) mới chính thức hết hạn và mở lại.
- **Hành vi hệ thống:** Skip hoàn toàn follow hook, không spawn subprocess `follow_runner` để tránh bị TikTok quét spam và shadowban nick; máy vẫn lướt feed và up video bình thường.
- **Hiện tượng log tích lũy lớn (VD: 352 lần/ngày):** Một ca có 3 phiên lướt + runner quét định kỳ mỗi 15 phút. Mỗi lần quét qua nick đang bị cooldown, hệ thống lại ghi 1 record `skipped: follow-released-daily-cooldown`.

---

## 2. Phân tích Số Liệu Follow & Sensitive Skip trong Báo Cáo Watchdog

### Tổng lượt Follow chéo (`Follow chéo: N lượt follow`)
- Số `N` là tổng số lượt follow thành công gom từ **tất cả các máy** đã chạy trong phiên đó.
- Bao gồm cả các máy hoàn thành trọn vẹn quota (`Status: OK`) và các máy follow được một phần trước khi bị rate-limit (`Status: FOLLOW_FAILED, follow_failed=True`, ví dụ máy 45 follow được 15 nick rồi mới dính nhả follow $\rightarrow$ 15 lượt vẫn được ghi nhận thành công).

### Phân loại `sensitive-skip-manual_needed`
- Khi tiến trình Feed chính (`multi_machine_feed_session.py`) gặp sự cố dừng khẩn cấp ở trạng thái `manual-needed` (ví dụ: mất kết nối atx-agent uiautomator `ATX_SESSION_UNAVAILABLE` ở bước `profile_preflight`), feed runner không thể xác thực tài khoản an toàn.
- Follow hook kích hoạt fail-closed an toàn: bỏ qua follow với lý do `sensitive-skip-manual_needed`, đồng thời giữ nguyên màn hình và device lock để operator/canary kiểm tra hiện trường.

---

## 3. Phân biệt `skipped-device-locked` vs Lỗi Thật trong Watchdog Alert

### Cơ chế Watchdog (`feed_session_watchdog.py`)
- Watchdog gom tất cả kết quả máy không đạt `success` hoặc `degraded` vào mục `Fail` trên báo cáo Telegram.
- Nếu một batch runner trước đó (ví dụ PID `194680`) đang chạy kéo dài hoặc vướng jitter, các lock file `C:/Users/Kibe/.codex/device-locks/machine_<M>.lock.json` vẫn đang được giữ.
- Lần quét tiếp theo của watchdog/runner sẽ bỏ qua các máy này với lý do `skipped-device-locked`.

### Triage checklist khi thấy Watchdog báo Fail số lượng lớn (20–30+ máy):
1. **Kiểm tra trạng thái lock file và PID:**
   ```python
   import psutil, glob, json
   for lf in glob.glob("C:/Users/Kibe/.codex/device-locks/machine_*.lock.json"):
       d = json.load(open(lf))
       pid = d.get("pid")
       alive = psutil.pid_exists(pid) if pid else False
       print(d.get("machine"), "PID:", pid, "Alive:", alive)
   ```
2. **Phân loại blocker category trong `summary.txt`:**
   - `focus/device issue: skipped-device-locked` $\rightarrow$ Tiến trình trước đang chạy hoặc để lại stale lock, **không phải lỗi nick hay lỗi flow**.
   - `script blocker: blocked-vichanger-vpn` $\rightarrow$ Mất kết nối WiFi / proxy.
   - `failed: ui_dump_error / ATX_SESSION_UNAVAILABLE` $\rightarrow$ Lỗi kết nối thiết bị / crash service uiautomator.
3. **Chờ batch tiếp theo chạy bù:**
   - Khi tiến trình trước kết thúc và nhả lock, runner tick tiếp theo sẽ tự động nhận máy và chạy bù đầy đủ (`status: success`).
