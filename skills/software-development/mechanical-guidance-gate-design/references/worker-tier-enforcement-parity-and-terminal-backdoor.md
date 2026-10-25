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

## 3. Quy Chuẩn 3 Chốt Chặn Bắt Buộc (Đã Triển Khai Cơ Học & Pass 115 Tests)
1. **Single Entry-Point Invariant:**
   Mọi thao tác dispatch worker sửa code từ Coordinator BẮT BUỘC chỉ được gọi duy nhất 1 entry point:
   ```bash
   python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> [--file <file>] "<prompt>"
   ```
   Tuyệt đối CẤM Coordinator gõ lệnh gọi trực tiếp `claude_worker.py` hoặc `ag_cli.py` trong session chính.
2. **Provenance Token / Flag Verification trên Tier 3 (`--from-dispatch` Exit 126):**
   Trong `claude_worker.py`, vai trò `--role worker` được bảo vệ bằng chốt chặn cơ học fail-closed:
   ```python
   if role == "worker" and not (args.from_dispatch or os.environ.get("DISPATCH_TIER_CALLER") == "dispatch_worker"):
       audit("mechanical_tier_gate_violation", role=role)
       print("⛔ [MECHANICAL TIER GATE VIOLATION]: Direct invocation of claude_worker for role worker is forbidden! "
             "Route through dispatch_worker.py (Tier 1 Sol first).", file=sys.stderr)
       return 126
   ```
   - Khi Coordinator hoặc script lạ gõ thẳng: `python D:/Taadaa/tools/claude_worker.py --role worker ...` $\rightarrow$ Trả về mã lỗi 126 và chặn đứng, triệt tiêu hoàn toàn khả năng bypass.
   - Khi đi đúng quy chuẩn qua `dispatch_worker.py`: Hàm `haiku_cmd` tự động truyền `--from-dispatch` sau khi Tier 1 Sol và Tier 2 Agy đã chạy thử nghiệm thất bại.
3. **Anti-Paralysis Execution Discipline (Cấm Khóc Lóc Bại Liệt):**
   - Khi gate kích hoạt hoặc phát hiện lỗi điều phối, CẤM Coordinator ngồi phân trần, than thở hay đổ lỗi cho môi trường/tools.
   - BẮT BUỘC thực thi dứt điểm bằng gate cơ học: Sử dụng công cụ chuẩn xác (Claude CLI khi User yêu cầu trực tiếp, hoặc sửa O(1) đúng hợp đồng) và chạy test kiểm chứng ngay tại hiện trường.
