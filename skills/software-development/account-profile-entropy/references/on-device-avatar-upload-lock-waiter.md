# On-Device TikTok Avatar Upload Lock Waiter Pattern

## 1. Bối Cảnh & Vấn Đề (User Correction 2026-10-19)
- **Vấn đề**: Khi chuẩn hóa kênh, việc nạp Avatar mới lên máy thật thường bị đụng độ với ca nuôi định kỳ của Farm (`multi-machine-feed-session`, chiếm `machine_<ID>.lock.json`).
- Nếu chạy `run_tiktok_upload_avatar.ps1` trực tiếp lúc máy đang có lock, launcher sẽ ghi nhận trạng thái `SKIPPED_LOCKED` và bỏ qua máy đó.
- Nếu Coordinator tự viết vòng lặp `while True: sleep(...)` trong session chính để chờ máy rảnh, Coordinator sẽ vi phạm nghiêm ngặt **Invariant 4 (CẤM TUYỆT ĐỐI POLLING TIẾN TRÌNH NỀN / EVENT-DRIVEN WAKEUP)** và làm đóng băng phiên làm việc.
- User phản ánh: *"R canh up ava cho 2 acc đó đi"* — Yêu cầu một cơ chế tự động theo dõi và tự kích hoạt khi máy rảnh mà không cần User phải nhắc lại hay Coordinator phải thăm dò thủ công.

---

## 2. Thiết Kế Runner Có Cơ Chế Chờ Lock (`--wait-lock`)

### A. Mã Nguồn Chuẩn (`D:/Taadaa/tools/run_upload_avatar.py`)
```python
import argparse
import os
import subprocess
import sys
import time

SCRIPT_PATH = r"D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1"
HOST_CONFIG_PATH = r"D:\Taadaa\machine-config\kibe.yaml"
DEVICE_LOCK_DIR = r"C:\Users\Kibe\.codex\device-locks"
WAIT_LOCK_POLL_SECONDS = 5
WAIT_LOCK_MAX_SECONDS = 900


def wait_for_lock_release(machine: int) -> bool:
    lock_path = os.path.join(DEVICE_LOCK_DIR, f"machine_{machine}.lock.json")
    waited = 0
    while os.path.exists(lock_path):
        if waited >= WAIT_LOCK_MAX_SECONDS:
            return False
        time.sleep(WAIT_LOCK_POLL_SECONDS)
        waited += WAIT_LOCK_POLL_SECONDS
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tik", type=int, required=True)
    parser.add_argument("--machine", type=int, required=True)
    parser.add_argument("--wait-lock", action="store_true", default=False)
    args = parser.parse_args()

    # Chờ lock nhả an toàn trong giới hạn timeout (Fail-closed)
    if args.wait_lock and not wait_for_lock_release(args.machine):
        sys.stderr.write(
            f"machine_{args.machine} still locked after {WAIT_LOCK_MAX_SECONDS}s; upload not started\n"
        )
        return 3

    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", SCRIPT_PATH,
        "-Tik", str(args.tik),
        "-MaxParallel", "1",
        "-HostConfigPath", HOST_CONFIG_PATH,
        "-ForceAvatarMachineList", str(args.machine),
    ]
    result = subprocess.run(cmd, input=b"RUN\r\n", capture_output=True)
    sys.stdout.write(result.stdout.decode("utf-8", errors="replace"))
    sys.stderr.write(result.stderr.decode("utf-8", errors="replace"))
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
```

---

## 3. Quy Trình Kích Hoạt Qua Hermes Coordinator
1. **Khởi chạy tiến trình nền event-driven**:
   ```python
   terminal(
       command=f"python D:/Taadaa/tools/run_upload_avatar.py --tik {tik} --machine {machine} --wait-lock",
       background=True,
       notify_on_complete=True,
       timeout=1200
   )
   ```
2. **Bàn giao và đánh thức**:
   - Coordinator kết thúc lượt trả lời, báo cáo rõ ràng cho User là tiến trình canh lock tự động đã được bật.
   - Khi tiến trình nền hoàn tất, Hermes harness sẽ tự động đánh thức Coordinator với output kết quả thực tế.
3. **Nghiệm thu hình ảnh thực tế (Gate 6)**:
   - Đọc `D:/CodexRuntime/tiktok-video/runs/run_<SERIAL>_<TIMESTAMP>/report.json` xác nhận:
     `"status": "AVATAR_SMOKE_SUCCESS"` và `"avatar_status": "FORCED_REPLACED_VERIFIED"`.
   - Mở ảnh chụp màn hình xác nhận `avatar-uploaded-confirmed.png` bằng WinRT OCR (`run_winrt_ocr.py`).
   - Gửi ảnh bằng chứng `MEDIA:<path>` kèm mô tả chi tiết cho Operator.
