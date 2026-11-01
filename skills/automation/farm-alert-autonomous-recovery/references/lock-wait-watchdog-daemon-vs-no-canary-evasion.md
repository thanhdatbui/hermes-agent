# Anti-Passivity: Lock-Wait Watchdog Daemon vs No-Canary Evasion

## 1. Bản Chất Bại Liệt / Trốn Việc Khi Gặp Lock Thiết Bị
Khi Coordinator nhận nhiệm vụ sửa script hoặc xử lý lỗi farm mà máy mục tiêu đang bị active lock (do ca nuôi chính, feed session hoặc worker khác đang chiếm giữ):
- **Hành vi sai phạm nghiêm trọng (Evasion / Performative Reporting):**
  - Tự ý áp dụng cờ `--no-canary` kèm lý do ngụy biện ("bảo vệ ca nuôi", "máy đang bận ca chiều").
  - Phân tích nguyên nhân trên lý thuyết, báo cáo lý thuyết suông rồi ngồi thụ động chờ ca sau tự chạy.
  - Hứa hẹn mồm "sẽ canh" nhưng không kích hoạt bất kỳ tiến trình theo dõi nào ở turn hiện tại.
- **Hành vi đúng (Mandatory Active Watchdog):**
  - **CẤM TUYỆT ĐỐI bỏ qua Canary:** Cờ `--no-canary` bị vô hiệu hóa cơ học đối với repo Farm/Device.
  - **Khởi động Watchdog Daemon ngay tại turn:** Khi máy mục tiêu bị lock, BẮT BUỘC dựng ngay script poller/daemon chạy nền (`terminal(background=True)`) để canh chừng thiết bị theo chu kỳ (ví dụ mỗi 60-120s).
  - **Tự động kích hoạt khi nhả lock:** Ngay khi máy mục tiêu nhả lock (không còn trong `.codex/device-locks`), daemon lập tức gọi runner thi công/kiểm chứng, lưu kết quả vào state file và dừng khi toàn bộ máy mục tiêu hoàn tất.

## 2. Mô Thức Thiết Kế Watchdog Poller O(1) Cho Máy Bị Lock

### Cấu trúc Poller Daemon (`run_watchdog_rerun_daemon.py`):
```python
import time
import subprocess
import sys

print("[DAEMON] Watchdog rerun daemon started")
sys.stdout.flush()

while True:
    try:
        res = subprocess.run(
            [sys.executable, "D:/Taadaa/tools/watchdog_rerun_failed_machines.py"],
            capture_output=True, text=True, timeout=600
        )
        if res.stdout:
            sys.stdout.write(res.stdout)
            sys.stdout.flush()
        if "ALL_COMPLETED" in res.stdout:
            print("[DAEMON] All machines completed successfully. Exiting.")
            sys.stdout.flush()
            break
    except Exception as e:
        print("[DAEMON] Exception:", e)
        sys.stdout.flush()
    time.sleep(120)
```

### Kỷ luật kiểm tra lock liên cụm (Kibe Local & Admin Remote):
- Kiểm tra lock remote qua `admin_ssh.py`:
  `python -c "import glob; print(len(glob.glob('C:/Users/Admin/.codex/device-locks/*{m}*.lock.json')))"`
- Kiểm tra lock local:
  `glob.glob('C:/Users/Kibe/.codex/device-locks/*{m}*.lock.json')`
- Nếu còn lock: ghi log `[INFO] May {m} dang ban (active lock). Bo qua luot nay, cho lan sau.` và sleep.
- Nếu hết lock: kích hoạt kiểm chứng ngay lập tức.
