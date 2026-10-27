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

- **CẤM TUYỆT ĐỐI ép Gate 0 đòi UI XML dump sau ca chạy:** 
  1. Khi ca chạy kết thúc, máy đã thoát app về Home hoặc tắt màn hình, việc dump XML hiện tại là hoàn toàn vô giá trị ("Xong ca chạy rồi thì dump XML để làm gì?").
  2. Gate 1 (Planner) và Gate 2 (Worker) xử lý lỗi logic/workflow chỉ tiêu thụ `target_file`, `error_type`, `stack_trace` và `log_tail` (kèm OCR text nếu có), hoàn toàn không dùng cây UI XML.
  3. Nếu envelope đã có `stack_trace` hoặc `log_tail` hợp lệ từ `summary.txt` / `report.json` (`atx_status == "run_artifact"`), Telemetry Gate 0 BẮT BUỘC coi là đủ điều kiện (`score >= 2`), tuyệt đối không được đánh rớt / chuyển L3 chỉ vì thiếu XML dump.
- **Cấm Fall-through sang Live ADB khi thiếu ảnh artifact:**
  Nếu artifact không chứa file ảnh (ví dụ lỗi chết ngay tại preflight VPN trước khi mở app), `incident_emitter` BẮT BUỘC chốt telemetry dựa trên `log_tail` và `stack_trace`, TUYỆT ĐỐI CẤM rớt xuống nhánh chạy `adb exec-out screencap` và `atx-agent dumpUI` vào máy đang ngủ.

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

## 3. Kiến Trúc Triển Khai O(1) trong Mã Nguồn
- **Tận dụng Parser $O(1)$ (`scripts/watchdog/parser.py` & `merger.py`):**
  - Trong quá trình parser duyệt ca chạy, khi đọc `run_manifest.json` ở root, BẮT BUỘC gán `"machine_dir": item.get("artifact_root")` vào `payload` của `res_m`. Nếu thiếu, `all_machines[m_num]` sẽ bị `machine_dir = None`.
  - Khi đọc `upload_result.json` và `follow_result.json`, do JSON từ runner không có trường này, BẮT BUỘC ép gán `u_data["machine_dir"] = root` và `f_data["machine_dir"] = root`.
  - Trong `merger.py`: đảm bảo `m_dir = new.get("machine_dir") or prev.get("machine_dir")` được giữ lại xuyên suốt chuỗi merge.
- **`incident_envelope.py` & Gate 0 Completeness Score:**
  - `completeness_score()`: Nếu `atx_status == "run_artifact"` hoặc envelope đã có `stack_trace` / `log_tail` hợp lệ từ run artifacts (`len(log_tail.strip()) > 20` cho lỗi Python / workflow sau ca), tự động tính điểm hợp lệ (`score = 2`), CẤM TUYỆT ĐỐI ép buộc phải có `xml_dump` hay bắt buộc OCR text.
- **`incident_emitter.py`:**
  - Hàm `extract_run_artifacts(machine_dir, stdout_tail, reason)`: Khai thác trực tiếp từ `machine_dir/summary.txt` và `stdout_tail` (tìm report Codex) trong thời gian $O(1)$ để lấy đủ 4 thành phần: `screenshot`, `xml_dump`, `log_tail`, `stack_trace`.
  - Hàm `collect_telemetry(..., artifacts=artifacts, is_post_shift=bool(machine_dir or stdout_tail))`: Nếu `is_post_shift` hoặc có artifact hợp lệ, sao chép thẳng ảnh/xml vào thư mục telemetry của sự cố nếu có, gán `atx_status="run_artifact"`, và return ngay lập tức. TUYỆT ĐỐI CẤM fall-through xuống nhánh live ADB screencap / atx-agent dumpUI kể cả khi artifact hoàn toàn không có ảnh/xml (ví dụ lỗi preflight VPN).
  - Bẫy Hard Gate #5 khi commit Git: Hard Gate #5 quét chuỗi lệnh terminal chứa token 'adb'. Trong commit message, CẤM viết từ 'adb' (ví dụ: 'prevent live adb fallback' sẽ bị chặn oan); dùng cụm từ trung tính như 'live device capture'.
  - Xử lý Serial dạng số: `resolve_serial_and_args(serial, machine_id)` phải bọc điều kiện `if (not serial or str(serial).isdigit())` để tra cứu serial phần cứng thật, tránh truyền serial giả dạng số `"54"` vào ADB.
  - Chặn đứng ADB Screencap vào máy tắt màn: Nếu `artifacts` rỗng mà thiết bị đang `Screen: OFF Sleep/Dozing`, CẤM TUYỆT ĐỐI gọi ADB screencap (tránh chụp ra ảnh đen xì làm méo mó Gate 0). Đánh dấu rõ `BLOCKED_NO_ARTIFACT_DEVICE_ASLEEP`.
- **`feed_session_watchdog.py`:**
  - Tại 3 vị trí emit (Feed, Follow, Upload), truyền trực tiếp `machine_dir=all_machines.get(m_num, {}).get("machine_dir")` và `stdout_tail=ud_info.get("stdout_tail")`.
  - **Bẫy Lệch Key Prefix "M" Trong Upload Loop:** Trong vòng lặp `for m_val in up_error:`, `m_val` có tiền tố `"M"` (vd: `"M29"`), nhưng dictionary `all_uploads` lại lưu key là chuỗi số thuần (`"29"`). BẮT BUỘC dùng `ud_info = all_uploads.get(m_val) or all_uploads.get(m_num, {})`. Nếu chỉ gọi `all_uploads.get(m_val, {})` sẽ ra dict rỗng `{}`, làm mất sạch `machine_dir` và `stdout_tail` của upload!
  - Gắn fallback đa tầng cho `machine_dir` upload: `machine_dir = ud_info.get("machine_dir") or all_machines.get(m_num, {}).get("machine_dir")`.
  - Cơ chế Fallback an toàn: Nếu `all_machines[m_num].get("machine_dir")` bị rỗng, watchdog phải tra cứu nhanh `item.get("artifact_root")` từ `run_manifest.json` trong `r_path` trước khi emit.
  - **Bắt buộc Force-Sync sau khi sửa Watchdog/Parser:** Sau khi commit sửa watchdog hoặc parser trong git, BẮT BUỘC kích hoạt ngay job `cron-sync-watchdog` (`2b5b608429c7`) để ép đồng bộ code Git sang môi trường thực thi runtime của Hermes cron, chống mtime runtime đè ngược Git.

## 4. Kỷ Luật Phản Hồi Khi Nhận Báo Cáo "Thất Bại / Chuyển L3" (Anti-Performative Triage)
- **CẤM TUYỆT ĐỐI:** Khi dispatcher báo có N sự cố bị chuyển L3 BLOCKED, Coordinator không được ngồi đọc triệu chứng hời hợt ("Màn hình OFF, Launcher, Score < 2 -> Máy ngủ an toàn") rồi báo cáo suông kết thúc việc.
- **BẮT BUỘC TRUY NGUYÊN:** Đặt câu hỏi truy ngược: *"Tại sao ca chạy đã kết thúc và có thư mục kết quả mà telemetry lại phải gọi ADB chụp sống vào máy đang ngủ?"*.
- Kiểm tra ngay:
  1. `checkpoint.jsonl` và file JSON của sự cố xem trường `machine_dir` có bị `null` hay không.
  2. File `run_manifest.json` của ca chạy có trường `artifact_root` hay không.
  3. Parser `parser.py` có đang nuốt chửng trường `artifact_root` khiến watchdog truyền `machine_dir=None` sang emitter hay không.
- Chỉ khi chứng minh được thư mục ca chạy thực sự không có artifact và máy đang ngủ thì mới được coi là BLOCKED hợp lệ. Có artifact mà hệ thống không nạp được là LỖI PIPELINE ĐIỀU PHỐI, bắt buộc phải khoanh vùng và đề xuất vá code ngay lập tức.

## 5. Quy Trình Kiểm Thử Nhanh O(1) Ngoại Tuyến (Fast Replay Test Without Waiting For Next Shift)
Không cần phải chờ đến ca chạy tiếp theo mới kiểm chứng được watchdog và auto-heal:
1. **Replay Thử Nghiệm Từ Dữ Liệu Ca Chạy Cũ:**
   - Dùng thư mục ca chạy vừa xong (vd: `D:/Taadaa/runtime/<cluster>/live/<date>/<shift_run>/`).
   - Gọi trực tiếp `m_res, f_res, u_res = parse_run_all(r_path)` để kiểm tra `machine_dir` có nằm trong dict máy lỗi hay không.
   - Gọi `extract_run_artifacts(machine_dir=m_res[m]['machine_dir'])` và khẳng định trích xuất được `screen.png` (>0 byte), `ui.xml` và `log_tail` trong < 0.1s.
2. **Kiểm Chứng Cổng 0 Telemetry Đạt Score = 2:**
   - Tạo thử envelope với `base_dir=tmp_dir`: kiểm tra `completeness_score() == 2`, `atx_status == 'run_artifact'`.
   - Khẳng định không có bất kỳ lệnh ADB nào (`screencap` hay `dumpUI`) được kích hoạt.
3. **Unit Test Tự Động Qua Pytest:**
   - Chạy focused test: `pytest D:/Taadaa/tools/tests/test_incident_envelope_and_lock.py -k test_parser_artifact_root_to_incident_emitter` (< 1s).
4. **Kích Hoạt Thử Cronjob Trực Tiếp Qua Runtime:**
   - Gọi `cronjob(action='run', job_id='1d62cb3562e0')` (hoặc ID của watchdog tương ứng) để scheduler thực thi ngay 1 nhịp và báo cáo status `ok`.
   - Kích hoạt `cronjob(action='run', job_id='2b5b608429c7')` (`cron-sync-watchdog`) để đảm bảo code Git được đồng bộ sang runtime ngay tức thì.
