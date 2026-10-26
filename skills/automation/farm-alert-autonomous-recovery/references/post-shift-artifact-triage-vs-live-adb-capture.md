# Post-Shift Artifact Triage vs Live ADB Capture Invariant

> Context: Incident Auto-Heal & Watchdog Emitter (`incident_emitter.py`, `feed_session_watchdog.py`, `incident_auto_harness.py`).

## 1. Bản chất sự cố lệch pha thời gian (Temporal Desync Pitfall)
- **Triệu chứng:** Hàng loạt vé sự cố từ watchdog ca chạy bị Gate 0 Telemetry phạt `BLOCKED` (score < 2) hoặc Planner Gate 1 timeout (> 300s) vì nhận stack trace rác (`NoneType: None\n`).
- **Nguyên nhân gốc rễ:** 
  1. Ca nuôi/upload đã hoàn thành trước đó (ví dụ 20:28), máy đã dọn dẹp app về `LauncherActivity` (Home screen) rồi tắt màn hình đi ngủ (`Screen: OFF Sleep/Dozing`).
  2. Watchdog quét định kỳ sau ca (21:00, 21:15) phát hiện máy lỗi từ summary tổng kết, sau đó gọi `incident_emitter.emit_if_needed()`.
  3. `incident_emitter` cũ tự ý gọi `adb screencap -p` vào cái máy đang ngủ -> chụp ra ảnh đen xì (RGB 0,0,0), WinRT OCR rỗng, ATX dump rỗng -> Gate 0 Telemetry bị chặn oan.
  4. Bỏ qua toàn bộ folder bằng chứng ca chạy thực tế của máy, không trích xuất stack trace / log thật khiến Planner nhận prompt mù.

## 2. Invariant điều tra hiện trường (Human-like Investigation Rule)
Khi điều tra sự cố sau ca chạy (post-shift watchdog), **tuyệt đối không được chụp sống (live ADB capture)** vào máy đã kết thúc ca. Hành vi điều tra chuẩn xác bắt buộc phải mô phỏng y hệt thao tác của con người:

1. **Định vị chính xác thư mục ca chạy của máy (Machine Run Directory):**
   - Từ `run_dir` của watchdog (vd: `D:/Taadaa/runtime/kibe/live/<date>/<shift_run>/machines/machine_<M>/<timestamp>/`).
2. **Khai thác trực tiếp từ Artifacts ca chạy (Evidence Salvage):**
   - **Stack Trace & Error Context:** Đọc trực tiếp từ `execution.log`, `log.jsonl`, `summary.txt`, `upload_result.json` hoặc `follow_result.json`. Trích xuất exception thật, tên hàm, dòng lỗi thay vì để `NoneType: None\n`.
   - **Ảnh hiện trường lúc xảy ra lỗi (Error-time Screenshots):** Bốc các ảnh artifact đã được runner chụp đúng thời điểm xảy ra lỗi trong `artifacts/` (vd: `video-pick-create-entry-before.png`, `soft-reboot-*.png`, `failed_*.png`, hoặc `media-push-*.png`).
   - **Cấu trúc UI lúc xảy ra lỗi:** Lấy file dump XML có sẵn trong run folder / artifacts (vd: `popup_before.xml`) thay vì cố gọi `atx dumpUI` trên màn hình khóa.
3. **Chỉ dùng Live ADB Capture khi nào?**
   - CHỈ ĐƯỢC PHÉP gọi `adb exec-out screencap` và `atx dumpUI` khi máy đang trong ca chạy chủ động (`status == "running"` / active live debug).
   - Nếu ca chạy đã kết thúc (`completed`, `manual-needed`, `failed`, `timeout`), 100% telemetry và bằng chứng phải được đào từ run artifacts.
