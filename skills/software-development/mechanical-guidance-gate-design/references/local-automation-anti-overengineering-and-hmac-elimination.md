# Local Automation Anti-Overengineering & HMAC Debt Elimination

## 1. Single-Host Trust Boundary Reality
Khi toàn bộ tác vụ tự động hóa (Hermes Coordinator, Worker CLI, Gate scripts, state files) đều chạy trên **cùng một máy Windows host dưới cùng một quyền người dùng (User `Kibe`)**:
- Việc dùng HMAC-SHA256 (`hmac.key`, `pipeline.key`, `vision_guard.key`) để ký state/receipts là **Security Theater (Over-engineering thuần túy)**.
- **Quy tắc bất biến:** Không bao giờ ký những thứ mà chính tiến trình ký có toàn quyền đọc, tạo mới hoặc ghi đè secret key.

## 2. Chuẩn Cơ Học Thay Thế (TLIS - Taadaa Local Integrity Standard)
Thay vì dùng cryptographic signing rườm rà dễ gãy và sinh nợ kỹ thuật, sử dụng 4 cơ chế cơ học chuẩn $O(1)$:
1. **Plain JSON:** State minh bạch, đọc được bằng mắt người và công cụ debug, có `schema_version`, `run_id`, và `status`.
2. **Atomic Write:** Ghi ra file tạm (`<target>.tmp.<pid>`) trong cùng thư mục rồi dùng `os.replace` để tráo đổi nguyên tử, chống hỏng file khi crash/đứt nguồn.
3. **OS-Level File Locking:** Dùng `msvcrt.locking` (trên Windows) hoặc `fcntl.flock` (trên POSIX) để khóa file liên tiến trình (`RepoLock`), chống race condition khi chạy song song.
4. **Git Diff Tracking:** Giám sát thay đổi code và chống sửa trộm bằng `git status --porcelain` và snapshot SHA256 nội dung của baseline dirty files ngoài scope.

## 3. Thang Điều Phối Gate B & Gate C Thực Chiến
- **Gate B (Planner Timeout):** Gemini Web qua CDP/Argon pool cần tối thiểu **120s** để suy luận bài toán hiện trường và failover khi dính acc lỗi; không được ép timeout 15s gây đứt chuỗi. Thang dự phòng: `Gemini Web (120s)` -> `Claude CLI (150s)` -> `Sol Worker (120s)`.
- **Target File Context Injection:** Khi gọi Planner, bắt buộc truyền tối thiểu 100 dòng đầu của target file (`--target-file`) để model thấy code thật, cấm để model đoán mò dẫn đến `old_string` rỗng hoặc không duy nhất. Anchor bắt buộc 3-5 dòng context (`count == 1`).
- **Gate C (Worker Tiering):** Ưu tiên hàng đầu là **Qoder Worker (DeepSeek-Flash - Tier 0)** -> **Sol Worker (Tier 1)** -> **Agy CLI (Tier 2)** -> **Haiku CLI (Tier 3)**.

## 4. Tách Biệt Closeout Gate Cơ Học vs LLM Scoring
- Closeout Gate v2 (`closeout_v2.py`) là kiểm tra xác thực cơ học $O(1)$: kiểm tra cú pháp (`py_compile`), chạy focused test, và ghi log audit trong < 0.1s.
- Điểm số `100/100` ở nhánh operational/clean working tree là kết quả tĩnh chuẩn hóa, không phải LLM ảo giác hay Sol chấm điểm.
