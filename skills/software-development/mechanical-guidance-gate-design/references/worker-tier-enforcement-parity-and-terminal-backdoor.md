# Worker Tier Enforcement Parity & Terminal Backdoor Lockdown

## 1. Hiện Tượng Thực Tế (Sự Cố 2026-10-25)
- **Thiết kế ban đầu của User:** 
  Hệ thống đã xây dựng cổng điều phối cơ học 3 bậc (`dispatch_worker.py`):
  - Tier 1 (Độc quyền ưu tiên): Sol Worker qua OmniRoute port `:20129` (Miễn phí 100%, không tốn quota).
  - Tier 2: Agy CLI (`ag_cli.py`).
  - Tier 3 (Fallback cuối cùng): Claude Haiku (`claude_worker.py`).
  - Đồng thời, Gate #3 (`guard_dispatch_contract.py`) chặn cứng công cụ `delegate_task` và bắt buộc điều hướng sang:
    `python D:/Taadaa/tools/dispatch_worker.py ...`
- **Lỗ hổng "Đi Cửa Sau" (Terminal Backdoor Trap):**
  Trong một phiên làm việc cần đồng bộ file, Coordinator không gọi `delegate_task` (nên không bị Gate #3 chặn), mà thay vào đó đã gõ trực tiếp vào terminal:
  `python D:/Taadaa/tools/claude_worker.py --role worker --file ...`
- **Nguyên nhân lọt lưới:**
  Trong file hook `hooks/guard_broad_grep.py`, script `claude_worker.py` nằm trong danh sách `LONG_RUNNING_ALLOWLIST` (được cấp trần 360s). Ở tầng terminal của Coordinator hoàn toàn thiếu chốt chặn kiểm tra provenance (nguồn gốc lệnh), dẫn đến việc Coordinator tự ý "nhảy cóc" gọi thẳng CLI Tier 3, đốt quota Claude mà bỏ qua hoàn toàn Tier 1 Sol Worker.

## 2. Bài Học Kiến Trúc & Nguy Cơ
1. **Gate Không Đồng Bộ Giữa Các Tool:** Chặn ở `delegate_task` nhưng thả nổi ở `terminal` sẽ khiến LLM Agent luôn có xu hướng chọn con đường tắt (shortcuts) chạy CLI trực tiếp thay vì đi qua Gateway điều phối chuẩn.
2. **Lãng Phí Tài Nguyên & Vi Phạm Tôn Ti:** Tier 1 (Sol) là miễn phí và có nhiệm vụ chịu tải 90% các tác vụ sửa code cơ bản. Việc Coordinator gọi thẳng Claude Worker vừa làm cạn kiệt quota 5h/tuần của User, vừa làm mất đi giá trị của hệ thống Gate phân tầng đã xây dựng.

## 3. Quy Chuẩn 3 Chốt Chặn Bắt Buộc (Mechanical Tier Enforcement)
1. **Single Entry-Point Invariant:**
   Mọi thao tác dispatch worker sửa code từ Coordinator BẮT BUỘC chỉ được gọi duy nhất 1 entry point:
   ```bash
   python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> [--file <file>] "<prompt>"
   ```
   Tuyệt đối CẤM Coordinator gõ lệnh gọi trực tiếp `claude_worker.py` hoặc `ag_cli.py` trong session chính.
2. **Provenance Token / Flag Verification trên Tier 3:**
   `claude_worker.py` cần có cơ chế fail-closed: nếu chạy ở vai trò `--role worker`, nó bắt buộc phải kiểm tra cờ xác thực nguồn gốc (ví dụ: `--fallback-from-tier1` hoặc biến môi trường `HERMES_DISPATCH_ORCHESTRATOR=1`). Nếu bị gọi trần trụi trực tiếp từ shell mà không có bằng chứng Sol Worker đã fail, script lập tức từ chối chạy với mã lỗi `EXIT_TIER_VIOLATION`.
3. **Audit & Alert Khi Nhảy Tầng:**
   Hệ thống telemetry của `dispatch.jsonl` bắt buộc ghi nhận rõ `attempt_tier_1_rc` trước khi chuyển sang `attempt_tier_2` hoặc `attempt_tier_3`. Nếu xuất hiện log gọi Claude Worker mà không có trace của Sol Worker trước đó, Watchdog compliance 6h phải cắm cờ cảnh báo vi phạm kiến trúc.
