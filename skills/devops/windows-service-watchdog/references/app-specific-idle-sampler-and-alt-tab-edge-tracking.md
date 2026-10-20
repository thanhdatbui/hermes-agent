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
- **State File nguyên tử (Atomic Write):** Ghi heartbeat và `last_active` vào file JSON tạm (`.tmp`) rồi `os.replace` vào file đích (`xiaowei_activity.json`).

### 2. Tầng 2: Periodic Watchdog (Cron 2 phút) & Nguyên tắc Fail-Safe
- **Fail-Safe (Cấm đóng mù):** Nếu sampler chưa chạy, state file không tồn tại, hoặc heartbeat bị cũ (>15s do sampler bị kill/treo) -> Watchdog **TUYỆT ĐỐI KHÔNG ĐƯỢC ĐÓNG APP**. Watchdog sẽ tự động spawn lại sampler và exit 0.
- **Xác thực 2 pha (TOCTOU Verification):** Khi `idle_seconds >= IDLE_THRESHOLD`:
  - Watchdog sleep 5 giây.
  - Đọc lại state lần thứ 2. Chỉ khi cả 2 lần đều vượt ngưỡng mới thực thi `taskkill`.
- **Tự động thoát khi hết việc:** Khi ứng dụng chính không còn chạy (không còn PID trong cây), sampler tự động kết thúc sau N ticks trống (ví dụ 5 ticks) để giải phóng tài nguyên.

---

## 5 Cạm Bẫy Vận Hành & Khắc Phục Sâu (Production Edge Cases)

1. **Khởi tạo lại trạng thái khi Sampler Restart (State Preservation across Restarts):**
   - *Cạm bẫy:* Khi sampler bị crash hoặc watchdog khởi động lại sampler, nếu gán `last_active = now`, toàn bộ thời gian idle mà ứng dụng đã tích lũy từ trước sẽ bị xóa sạch, lùi thời điểm đóng thêm cả một chu kỳ ngưỡng.
   - *Khắc phục:* Khi sampler boot, đọc lại file state cũ: nếu `st.get("xw_started") == started` (cùng một instance ứng dụng) và có `last_active`, kế thừa nguyên vẹn `last_active = st["last_active"]`. Chỉ gán `now` nếu ứng dụng vừa mở mới (`started` thay đổi).
2. **Bẫy False Input ở Tick đầu tiên (`prev_tick is None`):**
   - *Cạm bẫy:* Nếu kiểm tra `new_input = (tick != prev_tick)`, ở tick đầu tiên khi `prev_tick` là `None`, biểu thức luôn trả về `True`. Hậu quả: sampler vừa bật lên sẽ lập tức cập nhật `last_active = now` dù không hề có phím/chuột nào được bấm.
   - *Khắc phục:* Bắt buộc kiểm tra `new_input = (tick is not None and prev_tick is not None and tick != prev_tick)`.
3. **Tranh chấp khởi chạy đa tiến trình Watchdog (Spawn Race Control):**
   - *Cạm bẫy:* Khi 2 chu kỳ cron hoặc script kiểm tra chạy cùng lúc, cả hai cùng thấy heartbeat chưa có và cùng spawn 2 tiến trình sampler độc lập, gây đụng độ ghi đè file state.
   - *Khắc phục:* Trong `ensure_sampler_running()`, quét `psutil.process_iter(['cmdline'])` kiểm tra xem đã có tiến trình nào mang cờ `--sampler` và đúng tên script đang chạy hay chưa, kết hợp file lock hoặc atomic guard trước khi gọi `subprocess.Popen`.
4. **Phục hồi trước lỗi `psutil.Error` tạm thời:**
   - *Cạm bẫy:* Khi hệ thống bận, `psutil` có thể ném `AccessDenied` hoặc `NoSuchProcess` tạm thời giữa chừng. Nếu catch rồi trả về tập PID rỗng, sampler sẽ ngộ nhận app đã tắt và tự kill chính mình sau 5 ticks rỗng.
   - *Khắc phục:* Trả về `None` khi gặp lỗi và giữ nguyên danh sách PID đã biết của tick trước, không tăng biến đếm `empty_ticks`.
5. **Telemetry cảnh báo khi Idle Evaluation bị từ chối:**
   - *Cạm bẫy:* Khi state file bị thiếu hoặc heartbeat bị stale, hàm đánh giá trả về `(None, "SAMPLER_STALE")`. Nếu main chỉ im lặng exit 0 mà không ghi log, điều phối viên không thể phân biệt được ứng dụng đang active hay hệ thống theo dõi đang bị tê liệt.
   - *Khắc phục:* Bắn sự kiện telemetry `log_event("IDLE_EVAL_SKIPPED", level="WARNING", reason=reason)` để harvester/dashboard phát hiện sampler chết.

---

## Code Reference Contract (Python Windows)

```python
import ctypes, ctypes.wintypes as wt, json, os, sys, time, subprocess, psutil

STATE_V2 = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "hermes", "state", "xiaowei_activity.json")
HEARTBEAT_MAX_AGE_S = 15
IDLE_THRESHOLD_SECONDS = max(900, min(7200, int(os.environ.get("XIAOWEI_IDLE_THRESHOLD", "1200")))) # 20m

class LII(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

def last_input_tick() -> int | None:
    lii = LII()
    lii.cbSize = ctypes.sizeof(LII)
    return int(lii.dwTime) if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)) else None

def get_app_pid_tree(proc_name: str = "xiaowei.exe") -> tuple[set[int], float | None] | None:
    pids, started = set(), None
    try:
        for p in psutil.process_iter(["name", "create_time"]):
            if (p.info.get("name") or "").lower() == proc_name.lower():
                pids.add(p.pid)
                ct = p.info.get("create_time")
                if ct is not None and (started is None or ct < started):
                    started = ct
                try:
                    pids.update(c.pid for c in p.children(recursive=True))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        return pids, started
    except psutil.Error:
        return None  # Giữ danh sách PID cũ nếu lỗi tạm thời

def foreground_root_pid() -> int | None:
    u32 = ctypes.windll.user32
    hwnd = u32.GetForegroundWindow()
    if not hwnd:
        return None
    root = u32.GetAncestor(hwnd, 3) or hwnd  # GA_ROOTOWNER: dialog/popup -> main window
    pid = wt.DWORD()
    u32.GetWindowThreadProcessId(root, ctypes.byref(pid))
    return pid.value if pid.value else None

def run_sampler():
    pids: set[int] = set()
    started: float | None = None
    refreshed_at = 0.0
    empty_ticks = 0
    prev_tick: int | None = None
    prev_in: bool | None = None
    
    # 1. Kế thừa state cũ nếu cùng instance
    existing_st = read_sampler_state()
    initial_tree = get_app_pid_tree("xiaowei.exe")
    if initial_tree:
        pids, started = initial_tree
    now = time.time()
    if existing_st and existing_st.get("xw_started") == started and "last_active" in existing_st:
        last_active = existing_st["last_active"]
    else:
        last_active = now

    while True:
        now = time.time()
        if not pids or now - refreshed_at >= 5.0:
            res = get_app_pid_tree("xiaowei.exe")
            if res is not None:
                pids, started = res
                refreshed_at = now
        empty_ticks = 0 if pids else empty_ticks + 1
        fp = foreground_root_pid()
        in_xw = fp is not None and fp in pids
        tick = last_input_tick()
        
        # 2. Chống false input ở tick 1
        new_input = (tick is not None and prev_tick is not None and tick != prev_tick)
        
        # 3. Bắt góc chuyển đổi Alt-Tab (Edge Trigger)
        if (in_xw and new_input) or (prev_in is not None and in_xw != prev_in):
            last_active = now
        prev_tick, prev_in = tick, in_xw
        
        write_sampler_state({
            "v": 2, "heartbeat": now, "last_active": last_active,
            "xw_started": started, "in_xw": in_xw, "fg_ok": fp is not None
        })
        if empty_ticks >= 5:
            return
        time.sleep(1.0)
```
