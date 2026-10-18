# Cronjob Safety Gate & Defense-in-Depth Against LLM-Agent Queue Starvation

## 1. Sự cố thực tế & Căn nguyên kỹ thuật (18/10/2026)
- **Hiện tượng:** Tất cả session Telegram của Operator bị treo cứng, hoàn toàn không phản hồi từ 11:00 đến 12:29 trưa. Đến 12:25 - 12:29 thì tin nhắn đột ngột nổ dồn dập.
- **Nguyên nhân gốc rễ:**
  - Hai cronjob (`cron-auto-feed-chatgpt-pool` và `chatgpt-account-lifecycle-healer`) được tạo với lịch lặp dày đặc (`*/15 * * * *`) nhưng **bị thiếu cờ `no_agent: True`** (mặc định của Hermes Agent runtime là `no_agent: False`).
  - Khi kích hoạt (tick), Hermes coi đây là một task của AI Agent, tự động dựng một full LLM session mới.
  - Con AI Agent này chạy script Python, đọc stdout thấy dài hoặc có lỗi, liền rơi vào vòng lặp agentic reasoning (gọi tool, chẩn đoán, thử lại) kéo dài tới **86 turns / messages**.
  - Toàn bộ kết nối API và hàng đợi tin nhắn của Hermes Gateway bị chiếm dụng 100%, khiến mọi tin nhắn tương tác của Operator trong các topic Telegram bị dồn ứ trong hàng đợi (message queue starvation) suốt hơn 1 tiếng rưỡi.

## 2. Quy tắc phân định vai trò: Claude CLI vs Hermes Coordinator
- **User Mandate (18/10/2026):**
  - **Claude Code CLI (`claude -p` / `--role reviewer` / `--role planner`):** CHỈ dùng để tư vấn kiến trúc, thiết kế bảo vệ hệ thống, review code độc lập và sửa chữa các chốt chặn Gate Guard. CẤM TUYỆT ĐỐI gọi Claude CLI làm thay các task chính / nghiệp vụ farm hàng ngày để bảo vệ hạn mức Quota 5h (< 85%).
  - **Hermes Coordinator (Gemini / Omni-worker):** Tự lực thực thi các tác vụ vận hành, giao diện và sửa code trong ngân sách an toàn T0 (<= 80 dòng, <= 2 files) hoặc dispatch Worker subagent theo hợp đồng phân tầng Tiered Workflow 3.0.
  - **Sửa luật phải sửa bằng Code Gate:** Cấm sửa chính sách trên giấy (`AGENTS.md` / `HERMES_SUBAGENT_RULES.md`) mà bỏ quên chốt chặn Code Python runtime trong các file guard engine và hook pre-tool.

## 3. Kiến trúc Phòng thủ 2 Lớp (Defense-in-Depth Gate Guard)
Được đồng thuận bởi cả 3 bên: **Advisor Sol (`gpt-web-sol` :20129)**, **Claude Code CLI**, và **Hermes Coordinator**:

### Lớp 1: PreToolUse Contract Hook (Tích hợp trực tiếp vào `guard_cronjob_safety.py`)
- **Tránh xung đột & Phân mảnh hook:** Không tạo thêm file hook mới để tránh spawn 2 tiến trình hook lồng nhau. Mở rộng trực tiếp `D:/Taadaa/tools/guard_cronjob_safety.py` với hàm `check_cron_policy(ti)` chạy trước vòng quét console window `check_segment()`.
- **Phạm vi kiểm tra:** Chỉ chặn các thao tác `action in ('create', 'update')`; cho qua `list`, `pause`, `resume`, `remove`, `run` để không cản trở cứu hộ sự cố.
- **Rule Contract nghiêm ngặt:**
  1. `no_agent is True`: Bắt buộc kiểu `bool` chuẩn trong Python (`type(val) is bool and val is True`). Chặn đứng số `1`, mảng `[]`, chuỗi lách luật `"true"` hay `"True"`.
  2. Bắt buộc có trường `script: <file.py>` và file đó phải tồn tại trên đĩa cứng trong thư mục quy chuẩn (`%LOCALAPPDATA%\hermes\scripts\<script>` hoặc `D:/Taadaa/**`).
  3. **Chống Path Traversal:** Cấm tuyệt đối `..` và symlink trỏ ra ngoài allowed roots; bắt buộc resolve canonical path trước khi kiểm tra tồn tại.
  4. **Chống Update Bypass & Chặn oan Update một phần:**
     - Khi `action == 'create'`: Bắt buộc 100% phải có `no_agent: True` và `script`.
     - Khi `action == 'update'`: Chặn nếu cố tình set `no_agent=False` hoặc xóa `script` (`""` hoặc `None`); cho phép nếu chỉ update `schedule` hoặc metadata.
  5. Cấm tuyệt đối cronjob LLM-driven (`no_agent: False`) chạy tần suất dày đặc (< 6 giờ, như `*/5`, `*/15`, `*/30`, `every 15m`).
  6. Nếu có cronjob LLM hợp lệ (>= 6 giờ), bắt buộc phải có hard-cap `max_turns <= 5` và `timeout <= 120s` để triệt tiêu vĩnh viễn bẫy lặp 86 turns.
- **Tách biệt Telemetry Audit:** Tham số hóa `log_block()` để ghi nhận event riêng `cron_policy_block` / `cron_policy_allow` với tag `[CRON_AGENT_POLICY_BLOCKED]`, tách rời khỏi `console_window_*`.

### Lớp 2: Storage Reconciler Scanner (`reconcile_cronjobs.py`)
- Script chạy ngầm độc lập (bản thân nó chạy bằng `no_agent: True`).
- Đọc trực tiếp `jobs.json`, quét toàn bộ các job đang `enabled: True`.
- Nếu phát hiện bất kỳ job nào vi phạm schema, thiếu `no_agent: True` hoặc là LLM agent tần suất cao:
  * Tự động set `enabled: False`, chuyển `state: 'paused'`.
  * **CẤM XÓA JOB:** Không bao giờ xóa job hoặc sửa schedule để bảo toàn lịch sử cấu hình của Operator.
  * Ghi lý do cách ly vào audit log `cron_reconcile_audit.jsonl`.
  * Gửi đúng 1 cảnh báo Telegram dedup cho Operator.
  * **Atomic Write & Lock:** Ghi file nguyên tử (Atomic write qua temp file cùng thư mục rồi `os.replace`) dưới lock để chống race-condition với Scheduler.
  * **Chế độ Dry-Run an toàn:** Mặc định chạy `--dry-run` chỉ in danh sách job sẽ pause để Operator duyệt; CHỈ áp dụng ghi khi có cờ tường minh `--apply` (tuân thủ luật farm: cấm tự ý pause cron nuôi acc/reg).

## 4. Bảo toàn Test Suite & Hồi quy
- Cập nhật helper `scan()` trong `tests/test_guard_cronjob_safety.py` luôn kèm `"no_agent": True` để bảo toàn 35 tests kiểm tra console window cũ không bị fail.
- Bổ sung nhóm tests mới:
  * Block thiếu `no_agent` lúc `create`.
  * Block `no_agent: False` lúc `create` và `update`.
  * Block `no_agent: 1`, `"true"`, `"True"`.
  * Block path traversal (`..`), script không tồn tại.
  * Block update xóa `script`.
  * Allow `create` chuẩn `no_agent: True` + valid script.
  * Allow `update` chỉ đổi `schedule`.
  * Allow `list`, `pause`, `remove`.
