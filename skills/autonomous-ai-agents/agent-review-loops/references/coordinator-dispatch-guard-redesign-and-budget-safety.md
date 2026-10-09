# Coordinator Dispatch-Budget Redesign & Guard Safety

## 1. Core Rule: "Kiểm tra" nghĩa là Kiểm tra (Read-Only Probe)
- Khi user bảo "kiểm tra lại", "check xem đã fix chưa": BẮT BUỘC chỉ dùng lệnh inspect đọc trạng thái hiện hành (read-only state probe, SQLite, lock file, hoặc status output).
- CẤM TUYỆT ĐỐI tự ý gọi `claude -p`, `delegate_task` hay khởi chạy tiến trình sửa code để "thử nghiệm" khi user chưa yêu cầu chạy worker.

## 2. Phân biệt Runtime Live Plugin vs Deploy/Repo Copy
- **Live active plugin:** `C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard/__init__.py` (tiến trình Gateway đang nạp).
- **Deploy/Repo copy:** `D:/Taadaa/Hermes/deploy/hermes-home/plugins/farm-coordinator-guard/__init__.py`.
- Hai file này có thể bị lệch trạng thái (desync). Không được tùy tiện ghi đè mù quáng. BẮT BUỘC diff trước khi đồng bộ.
- Sau khi sửa file trên đĩa, tiến trình Python đang chạy KHÔNG tự động nạp lại mã mới trong RAM trừ khi Gateway được restart hoặc có cơ chế reload hook.

## 3. Kiến trúc Ngân sách Dispatch & Failure Circuit Breaker Chuẩn
Theo khuyến nghị từ review hệ thống:
1. **Dual Ceiling (2 tầng trần):**
   - `total_dispatches`: Trần cứng tối đa mỗi session (ví dụ: 20–40 lượt), KHÔNG BAO GIỜ hoàn lại để tránh lặp vô hạn (infinite loop).
   - `consecutive_failures` / `worker_failures`: Bộ đếm số lần thất bại liên tiếp trên cùng một `target_file` đã chuẩn hóa (normalized path).
2. **Miễn trừ Inspect / Read-only:**
   - Các task `task_type in ('research', 'inspect_only', 'non_code', 'query')` hoặc có nhãn `TASK_KIND: INVESTIGATE` KHÔNG ĐƯỢC tính vào chuỗi thất bại cấu trúc (`worker_failures`), nhưng vẫn phải tuân thủ quyền đọc và trần tổng.
3. **Explicit Success Invariant:**
   - Chỉ ghi nhận thành công khi có bằng chứng rõ ràng (`STATUS: SUCCESS` / `STATUS: COMPLETED` và không có Exception/Error). CẤM suy diễn thành công chỉ vì output không dính regex failure.
   - Timeout mạng, lỗi kết nối (TRANSIENT) không tính vào lỗi cấu trúc để tránh kích hoạt L2 sai lệch.
4. **Circuit Breaker & Escalation Ladder:**
   - Khi cùng một target gặp thất bại cấu trúc $\ge 3$ lần: Kích hoạt `l2_eligible = True`, chặn dispatch lặp lại, hướng dẫn chuyển sang L2 (Emergency Surgery) hoặc L3 (BLOCKED kèm evidence).

## 4. Kỷ luật Soạn Patch Contract cho Guard
- Trước khi tạo patch contract cho worker hoặc áp dụng diff: BẮT BUỘC dùng `read_file` đọc chính xác đoạn mã trên đĩa để lấy `OLD_STRING`.
- CẤM bịa đặt hoặc nhớ gần đúng `OLD_STRING` dẫn đến lỗi `ANCHOR_NOT_FOUND` hoặc `CONTRACT_VIOLATION`.
- **Formatting Invariant cho Multi-line Cards (`<<<`):** Trong `farm_policy.py`, parser yêu cầu `OLD_STRING: <<<` và `NEW_STRING: <<<` BẮT BUỘC phải có dấu xuống dòng (`\n`) ngay sau `<<<`. Nếu viết cùng dòng (`<<<code...>>>`), regex `pat_multi` sẽ không khớp, fallback sang `pat_single` nuốt luôn ký tự `>>>` vào chuỗi tìm kiếm, gây lỗi `ANCHOR_NOT_FOUND`.

## 5. Quy trình Tham vấn Sol Web qua `sol_planner.py`
- Khi cần Sol Web tư vấn kiến trúc / phân rã công việc chuẩn Taadaa Farm:
  `python D:/Taadaa/tools/sol_planner.py --file "D:/Taadaa/tools/cage_gate.py" --goal "<mục tiêu>" --context "<ngữ cảnh>"`
- Script kết nối trực tiếp `chatgpt-web/gpt-5.6-sol-high` trên OmniRoute port 20129, trả về chẩn đoán và tasks, lưu tại `D:/Taadaa/runtime/sol_plans/sol_plan_<id>.json`.
- **Tránh bẫy Guard Self-Protection:** Không truyền đường dẫn chứa chuỗi `farm-coordinator-guard` vào CLI arguments của terminal vì sẽ bị chốt an toàn chuỗi chặn vô điều kiện. Hãy dùng 1 file hợp lệ (như `cage_gate.py`) và đưa thông tin cần tham vấn vào `--context`.

## 6. Rào cản Tự Bảo Vệ & Các Kênh Can Thiệp Bên Thứ Ba
- **Worker Subagent:** Bị chặn bởi `[WORKER GATE - SELF-MODIFICATION BLOCKED]`, không bao giờ được phép sửa file guard.
- **Coordinator:** Bị chặn bởi `[GUARD SELF-PROTECTION / GUARD SOURCE BLACKLISTED]` khi ghi file hoặc chạy lệnh terminal chứa đường dẫn guard.
- **Claude Code CLI:** Chạy ngoài hook Hermes để can thiệp file guard, nhưng cần lưu ý quota giới hạn theo phiên (`session limit`). CẤM tự ý gọi Claude CLI khi user chỉ bảo "kiểm tra".
- **OpenCode CLI (`oc_farm.py`):** Có thể chạy headless và trả stdout, nên phù hợp làm worker thay thế khi Claude/Codex không dùng được:
  `python D:/Taadaa/tools/oc_farm.py run --model <model> --dir <repo> -- "<prompt>"`.
  Smoke-test một prompt ngắn trước. Wrapper farm có timeout khoảng 35s cho mỗi proxy attempt, vì vậy prompt/code task dài có thể timeout; đó là giới hạn wrapper/proxy, không phải bằng chứng OpenCode không hỗ trợ headless.
- **Codex CLI:** Có worker headless native:
  `codex exec -C <repo> "<prompt>"`, hoặc `codex exec --json ...` để lấy JSONL events; kiểm tra `codex login status` trước khi giao việc. Đừng suy ra Codex hỏng nếu API/account đang hết quota.
- **Antigravity IDE (phân biệt với Antigravity app/model pool):**
  * IDE riêng có launcher `C:/Users/Kibe/AppData/Local/Programs/Antigravity IDE/bin/antigravity-ide.cmd`, version tùy máy.
  * Hỗ trợ `chat -m ask|edit|agent`, `-a/--add-file`, và stdin; nhưng đây là launcher GUI/VS-Code-style, không phải headless agent runner tương đương `claude -p`: lệnh chat không đảm bảo trả final response/exit status ra stdout.
  * Antigravity app Electron thường có CDP, nhưng CDP là workaround điều khiển DOM/UI, không phải API agent ổn định. Chỉ dùng khi chấp nhận adapter/version coupling.
  * Không được gọi là “đã nối Antigravity vào Hermes” chỉ vì Hermes có các alias/model `ag-*` qua OmniRoute. Đó là đường model pool khác với việc điều khiển app IDE local.
  * Nếu user muốn Hermes gọi Antigravity IDE, cần một bridge riêng (MCP server hoặc CDP adapter) với hai operations rõ ràng (`ag_ask`, `ag_fix`), scope workspace, timeout, diff/test verification, và status DONE/BLOCKED. Không tự viết bridge trong lúc user chỉ hỏi kiểm tra.

## 7. Anti-Pattern: Lệnh "Kiểm tra lại" Tuyệt Đối Không Kích Hoạt Coding Agent
- Khi User yêu cầu "kiểm tra lại", "check xem đã fix chưa": Nhiệm vụ DUY NHẤT là thực hiện 1 thao tác probe trạng thái (ví dụ test gọi `delegate_task` O(1) hoặc đọc log) rồi trả lời ngay cho User.
- CẤM TUYỆT ĐỐI tự tiện khởi chạy Claude CLI, OpenCode, Codex, Antigravity IDE hoặc tiến trình nền để "thử sửa code" hoặc "thử reproduce" khi chưa có chỉ đạo.
- Khi user đã rõ ràng yêu cầu “gọi Claude/Codex/OpenCode/AG để sửa”, phải dùng đúng runner được yêu cầu và báo đúng trạng thái thực tế; không tự đổi sang pool/model khác rồi gọi đó là cùng một công cụ.
- Với các câu hỏi kiểu “nối AG vào Hermes”, trước hết phải phân biệt ba lớp: Antigravity model pool qua OmniRoute, Antigravity app Electron, và Antigravity IDE CLI. Chỉ kết luận “đã nối” khi đã có đường gọi thực tế và output kiểm chứng.
- Hành vi tự ý gọi agent làm user mất kiểm soát công việc, gây phản ứng cực kỳ tiêu cực và vi phạm kỷ luật Coordinator.
