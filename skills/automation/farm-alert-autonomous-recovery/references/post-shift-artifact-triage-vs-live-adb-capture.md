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
   - Từ `run_dir` của watchdog (vd: `D:/Taadaa/runtime/kibe/live/<date>/<shift_run>/`).
   - Duyệt có giới hạn (bounded `os.scandir`, depth <= 3, CẤM `os.walk`/`glob(recursive=True)` để chống vi phạm GuardGate) tìm thư mục máy: `machine_<M>` hoặc `machines/machine_<M>/<run_timestamp>/`.
2. **Khai thác trực tiếp từ Artifacts ca chạy (Evidence Salvage):**
   - **Stack Trace & Error Context:**
     - Đọc `summary.txt`: trích xuất `stop_reason` hoặc `reason`, tail 4000 ký tự nạp vào `log_tail`.
     - Đọc `upload_result.json`: trích xuất `reason`, `exit_code`, `stdout_tail`, và tìm đường dẫn `report.json` của CodexRuntime (`D:\CodexRuntime\tiktok-video\runs\...`).
     - Đọc `execution.log` trong CodexRuntime: trích xuất 150 dòng cuối cùng.
   - **Ảnh hiện trường lúc xảy ra lỗi (Error-time Screenshots):**
     - Trong `summary.txt`: quét các dòng `manual-needed` hoặc `fail` để lấy đường dẫn artifact directory (chứa `screen.png` thật chụp đúng lúc popup/lỗi xuất hiện).
     - Trong CodexRuntime run dir: lấy các file ảnh lỗi được chụp lúc sự cố (`video-pick-create-entry-before.png`, `soft-reboot-*.png`, `*failure*.png`, `*recaptured*.png`).
   - **Cấu trúc UI lúc xảy ra lỗi (UI XML Dump):**
     - Lấy file `ui.xml` trong thư mục artifact hoặc `popup_before.xml` trong Codex run dir.
   - **Thị giác OCR trên Bằng chứng thật:**
     - Chạy `winrt_ocr` trực tiếp trên bức ảnh hiện trường thật lấy từ artifacts (ví dụ đọc được text popup bên thứ 3 "Bạn đang truy cập nội dung...").
3. **Chỉ dùng Live ADB Capture khi nào?**
   - CHỈ ĐƯỢC PHÉP gọi `adb exec-out screencap` và `atx dumpUI` khi máy đang trong ca chạy chủ động (`status == "running"` / active live debug).
   - Nếu ca chạy đã kết thúc (`completed`, `manual-needed`, `failed`, `timeout`), 100% telemetry và bằng chứng phải được đào từ run artifacts. Tuyệt đối không gọi ADB chụp sống vào máy đang ngủ.

## 3. Kiến Trúc Triển Khai trong Mã Nguồn
- **`incident_emitter.py`:**
  - Hàm `extract_machine_run_artifacts(run_dir, machine_id, upload_info=None)`: Duyệt có giới hạn gom đủ 4 thành phần: `screenshot`, `xml_dump`, `log_tail`, `stack_trace`.
  - Hàm `collect_telemetry(..., run_dir=None, artifacts=None)`: Nếu `artifacts` hợp lệ, nạp trực tiếp screenshot/xml vào envelope, chạy `winrt_ocr` trên ảnh artifact, gán `atx_status="run_artifact"`, bỏ qua hoàn toàn lệnh ADB.
  - Hàm `emit_if_needed(..., run_dir=None)`: Nhận `run_dir` từ watchdog, tự động nạp stack_trace và telemetry thật.
- **`feed_session_watchdog.py`:**
  - Tại 3 vị trí emit (Feed, Follow, Upload), truyền `run_dir = os.path.join(date_live, sorted_run_names[-1])`.
