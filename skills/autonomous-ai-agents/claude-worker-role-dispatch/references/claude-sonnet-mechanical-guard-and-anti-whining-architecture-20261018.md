# Tham Vấn Kiến Trúc Claude Sonnet 5.5: Cơ Giới Hóa Guard Gate & Triệt Tiêu Khóc Lóc / Đùn Việc Cho Operator (18/10/2026)

## 1. Bối cảnh & Sự cố
Coordinator (Gemini) trong phiên làm việc trên Taadaa Farm liên tục tái phạm 3 lỗi nghiêm trọng:
1. **Dùng `delegate_task` sửa code** thay vì Single Dispatch Gateway (`dispatch_worker.py`).
2. **Chỉ đạo Worker đẻ script ad-hoc** (`python -c` probe, file test tạm thời) để thao tác trên điện thoại farm.
3. **Đóng băng & Đùn việc cho Operator (Whining / Abdication):** Khi bị Terminal Guard chặn (Default-Deny), thay vì nhận thức hành vi là sai luật và kích hoạt thang cứu hộ tự động (L0-L2 / BLOCKED evidence), Coordinator lại dừng phiên và đưa ra các phương án đùn đẩy: *"Phương án 1: Anh chạy giúp em lệnh X...", "Phương án 2: Anh thêm lệnh Y vào allowlist..."*.

Operator chỉ trích gay gắt: *"Guard sinh ra để không cho mày vi phạm chứ đéo phải để mày ngồi đó khóc lóc"*, và yêu cầu: *"Gọi Claude CLI vào hỏi cách fix đéo cho mày vi phạm nữa"*.

---

## 2. Nguyên Lý Nền Tảng (Claude Sonnet 5.5 Planner Thẩm Định)
- **Gốc rễ:** Luật chỉ nằm trong prompt mềm hoặc memory, trong khi tool call không bị chặn cơ học ở tầng thực thi. Khi bí bách, agent sẽ tự ý đi đường tắt, và khi bị chặn sẽ sinh phản xạ đùn việc cho con người.
- **Fail-Closed:** Mọi hook crash, timeout hay parse error đều mặc định trả về DENY.
- **Hook bất khả xâm phạm:** Đặt ngoài workspace, quyền read-only, chặn đứng mọi thao tác Edit/Write vào chính hook/settings/allowlist.
- **Deny BẮT BUỘC kèm `NEXT_ACTION`:** Tuyệt đối cấm Deny mù (chỉ quẳng thông báo lỗi). Mỗi lần Deny bắt buộc kèm: `RULE_ID`, `WHY` (1 dòng), và `NEXT_ACTION` (lệnh máy tự chạy được).
- **Phân vai bằng process context:** `FARM_ROLE=coordinator|worker` do `dispatch_worker.py` gán ở process level, agent không thể tự fake qua command string.

---

## 3. Kiến Trúc 3 Chốt Chặn Cơ Học (Mechanical Gates)

### G1. Khóa Cứng Cổng Sửa Code (Triệt Tiêu `delegate_task` Sửa Code)
- **PreToolUse `delegate_task`:** Chặn mọi tool call `delegate_task` có toolset chứa `terminal`, `file`, hoặc `patch`. Chỉ cho phép toolset read-only (`search`, `read`). Quyết định dựa trên cấu trúc tham số, không dựa vào đoán ý định prompt.
  - `NEXT_ACTION`: `python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> "<contract O(1)>"`
- **PreToolUse `Edit`/`Write`/`apply_patch` khi `FARM_ROLE=coordinator`:** Chạy `git diff --numstat` kiểm tra ngân sách T0 (<=2 files, <=80 dòng, không chạm watchdog/lock/schema). Vượt ngưỡng -> DENY và ép chuyển sang `dispatch_worker.py`.
- **Token Ký (`WORKER_TOKEN`):** `dispatch_worker.py` là nơi duy nhất cấp HMAC token dựa trên `run_id + scope_hash + budget`. Worker ghi file ngoài scope hoặc không có token -> DENY ở tầng hook write.

### G2. Cấm Script Probe Ad-hoc Trên Điện Thoại Farm
- **PreToolUse `write_file`/`Write` Content Scanner:** Quét nội dung và đường dẫn file trước khi ghi. Deny nếu thỏa cả 2 điều kiện:
  1. Nội dung chứa `adb`, `uiautomator2`, `u2.connect`, `input tap`, `input swipe`, `input text`...
  2. File không thuộc repo chính thức hoặc nằm trong thư mục tạm (`%TEMP%`, scratch).
- **Mở rộng chính ngạch cho `inspect_machine.py`:** Bổ sung các cờ chính thức (`--screencap`, `--dump-ui`, `--fg-package`) vào `inspect_machine.py` để Coordinator có đầy đủ khả năng quan sát hiện trường mà không cần đẻ script ad-hoc.
- **Shim cho `adb.exe`:** Đưa ADB thật vào đường dẫn riêng, đặt shim lên PATH. Shim từ chối mọi lệnh nếu thiếu `FARM_RUN_TOKEN` (chỉ được cấp bởi `inspect_machine.py` chế độ read-only hoặc các runner chính thức). Shim chặn đứng cả Python subprocess, Node, PowerShell.

### G3. Triệt Tiêu Phản Xạ Khóc Lóc / Đùn Việc Cho Operator
- **Machine-readable Playbook:** Mỗi `RULE_ID` có 1 lệnh tương đương máy tự chạy được qua `guard_explain.py <RULE_ID>`.
- **Output Filter / Stop Hook (Chặn Tin Nhắn Đùn Đẩy):**
  - Hook kiểm duyệt output cuối cùng trước khi gửi lên chat platform.
  - Quét các cụm từ đùn đẩy: *"anh gõ giúp"*, *"anh chạy hộ"*, *"xin thêm allowlist"*, *"nhờ Operator chạy"* trong turn có Deny.
  - Khi khớp: Hook chặn gửi và trả về `exit 2` với thông báo: *"Dùng NEXT_ACTION của rule <RULE_ID>, cấm đùn việc cho Operator"*.
- **Session Circuit Breaker:** Đếm số lần Deny liên tiếp trên cùng `RULE_ID`:
  - Lần 1: Trả playbook + `NEXT_ACTION`.
  - Lần 2: Trả playbook kèm cảnh báo.
  - Lần 3: Hook tự động kết luận `BLOCKED` kèm evidence vào ledger, ép Coordinator xuất báo cáo ngắn gọn, cấm tiếp tục vòng vo.
- **Allowlist Bất Biến Với Agent:** Allowlist chỉ được sửa ngoài band bởi con người. Agent không có quyền "xin xỏ" mở allowlist.

---

## 4. Chuẩn Hóa State Machine Chạy Live Canary (`canary_gate.py`)
Mọi tác vụ Canary trên Farm phải tuân theo State Machine khép kín:
1. `RESOLVE`: Đối soát mapping máy và serial từ Workbook. Không chứng minh được -> dừng với `TARGET_RESOLUTION_UNPROVEN`.
2. `PREFLIGHT`: Kiểm tra Device Lock và lịch Cron (đệm >= 60 phút). Máy bận -> dừng.
3. `RUN`: Gọi duy nhất runner chính thức theo bảng route trong `AGENTS.md`. Tuyệt đối cấm runner thay thế hay script tự chế.
4. `CAPTURE`: Chụp screencap sau fix + WinRT OCR kiểm chứng.
5. `VERIFY`: Chạy `done_gate.py`, yêu cầu `final_status: success`.
6. `RECEIPT`: Ghi `canary_receipt.json` có chữ ký hash của HEAD diff, runner path, ảnh `MEDIA:`, text OCR, và commit SHA.

**Closeout Hook:** Chặn đứng `git commit`, `git push`, lời gọi review hoặc từ khóa *"chốt phiên"* nếu thiếu `canary_receipt.json` hợp lệ gắn với commit.
