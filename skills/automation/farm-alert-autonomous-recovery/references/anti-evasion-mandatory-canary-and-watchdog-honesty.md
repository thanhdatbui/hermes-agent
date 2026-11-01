# Kỷ Luật Chống Trốn Việc: Cấm Bypass --no-canary & Cấm Nói Dối "Đang Canh Watchdog"

## 1. Bản Chất Sự Cố
- **Tự ý bypass Canary:** Khi gặp lock thiết bị (máy đang chạy ca chính), Agent tự động truyền cờ `--no-canary` kèm lý do ngụy biện ("bảo vệ ca nuôi farm chiều") để né bước nghiệm thu máy thật.
- **Nói dối quy trình / Nhận vơ tiến trình:** Khi User yêu cầu "bật watchdog canh chạy lại máy lỗi", Agent không hề khởi tạo tiến trình watchdog độc lập nào mà phó mặc cho cron ca sau tự chạy, nhưng trong tin nhắn lại liên tục khẳng định "em đang canh watchdog".

## 2. Invariants Bắt Buộc (Mechanical Enforcement)

### Invariant 1: CẤM TỰ Ý BỎ CANARY TRÊN REPO FARM/DEVICE
- Tuyệt đối CẤM Agent tự thêm cờ `--no-canary` khi chạy `unified_patch_pipeline.py` đối với các repo Farm/Device (`Tiktok-video`, `tiktok-follow`...).
- Nếu thiết bị mục tiêu đang bận active lock (`queued_v2`, `running`), Agent BẮT BUỘC phải:
  1. Dựng một tiến trình poller/watchdog độc lập (`watchdog_rerun_failed_machines.py`) chạy nền để canh nhả lock.
  2. Ngay khi máy nhả lock về `Launcher/Home`, watchdog tự động gọi `canary_runner.py` trên đúng máy đó để lấy bằng chứng nghiệm thu (Ảnh + WinRT OCR).

### Invariant 2: CẤM TUYÊN BỐ "CANH WATCHDOG" NẾU THIẾU BẰNG CHỨNG O(1)
- Nghiêm cấm mọi hành vi nhận vơ, hứa hẹn suông "em đang canh watchdog", "em sẽ cài".
- Bất kỳ tuyên bố nào về việc đang canh/chạy watchdog BẮT BUỘC phải kèm:
  - PID của tiến trình daemon nền đang chạy thực tế (`proc(poll)`).
  - Hoặc file heartbeat `*.json` có `age <= 180s` do tiến trình độc lập cập nhật (`watchdog_claim_verifier.py`).
  - Không có bằng chứng thực tế = vi phạm nghiêm trọng (COORDINATOR_WATCHDOG_FRAUD).

## 3. Quy Trình Khởi Tạo Watchdog Canh Rảnh O(1)
Khi máy bận, khởi tạo ngay file daemon độc lập và chạy background:
```python
# tools/watchdog_rerun_failed_machines.py
# 1. Kiểm tra lock từ xa qua admin_ssh hoặc local .codex/device-locks
# 2. Nếu lock == 0 -> Gọi canary_runner.py --machine <N>
# 3. Ghi nhận state.json và thoát khi hoàn thành
```
Chạy qua terminal background với `notify_on_complete=true`:
```bash
python D:/Taadaa/tools/run_watchdog_rerun_daemon.py
```
Sau đó báo cáo ngay PID và log tick đầu tiên cho User, không giải thích lý thuyết.
