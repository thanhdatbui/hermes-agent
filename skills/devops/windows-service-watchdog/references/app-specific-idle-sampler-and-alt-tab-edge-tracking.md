# App-Specific Idle Watchdog: 1Hz Continuous Sampler with PID Tree & Alt-Tab Edge Tracking

## Bối cảnh & Vấn đề (The Under-Sampling Trap)
Khi người dùng yêu cầu: *"Tự động đóng ứng dụng (ví dụ Tiểu Vi / Xiaowei chiếu màn hình Android) khi KHÔNG thao tác trong ứng dụng đó quá X phút (ví dụ 20 phút), nhưng nếu vừa thao tác trong ứng dụng rồi Alt-Tab ra ngoài làm việc khác thì phải đủ đúng 20 phút kể từ lúc rời đi mới được đóng, cấm đóng sớm sau 3 phút."*

### Tại sao cơ chế Polling thưa (2 phút / lần) luôn thất bại?
1. **Bẫy lấy mẫu thưa (Under-sampling):** Người dùng thao tác trong app (click vài cái -> ngồi quan sát 1-2 phút). Xác suất một lần click rơi đúng tích tắc cron 2 phút thức dậy là rất thấp.
2. **Kẹt mốc `last_active` cũ:** Nếu mốc không được làm mới, `last_active` bị kẹt ở thời điểm mở app (hoặc lần click từ 15-18 phút trước).
3. **Alt-Tab bị trảm tức thì:** Khi người dùng vừa Alt-Tab sang app khác được 3 phút, cron thức dậy thấy `in_app == False`, lấy `now - last_active` (đã dồn toa từ trước) vượt quá ngưỡng -> lập tức phát lệnh `taskkill` oan uổng!
4. **Nhận diện sai cửa sổ:** Khớp tiêu đề cửa sổ (title string) hoặc tên process chung (`msedgewebview2`) bị trượt khi người dùng click vào dialog con, floating mirror, hoặc bị false-positive từ các app WebView2 khác (Teams, Slack).

---

## Kiến trúc chuẩn: 2 Tầng (Sampler 1Hz + Watchdog 2m)

### 1. Tầng 1: Continuous 1Hz Sampler (Chạy ngầm trong phiên người dùng)
- **Chu kỳ lấy mẫu:** 1.0 giây (`time.sleep(1.0)`).
- **Nhận diện bằng Cây PID (PID Tree):** Dùng `psutil` tìm PID của process chính (`xiaowei.exe`) và **toàn bộ process con** đệ quy của nó. Bất kể tiêu đề cửa sổ là gì hay click vào ô stream nào, chỉ cần PID thuộc cây này đều là `in_app = True`.
- **Bắt góc chuyển đổi Alt-Tab (Edge Triggering):**
  - Khi đang trong app và có input mới (`GetLastInputInfo` dwTime thay đổi) -> `last_active = now`.
  - **ĐẶC BIỆT QUAN TRỌNG:** Khi người dùng chuyển vào hoặc chuyển ra khỏi app (`in_app != prev_in_app`) -> lập tức neo `last_active = now`. Điều này đảm bảo giây phút Alt-Tab rời app chính là mốc bắt đầu đếm ngược!
- **State File nguyên tử (Atomic Write):** Ghi heartbeat và `last_active` vào file JSON tạm rồi `os.replace` vào file đích (`xiaowei_activity.json`).

### 2. Tầng 2: Periodic Watchdog (Cron 2 phút) & Nguyên tắc Fail-Safe
- **Fail-Safe (Cấm đóng mù):** Nếu sampler chưa chạy, state file không tồn tại, hoặc heartbeat bị cũ (>15s do sampler bị kill/treo) -> Watchdog **TUYỆT ĐỐI KHÔNG ĐƯỢC ĐÓNG APP**. Watchdog sẽ tự động spawn lại sampler và exit 0.
- **Xác thực 2 pha (TOCTOU Verification):** Khi `idle_seconds >= IDLE_THRESHOLD`:
  - Watchdog sleep 5 giây.
  - Đọc lại state lần thứ 2. Chỉ khi cả 2 lần đều vượt ngưỡng mới thực thi `taskkill`.
- **Tự động thoát khi hết việc:** Khi ứng dụng chính không còn chạy, sampler tự động kết thúc vòng lặp để giải phóng tài nguyên.

---

## Code Reference Contract (Python Windows)

```python
import ctypes, ctypes.wintypes as wt, json, os, time, psutil

STATE_V2 = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "hermes", "state", "xiaowei_activity.json")
HEARTBEAT_MAX_AGE_S = 15
IDLE_THRESHOLD_SECONDS = max(900, min(7200, int(os.environ.get("XIAOWEI_IDLE_THRESHOLD", "1200")))) # 20m

class LII(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

def last_input_tick() -> int | None:
    lii = LII()
    lii.cbSize = ctypes.sizeof(LII)
    return lii.dwTime if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)) else None

def get_app_pid_tree(proc_name: str = "xiaowei.exe") -> tuple[set[int], float | None]:
    pids, started = set(), None
    for p in psutil.process_iter(["name"]):
        if (p.info["name"] or "").lower() == proc_name.lower():
            pids.add(p.pid)
            try:
                started = min(started or float("inf"), p.create_time())
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            try:
                pids.update(c.pid for c in p.children(recursive=True))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    return pids, started

def foreground_root_pid() -> int | None:
    u32 = ctypes.windll.user32
    hwnd = u32.GetForegroundWindow()
    if not hwnd:
        return None
    root = u32.GetAncestor(hwnd, 3) or hwnd  # GA_ROOTOWNER: dialog/popup -> main window
    pid = wt.DWORD()
    u32.GetWindowThreadProcessId(root, ctypes.byref(pid))
    return pid.value if pid.value else None

def evaluate_idle() -> tuple[float | None, str]:
    if not os.path.exists(STATE_V2):
        return None, "SAMPLER_STATE_MISSING"
    try:
        with open(STATE_V2, "r", encoding="utf-8") as f:
            st = json.load(f)
    except Exception:
        return None, "SAMPLER_STATE_CORRUPT"
    now = time.time()
    if now - st.get("heartbeat", 0) > HEARTBEAT_MAX_AGE_S:
        return None, "SAMPLER_STALE"
    anchor = max(st.get("last_active", 0), st.get("xw_started", 0))
    return max(0.0, now - min(anchor, now)), "OK"
```
