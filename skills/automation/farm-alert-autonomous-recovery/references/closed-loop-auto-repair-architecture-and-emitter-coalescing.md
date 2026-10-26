# Closed-Loop Auto-Repair Architecture, Emitter Coalescing & Canary Gate 4 Adapter

> Kinh nghiệm thiết kế và thi công hệ thống tự sửa code khép kín (Autonomous Script Auto-Repair) cho Taadaa Phone Farm (tháng 10/2026).

## 1. Kiến trúc 6 Cổng Điều Phối (IncidentAutoHarness)
Thay vì để LLM tự do sửa code hoặc sửa trong luồng chính của session, Auto-Repair chạy trong tiến trình headless độc lập qua 6 cổng cơ học bất biến:
- **Cổng 0 (Telemetry Completeness):** Bắt buộc có cả cây UI XML và ảnh chụp màn hình PNG (> 0 bytes) kèm OCR text. Thiếu bằng chứng -> `BLOCKED_PENDING_TELEMETRY`, cấm sửa mò.
- **Cổng 1 (Mechanical Planner):** Tier 1 là Claude Sonnet CLI (`dispatch_planner.py`), Tier 2 dự phòng là Sol Planner (:20129) khi quota >= 85%. Bắt buộc anchor duy nhất (`grep -c == 1`), contract `old_string -> new_string`, test command < 30s.
- **Cổng 2 (Surgery Worker):** Thi công bản vá O(1) qua `dispatch_worker.py`, ngân sách cứng <= 2 files, <= 30 dòng diff (`git diff --numstat`). Vượt quá -> revert ngay.
- **Cổng 3 (Protected Regression Gate):** Kiểm tra các hằng số bảo vệ phần cứng và tài khoản qua `guardgate/runner.py` (Case 162 timeout micro-drop >= 20s, Case 161 follow ceiling <= 0, CREATE_NO_WINDOW flags).
- **Cổng 4 (Canary Gate):** Tự động kích hoạt `canary_runner.py` trên 1 máy thật/test, xuất `canary_evidence.json` kèm ảnh nghiệm thu thực tế.
- **Cổng 5 (Closeout Gate):** Reviewer Sol (:20129) chấm điểm độc lập qua `closeout_gate.py` (ngưỡng >= 85/100, grace band >= 80).

## 2. Dây Kích Nổ (Incident Emitter) & Thu Thập Telemetry < 2.5s
- **Phân loại Heuristic Lỗi Phần cứng vs Lỗi Code:**
  - Lỗi Phần cứng / ADB / USB: Return code lệnh ADB != 0 hoặc chứa chuỗi `('device offline', 'device not found', 'no devices', 'protocol fault', 'connection refused')` -> Không gửi LLM sửa code, ghi nhận lỗi runtime hạ tầng.
  - Lỗi Script / UI Drift: Lệnh ADB trước đó returncode == 0 (máy sống, phản hồi bình thường) nhưng Python crash (`NoSuchElement`, `KeyError`, vỡ selector) -> 100% là lỗi code/UI -> Kích hoạt Emitter.
- **Thu thập Telemetry song song:**
  - Bắn đồng thời 2 tiến trình: `p_cap = adb exec-out screencap -p` và `p_xml = adb shell uiautomator dump` với timeout cứng 2.5s.
  - Bắt buộc kiểm tra returncode của cả 2 tiến trình (`rc_cap == 0` và `rc_xml == 0`) trước khi pull XML về máy tính.
  - Khi timeout: BẮT BUỘC gọi `p.kill()` VÀ `p.wait()` để reap process, chống để lại zombie subprocess trên Windows.
- **Tích hợp WinRT OCR:**
  - Gọi `winrt_ocr_util.winrt_ocr(png_path)` để trích xuất text tiếng Việt/Anh trực tiếp từ ảnh chụp màn hình, nạp vào `telemetry.extra['ocr_text']` giúp Planner hiểu ngữ cảnh màn hình mà không cần tốn token vision.

## 3. Cơ Chế Chống Bão Sự Cố (Anti-Storm Coalescing)
- **Vấn đề:** Khi TikTok đổi giao diện hoặc bật popup mới, cả cụm 15-80 máy trong ca cùng nổ lỗi giống hệt nhau. Nếu bắn 15-80 tickets sẽ làm tràn queue và xung đột khóa NTFS `IncidentLock`.
- **Giải pháp Marker Atomic:**
  - Tính `error_signature = sha256(error_type + target_file + normalized_stack)[:16]`.
  - Dùng cờ `os.O_CREAT | os.O_EXCL` tạo file marker `pending/SIG_{signature}.marker`.
  - Máy đầu tiên: Tạo marker thành công -> Lưu vé sự cố chính thức vào `pending/<incident_id>.json`.
  - Các máy sau (cùng signature trong cửa sổ 20 phút của ca): Bị `FileExistsError` -> Không tạo vé mới, chỉ ghi số máy vào `pending/<incident_id>.affected.jsonl`.
  - Xử lý Marker hết hạn (> 1200s): Ghi đè nguyên tử bằng file tạm `.tmp.<pid>` và `os.replace` để triệt tiêu hoàn toàn race condition giữa các tiến trình.

## 4. Adapter Cổng 4 (Canary Gate) & Bẫy Stale Receipt
- **Lệch Schema giữa Canary Runner và Harness:**
  - `canary_runner.py` xuất ra file dùng chung toàn farm: `D:/Taadaa/.canary_receipt.json` với trường `runner_status` và `media_path`.
  - `IncidentAutoHarness` cần file per-incident `canary_evidence.json` với trường `final_status` và `media`.
- **Bẫy Stale Receipt:**
  - Nếu chỉ kiểm tra `receipt_file.is_file()`, Harness có thể nhặt nhầm receipt của một ca chạy từ nhiều giờ trước.
  - Bắt buộc ghi lại mốc thời gian bắt đầu `t_start = time.time()` trước khi gọi runner.
  - Kiểm tra `receipt_file.stat().st_mtime >= (t_start - 2.0)` và xác thực schema `runner_status in ('success', 'failed')` kèm file media tồn tại thật.
  - CẤM gọi `receipt_file.unlink()` vì đây là file dùng chung của toàn farm, xóa nó sẽ làm đứt luồng của các tiến trình giám sát khác.

## 5. Chống Rò Rỉ Môi Trường Test & Vòng Lặp Kẹt Hàng Đợi (Queue Jam)
- **Bẫy Rò Rỉ Test Vào Hàng Đợi Production (Test Isolation Leak):**
  - **Triệu chứng:** Khi chạy unit test / CI (`pytest test_incident_envelope_and_lock.py`), nếu `emit_if_needed` dùng biến toàn cục `INCIDENTS_BASE` thay vì dependency injection, test sẽ âm thầm tạo các ticket giả lập (`RuntimeError`, `test.py`, telemetry rỗng) vào thư mục sản xuất thật `D:/Taadaa/runtime/incidents/pending`.
  - **Khắc phục:** `emit_if_needed(..., base_dir: Optional[Path] = None)` bắt buộc nhận `base_dir`. Mọi thao tác `collect_telemetry(..., base_dir=base)`, `marker`, và `envelope.save_pending(base_dir=base)` phải bám theo `base = base_dir or INCIDENTS_BASE`. Mọi test case bắt buộc truyền `base_dir=tmp_dir`.
- **Cơ Chế Cách Ly Tránh Spam Lặp (Queue Jam & Quarantining):**
  - **Nguyên tắc:** Mỗi sự cố chỉ được báo cáo 1 lần khi chuyển trạng thái cuối (Done hoặc Blocked). CẤM để sự cố lỗi nằm vĩnh viễn ở `pending/`.
  - **State Machine trong `process_queue()`:**
    - `rc == 0`: Vá thành công -> Chuyển sang `base_dir / 'resolved'`.
    - `rc == 20`: Kẹt khóa scope (`LOCK BUSY`) -> Giữ lại ở `pending/` để thử lại ca sau.
    - `rc != 0` và `rc != 20` (`BLOCKED_PENDING_TELEMETRY`, `PLANNER_FAILED`, `WORKER_FAILED`, `CLOSEOUT_REJECTED`): Đã notify 1 lần -> BẮT BUỘC di chuyển file vé sang `base_dir / 'blocked'` ngay lập tức. Triệt tiêu hoàn toàn nguy cơ cron 15 phút quét lại và spam Telegram bão thông báo lặp vô tận.
- **Kỷ Luật Ứng Xử Điều Phối (Anti-Paralysis):**
  - Khi User báo alert dispatcher lỗi/spam ("Clgt", "Fix đi"): CẤM TUYỆT ĐỐI dừng lại phân trần triết lý hay tường trình suông khi chưa chạm code.
  - Phải lập tức truy vết hàng đợi thật (`runtime/incidents/pending`), kiểm tra schema/diff của emitter & harness, cô lập nguồn sinh rác và verify bằng focused test trước khi báo cáo.


## 5. Bẫy Notification Flood Trong Queue Processing & Anti-Spam
- **Vấn đề vỡ trận spam Telegram:**
  - Trong `incident_auto_harness.py`, hàm `notify()` được gọi trực tiếp bên trong `run()` mỗi khi 1 sự cố fail cổng (đặc biệt là Cổng 0 `BLOCKED_PENDING_TELEMETRY`).
  - Khi cronjob `incident-auto-heal-dispatcher` chạy `process_queue()` duyệt qua các vé tồn đọng trong `pending/`, vòng lặp đã bắn liên thanh các tin nhắn `[AUTO-HEAL REPORT]` riêng lẻ vào channel Telegram gây bão tin nhắn (bị user phản ứng gắt gao).
- **Quy tắc cơ giới hóa:**
  - **CẤM notify lẻ trong loop:** Vòng lặp `process_queue()` tuyệt đối KHÔNG được gửi tin Telegram riêng lẻ cho từng incident bị fail Cổng 0 / telemetry thiếu.
  - **Chỉ gửi 1 tin Digest tổng kết:** Dispatcher chỉ được gửi đúng 1 bản tin tóm tắt duy nhất sau khi duyệt xong toàn bộ queue: `[INCIDENT AUTO-HEAL DISPATCHER] Đã vá: X, Thất bại / L3: Y`.
  - **Xử lý nhanh khi bị spam:** Nếu phát hiện dispatcher bắn lặp tin, Coordinator lập tức dùng `cronjob(action='pause', job_id='...')` ngắt ngay tiến trình lập lịch trước khi can thiệp điều tra hoặc sửa code.

## 6. Bẫy Mapping ADB Serial Trong Thu Thập Telemetry
- **Lỗi `serial = serial or machine_id`:**
  - `machine_id` trên farm thường là số thứ tự (`1`, `2`, `38`...), trong khi ADB yêu cầu hardware serial thật (chuỗi hex hoặc IP:port).
  - Nếu `serial` nhận giá trị thô từ `machine_id` mà không qua hàm tra cứu map serial (`get_serial_by_machine(m)`), lệnh `adb -s <serial> screencap` sẽ timeout/fail 100%.
  - Hậu quả: Toàn bộ ảnh và XML đều rỗng (0 bytes) $\to$ rớt 100% Cổng 0 `BLOCKED_PENDING_TELEMETRY`, biến lỗi phần mềm thành lỗi thiếu telemetry giả tạo.


## 5. Hook Emitter Thực Chiến Vào Watchdog Nuôi (`feed_session_watchdog.py`)
- **Vị trí cắm hook mỏng:** Trong `feed_session_watchdog.py`, tại khối tổng hợp lỗi ca nuôi `fail_groups.items()`, chỉ kích hoạt khi `cat == "Lỗi App TikTok/Script"`.
- **Nguyên tắc không phá vỡ Watchdog:**
  - Bọc trong `try/except` độc lập với `logger.warning("[INCIDENT_EMITTER_WARNING] %s", exc)`. Nếu emitter gặp lỗi runtime, watchdog vẫn tiếp tục in báo cáo và hoàn thành phiên bình thường.
  - BẮT BUỘC tra cứu hardware serial thật qua device inventory / machine mapping (e.g. `get_device_serial(machine_num)` hoặc workbook inventory), TUYỆT ĐỐI CẤM truyền số máy thô (`"16"`) vào `serial`. Truyền số máy thô vào `serial` khiến `adb -s 16 screencap` fail 100%, sinh ra envelope có `screenshot: null, xml_dump: null` và gây kẹt toàn bộ Cổng 0.
  - Chỉ định rõ `target_file="python_runner/flows/multi_machine_feed_session.py"` để Harness tính đúng `scope_hash` cho `IncidentLock`.

## 8. Chẩn Đoán Khi Auto-Heal Sau Ca Chạy Không Hoạt Động (Triage Checklist)
Khi người dùng phản ánh auto-heal không chạy sau báo cáo watchdog ca:
1. **Kiểm tra trạng thái Cronjob:** Gọi `cronjob(action='list')` kiểm tra job `incident-auto-heal-dispatcher`. Nếu `state == 'paused'` (thường do phiên trước pause chống spam sau sự cố), dispatcher sẽ không bao giờ thức dậy để xử lý hàng đợi.
2. **Kiểm tra Telemetry trong `pending/`:** Đọc file JSON trong `D:/Taadaa/runtime/incidents/pending/`. Nếu `screenshot: null` hoặc `xml_dump: null`, Cổng 0 sẽ từ chối xử lý. Phải kiểm tra trường `serial` xem có bị truyền nhầm `machine_id` số thay vì hardware serial ADB hay không.
3. **Quy trình phục hồi khép kín:**
   - Dọn sạch các file envelope thiếu telemetry trong `pending/`.
   - Sửa hàm gọi emitter ở watchdog để mapping đúng hardware serial.
   - Gọi `cronjob(action='resume', job_id='...')` để tái kích hoạt auto-heal an toàn.

## 6. Dependency Injection `base_dir` Cho Phép Cô Lập Test
- Trong `incident_emitter.py`, hàm `emit_if_needed` nhận thêm `base_dir: Optional[Path] = None`.
- Mặc định (`base_dir=None`) trỏ về `INCIDENTS_BASE = Path("D:/Taadaa/runtime/incidents")`.
- Trong unit test/sandbox: Truyền `base_dir=tmp_path` để cô lập 100% dữ liệu test, triệt tiêu nguy cơ để lại file sự cố giả trong thư mục `pending/` thật của hệ thống.

## 7. Pitfalls Thực Chiến: Closeout Binding Mismatch & Console Window Guard
- **Closeout Gate Binding Mismatch (`staged/working-tree candidate overlaps committed HEAD`):**
  - **Triệu chứng:** Khi chạy `closeout_gate.py --repo <path> --base HEAD~1`, Bước 2 thất bại với `✘ binding mismatch: staged/working-tree candidate overlaps committed HEAD`.
  - **Nguyên nhân:** Working tree có thay đổi chưa commit (unstaged hoặc staged) trùng lặp với commit vừa tạo ở `HEAD`.
  - **Khắc phục:** Bắt buộc đồng bộ working copy sạch hoàn toàn với `HEAD` (`git diff HEAD` phải rỗng, unstage bằng `git restore --staged <file>` nếu cần) trước khi chạy `closeout_gate.py`.
- **Console Window Guard trên Windows & Thang Leo Thang Coordinator:**
  - Khi chạy background process (`background=True`), lệnh `python` trần bị chặn bởi `[CONSOLE_WINDOW_BLOCKED]`.
  - Nếu `pythonw` hoặc `powershell -WindowStyle Hidden` không nằm trong allowlist của Coordinator, không được thử lại mù quáng; lập tức chuyển sang L2 Emergency Surgery (nếu đã có exact diff O(1) <= 2 files, <= 30 dòng) hoặc chạy foreground với timeout <= 60s.
- **Hành vi Phản Hồi Khi Nhận Lệnh "Fix đi":**
  - Khi user báo lỗi ("Clgt", "Fix đi", "Fix đi gemini"), CẤM TUYỆT ĐỐI trả lời bằng văn bản hứa hẹn, giải thích triết lý hay trình bày kế hoạch ("Tôi sẽ xử lý...", "Bước tiếp theo cần...").
  - Phải lập tức gọi tool để truy vết hiện trường, phân tích queue/log, sửa code, chạy test focused và chỉ trả lời kèm bằng chứng thực tế khi đã hoàn tất.

