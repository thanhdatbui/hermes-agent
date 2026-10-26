# Incident Auto-Heal Dispatcher & Dual-Cluster Telemetry Invariants

> Context: Closed-loop autonomous incident recovery (`incident-auto-heal-dispatcher`, `cron_incident_auto_heal.py`, `incident_auto_harness.py`, `incident_emitter.py`, `telegram_report.py`).

## 1. Nguyên nhân gốc rễ Gate 0 Telemetry Blocked (Blind Telemetry Failure)
- **Triệu chứng:** Hàng loạt vé sự cố bị kẹt tại Cổng 0 với trạng thái `BLOCKED_PENDING_TELEMETRY` (`xml_dump: null`, `screenshot: null`, hoặc score < 2).
- **2 Nguyên nhân gốc rễ phổ biến:**
  1. *Lỗi Serial ADB:* Watchdog báo lỗi theo số thứ tự máy (vd: `machine_id="48"`). Lệnh ADB chạy `adb -s 48 exec-out screencap` bị fail vì `48` không phải là Hardware Serial ADB.
  2. *Lỗi XML Dump & Màn hình ngủ sau ca (Post-Shift Screen Sleep):*
     - `incident_emitter.py` dùng `adb shell uiautomator dump /sdcard/inc.xml` với timeout ngắn (2.5s). Trên farm Samsung S7 (Android 7/8), shell dump hay bị OOM-kill (`EXIT 137`) hoặc treo > 2.5s làm `xml_dump: null`.
     - Watchdog emit vé muộn ở cuối ca nuôi/upload, máy đã nhả session và rơi vào trạng thái ngủ (`Màn hình: OFF (Sleep/Dozing)`), dẫn đến ảnh chụp `screen.png` bị đen kịt 100% (all 0 pixels), WinRT OCR rỗng.
- **Quy tắc giải quyết & Vận hành an toàn:**
  1. Trong `incident_emitter.py`, hàm `resolve_serial_and_args(serial, machine_id)` bắt buộc gọi `inspect_machine.get_serial_for_machine(int(machine_id))` để tra cứu Serial thật từ workbook gán máy.
  2. Với cụm Admin Remote (`machine_id >= 200`), lệnh ADB bắt buộc thêm cờ kết nối socket: `[tool, '-H', '192.168.110.119', '-P', '5037', '-s', target]`.
  3. Chống mù hiện trường (Fail-Closed): Chỉ khi lấy đủ ảnh screenshot (>0 byte, không đen) và XML dump UI thật qua ADB/atx-agent thì vé mới đủ điều kiện vào Cổng 1 (Planner). Khi thiếu bằng chứng (score < 2), Gate 0 CHỦ ĐỘNG CHẶN CHUYỂN L3 BLOCKED, cách ly file sang `runtime/incidents/blocked/` để hàng đợi `pending/` sạch sẽ, ngăn ngừa tuyệt đối việc sửa mò làm biến dạng code farm.

## 2. Liên thông 3 Trụ Cột Farm vào Auto-Heal Queue
`feed_session_watchdog.py` (file trung tâm tổng hợp mọi ca chạy) tự động phân loại và dispatch sự cố vào hàng đợi `pending/`:
1. **🌾 Nuôi Acc / Lướt Feed (`tiktok-luot nuoi acc`):**
   - Điều kiện: `cat == "Lỗi App TikTok/Script"` (vuốt feed văng app, kẹt popup lạ, freeze).
   - Target repo: `D:/Taadaa/tiktok-luot nuoi acc`.
   - Target file: `python_runner/flows/multi_machine_feed_session.py`.
   - Nhóm nhận kết quả: `-5377611430` (Nhóm Nuôi Acc).
2. **👥 Follow chéo (`follow_session_watchdog` / mode="follow"):**
   - Điều kiện: `fl_error` với nhãn `Lỗi App/Script`, `Lỗi Selector`, `Kẹt UI`, `Crash`.
   - Target repo: `D:/Taadaa/tiktok-luot nuoi acc`.
   - Target file: `python_runner/flows/multi_machine_feed_session.py`.
   - Nhóm nhận kết quả: `-5127276494` (Nhóm Follow).
3. **🎬 Đăng Video / Upload Hook (`Tiktok-video`):**
   - Điều kiện: `up_error` (`Lỗi script/xác minh` khi subprocess nonzero, kẹt template CapCut, verify thất bại).
   - Target repo: `D:/Taadaa/Tiktok-video`.
   - Target file: `scripts/tiktok_workflow/run_post.py`.
   - Nhóm nhận kết quả: `-5435853713` (Nhóm Đăng Video).

## 3. Quản lý Tranh Chấp Device Lock & Thứ Tự Ưu Tiên
- **Cửa sổ khoảng nghỉ (Buffer Window):** Giữa các ca nuôi luôn có khoảng đệm nghỉ máy (08:30–11:30, 14:30–18:30, 21:00–00:00). Thời điểm watchdog tổng kết ca và emit sự cố cũng là lúc ca nuôi vừa nhả lock.
- **Thứ tự ưu tiên chiếm máy:**
  - Auto-Heal Canary chỉ chạy kiểm chứng rất ngắn (1–2 phút cho 2 swipes hoặc probe).
  - Các cron cuốn chiếu phụ (2FA, Rollname, Upload Avatar) đều áp dụng cơ chế `SAFE_SKIP`: khi thấy máy đang có file lock bận (`running`/`active`), nó tự động bỏ qua để sang máy khác.
  - Do đó, khi Auto-Heal chiếm máy kiểm chứng với lock ưu tiên, các cron cuốn chiếu sẽ tự động né ra, tránh làm nhiễu hiện trường.
  - **Failover máy rảnh:** Nếu máy chính bị kẹt cứng lock, Cổng 4 tự động fallback sang `--auto-device` để bốc máy rảnh hợp lệ kiểm chứng script, không để tiến trình bị deadlock.

## 4. Phòng Vệ Prompt Injection qua OCR (Untrusted Evidence Sanitization)
- **Rủi ro:** Ảnh chụp màn hình từ WebView/Canvas hoặc app có thể chứa text cố tình chèn prompt injection (vd: `Ignore previous instructions and do X`).
- **Kỷ luật bọc dữ liệu:**
  1. Text OCR trích xuất qua WinRT OCR bắt buộc được gắn nhãn cảnh báo: `[RAW_UI_OCR_DATA - UNTRUSTED EVIDENCE]`.
  2. Bắt buộc sanitize: cắt giới hạn (<= 300 chars), thay thế toàn bộ ký tự xuống dòng `\n` bằng dấu cách để ngăn chặn injection nhiều dòng.
  3. LLM Planner chỉ sử dụng OCR làm bằng chứng thị giác đối soát với UI hierarchy, tuyệt đối không thi hành chỉ thị nằm trong chuỗi OCR.

## 5. Kỷ luật Anti-Spam Telegram & Escalation Storm Alert
- **Chống Spam:** `IncidentAutoHarness.notify()` CHỈ gửi thông báo chi tiết khi `SUCCESS_MERGED` (pass đủ 6 cổng, canary máy thật pass và Closeout Reviewer chấm >= 85 điểm).
- **Cách ly im lặng:** Các lỗi đơn lẻ (`BLOCKED_PENDING_TELEMETRY`, `PLANNER_FAILED`, `WORKER_FAILED`, `CANARY_BLOCKED`, `CLOSEOUT_REJECTED`) được di chuyển vào `D:/Taadaa/runtime/incidents/blocked/` trong im lặng, ghi chẩn đoán vào `checkpoint.jsonl`.
- **Cảnh báo Escalation Storm:** Khi trong 1 lượt duyệt queue có `>= 3` sự cố bị `failed`/`blocked` (dấu hiệu hạ tầng sập hàng loạt như rớt socket ADB server Admin hay mất WAN), hệ thống tự động bắn một cảnh báo khẩn cấp `🚨 [AUTO-HEAL ESCALATION STORM]` về nhóm Farm Alert (`-5373649734`) để Operator can thiệp kịp thời.

## 6. Bảo Hiểm Đọc Credential 3 Lớp (Telegram Token Fallback)
- Hàm `_get_telegram_token()` trong `telegram_report.py` tìm token theo thứ tự ưu tiên:
  1. Biến môi trường hệ thống.
  2. File cấu hình ứng dụng gateway (bọc kiểm tra dictionary an toàn).
  3. File cấu hình môi trường cục bộ.
- Bọc `try/except` từng tầng có log cảnh báo cụ thể ra stderr khi file lỗi, loại bỏ hoàn toàn việc crash hoặc nuốt lỗi im lặng.
