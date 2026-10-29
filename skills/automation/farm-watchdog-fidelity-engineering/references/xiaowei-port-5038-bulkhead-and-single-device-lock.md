# XiaoWei Port 5038 vs Fleet Bulkhead Invariant (Single-Device Lock Isolation)

## 1. Context & Incident History
On Taadaa Farm, the operator regularly uses XiaoWei (Tiểu Vi - `xiaowei.exe`) for manual device control tasks, such as placing TikTok Shop orders, inspecting apps, or capturing tracking codes (e.g. Machine 40).
XiaoWei starts its own ADB server on **Port 5038** (`C:\Program Files (x86)\xiaowei\tools\adb.exe -P 5038`).
In commit `b88415d` (Oct 23, 2026), an over-engineered preflight check was introduced into `run-feed-session.ps1`:
```powershell
if (-not (Clear-XiaoWeiPort5038)) {
    throw "PREFLIGHT_PORT_5038_BLOCKED: Port 5038 is occupied. XiaoWei ADB must be stopped before starting feed session."
}
```

### The Failure Trap: Fleet-Wide Starvation on Single-Device Interaction
When the operator actively placed orders on 1 locked machine (e.g. Machine 40):
1. `Clear-XiaoWeiPort5038` detected port 5038 listening.
2. It attempted `adb -P 5038 kill-server`, but `xiaowei.exe` was active and holding the socket.
3. The script threw `PREFLIGHT_PORT_5038_BLOCKED` and aborted immediately with exit code 1.
4. **All 79 healthy machines were aborted and starved of nurture for entire shifts**, even though the operator only interacted with 1 device!
5. Watchdogs checking local outputs saw no run folder for today and went completely blind.

---

## 2. Technical Ground Truth: Port 5037 vs Port 5038 USB Concurrency
- On Windows USB, ADB daemons claim interface handles per device serial.
- **Port 5037** (standard automation ADB) and **Port 5038** (XiaoWei ADB) operate concurrently across separate USB endpoints without latency penalties. Live probe (`inspect_machine.py`) showed 0.12s latency on Machine 1 and 2 via port 5037 while XiaoWei was actively running on port 5038.
- Device collision only occurs if both daemons simultaneously attempt shell commands on the **exact same device serial**.

---

## 3. Invariants & Rules

### Rule 1: Anti-Fleet-Abort (Bulkhead Isolation)
- CẤM TUYỆT ĐỐI runner ném exception (`throw`) làm sập toàn bộ ca chạy của 80 máy khi phát hiện XiaoWei đang mở.
- Khế ước xử lý:
  * Nếu port 5038 có listener và `xiaowei.exe` đang chạy: Ghi log `[PREFLIGHT_DIAGNOSTIC] xiaowei_active=True`, giữ nguyên tiến trình cho operator.
  * Nếu port 5038 có listener nhưng `xiaowei.exe` KHÔNG chạy (zombie socket): kill `adb.exe -P 5038` để dọn rác.
  * Trong mọi trường hợp, tiếp tục thực thi feed session cho các máy khả dụng.

### Rule 2: Single-Device JIT Lock Protection
- Máy operator đang dùng (ví dụ Máy 40 đặt hàng) bắt buộc có JIT lock file:
  `%USERPROFILE%\.codex\device-locks\machine_<M>.lock.json`
- `run_tiktok.py` và `multi_machine_feed_session.py` tự động nhận diện lock và ghi nhận `is_device_locked_skip = True`, bỏ qua đúng 1 máy đó.
- 79 máy còn lại được tự do lướt feed, thả tim, follow và upload video bình thường.
