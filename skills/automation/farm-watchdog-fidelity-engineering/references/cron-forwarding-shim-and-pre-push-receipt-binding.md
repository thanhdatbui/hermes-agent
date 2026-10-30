# Cron Forwarding Shim Architecture & Pre-Push Audit Receipt Binding

## 1. Heavy Automation Cron Jobs & The LLM-Timeout Trap
- **Triệu chứng:** Cron job chạy các tác vụ automation nặng (như Playwright, GPMLogin batch cứu acc `cron_auto_feed_chatgpt_pool.py`) thỉnh thoảng hoặc liên tục bị đánh dấu `last_status: error`.
- **Nguyên nhân gốc:** Job được khai báo `no_agent: false` (hoặc thiếu cờ `no_agent`). Khi đến lịch chạy, scheduler spawn một LLM agent session để thực thi shell command. Nếu tác vụ trình duyệt chạy quá 180s, session LLM chạm trần timeout và bị hủy ngang với mã lỗi `error`.
- **Giải pháp dứt điểm:**
  1. Tạo **Canonical Zero-Drift Forwarding Shim** đặt tại `%LOCALAPPDATA%\hermes\scripts\<script_name>.py` (và đồng bộ sang `deploy\hermes-home\scripts\` và `OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\`).
  2. Shim gọi trực tiếp script đích trong repo:
     ```python
     PY = sys.executable  # hoặc venv automation
     SCRIPT = r"D:\Taadaa\...\scripts\<script_name>.py"
     proc = subprocess.run([PY, "-B", SCRIPT] + sys.argv[1:], cwd=WORKDIR)
     ```
  3. Cập nhật cấu hình cron sang **`no_agent: true`** kết hợp `script: "<script_name>.py"`. Scheduler sẽ chạy thẳng tiến trình con mà không tốn token LLM và không bị giới hạn bởi trần timeout của agent loop.

## 2. Quy Trình Vượt Pre-Push Hook Qua Closeout Receipt Binding
- **Cơ chế Hard Invariant (`INC-HERMES-2026-001`):**
  - Script đẩy code an toàn `python D:/Taadaa/tools/safe_push.py <repo>` kích hoạt hook `.git/hooks/pre-push`.
  - Hook quét file log thẩm định của Closeout Gate để tìm bản ghi có `commit` khớp đúng mã băm SHA của commit `HEAD` hiện tại, kèm `verdict=APPROVED` và `score >= 80`.
  - Nếu commit vừa được tạo bằng `git commit -m "..."` mà gọi ngay `safe_push.py`, lệnh push sẽ bị **CHẶN ĐỨNG**:
    ```text
    ❌ [BLOCKED - PRE-PUSH HOOK]: Gate check FAILED — Không tìm thấy bản ghi Closeout Gate APPROVED >= 80 cho commit hiện tại!
    ```
- **Quy trình 3 bước bắt buộc khi push code farm:**
  1. **Bước 1 (Commit):** Tạo commit git chứa code và test sạch:
     ```bash
     git -C "<repo>" commit -m "fix(...): ..."
     ```
  2. **Bước 2 (Cấp biên lai thẩm định cho HEAD):** Chạy Closeout Gate trên commit vừa tạo:
     ```bash
     python D:/Taadaa/tools/closeout_gate.py --repo "<repo>" --base HEAD~1 --json-output
     ```
     *(Hoặc `python D:/Taadaa/tools/closeout_v2.py --repo "<repo>" --base HEAD~1 --json-output`)*
     Lệnh này sẽ ghi bản ghi thẩm định hợp lệ gắn với mã commit SHA vào audit log.
  3. **Bước 3 (Safe Push):**
     ```bash
     python D:/Taadaa/tools/safe_push.py "<repo>"
     ```
     Pre-push hook đối soát thành công và cho phép đẩy lên remote GitHub:
     ```text
     ✅ [pre-push] Closeout Gate OK: verdict=APPROVED score=100 passed=True commit=<SHA>
     [pre-push] Cho phép push.
     ```
