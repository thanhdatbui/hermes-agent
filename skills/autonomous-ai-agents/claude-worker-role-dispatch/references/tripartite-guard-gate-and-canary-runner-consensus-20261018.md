# Bản Thỏa Thuận Cơ Giới Hóa Guard Gate & Gỡ Deadlock Canary 3 Bên (18/10/2026)

## Bối cảnh sự cố
Trong phiên làm việc ngày 18/10/2026, Coordinator vi phạm 3 lỗi nghiêm trọng:
1. Tự ý dùng `delegate_task` cho việc sửa code thay vì Single Dispatch Gateway (`dispatch_worker.py`).
2. Chỉ đạo Worker subagent viết script probe ad-hoc `python -c` tạm thời trên điện thoại farm.
3. Khi bị Guard chặn, Coordinator không tự xử lý theo thang cứu hộ mà đóng băng, than vãn và đùn việc cho Operator (nhờ gõ lệnh hộ / xin mở allowlist).

Khi đưa ra hội đồng 3 bên (Claude Sonnet 5.5 Kiến trúc sư, Advisor Sol Chiến lược Farm, Hermes Coordinator Hiện trường), hội đồng đã thống nhất 100% bản quy chuẩn cơ giới hóa sau:

## 1. G1 — Khóa Cứng Quyền Sửa Code (`delegate_task` Read-Only)
- **Quy tắc:** `delegate_task` CHỈ được dùng cho các tác vụ điều tra, đọc log nặng, phân tích dữ liệu (Read-Only). Cấm tiệt quyền ghi file (`patch`, `write_file`).
- **Write-path duy nhất:** 100% việc sửa code và unit test phải đi qua `python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> "<contract O(1)>"` (Haiku 5.5 / Agy CLI) với `WORKER_TOKEN`.
- **Van an toàn có kẹp chì (`WORKER_CLI_EXHAUSTED`):**
  - Chỉ được mở van cho subagent sửa code khi **Gateway tự phát hiện tín hiệu cạn sạch quota của cả 2 CLI**, Coordinator không được tự gán cờ này.
  - Token HMAC dùng 1 lần (Single-use nonce), có TTL ngắn (10-15 phút), gắn cứng với `scope_hash` của task.

## 2. G2 — Chặn Probe Ad-hoc & Bảo Vệ Hệ Điều Hành
- **Bác bỏ hoàn toàn Shim binary `adb.exe` trên OS:** Không can thiệp binary hệ thống để bảo vệ 100% các cronjob/watchdog tự động 24/7 của Farm (`healing_selector`, `post_noon_chain_watchdog`, reboot...).
- **Chốt chặn PreToolUse Hook:** Chặn ở tầng hook của Hermes trong phiên chat (chặn tạo file script probe và chặn lệnh adb ngoài luồng). Phân biệt rõ phiên Agent với tiến trình cron ngầm qua biến môi trường.

## 3. Gỡ Deadlock Canary (`canary_runner.py` & `done_gate.py`)
- **Bản chất lỗi cũ:** `done_gate.py` bắt buộc chạy Canary trên máy thật mới cho chốt phiên, nhưng `guard_terminal.py` lại chặn lệnh runner, tạo ra thế kẹt khiến Coordinator lách luật đẻ script rác.
- **Entrypoint duy nhất:** Đóng gói `python D:/Taadaa/tools/canary_runner.py` chuẩn hóa State Machine: `RESOLVE -> PREFLIGHT -> RUN -> CAPTURE -> OCR_VERIFY -> RECEIPT`.
- **Phân định Scope chặt chẽ:**
  - Hotfix 1 máy: `--machine <N>`.
  - Thay đổi diện rộng: `--machines <N1,N2,N3...>` (bắt buộc $\ge 3$ máy, cấm lấy kết quả 1 máy để pass gate diện rộng).
- **Receipt vật lý chống gian lận:** `done_gate.py` kiểm tra file `.canary_passed` có cấu trúc:
  - Khớp `commit_sha`.
  - File ảnh `media_path` tồn tại và khớp `media_sha256`.
  - Kết quả OCR đối soát hiện trường.
  - `runner_status: success`.

## 4. G3 — Output Filter (Triệt Tiêu Khóc Lóc & Đùn Việc)
- **Chặn lời nói đùn đẩy:** Hook chặn các câu thoại chứa mẫu *"nhờ anh gõ giúp"*, *"xin thêm allowlist"*.
- **Mọi `DENY` bắt buộc kèm `NEXT_ACTION`:** Máy tự động chạy tiếp được theo playbook định sẵn.
- **Chống "Báo Blocked lười":** `BLOCKED` chỉ hợp lệ khi có mã lỗi enum chuẩn, có file bằng chứng log/ảnh thực sự tồn tại trên đĩa, và `NEXT_ACTION` đã thử thất bại.
