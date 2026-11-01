# Pipeline Over-Engineering Paralysis & Scoped Transaction Architecture

## 1. Bối cảnh & Hiện tượng "Bại liệt hệ thống"
Khi một pipeline tự động hóa sửa code (`unified_patch_pipeline.py`) được thiết kế với quá nhiều tầng phòng thủ chặt chẽ nhưng thiếu ranh giới rõ ràng:
- **Hiện tượng:** Pipeline liên tục rơi vào trạng thái `PATCH_FAILED` $\rightarrow$ `FAIL-CLOSED` $\rightarrow$ `ROLLBACK` sạch mọi thay đổi, kể cả khi AI đã sinh ra plan sửa code hoàn toàn chính xác.
- **Hệ quả dây chuyền:** 
  1. Pipeline rollback khiến công việc không tiến triển.
  2. Watchdog báo cáo FAIL liên tục.
  3. Agent ở các session loay hoay tìm cách quét đĩa, gõ lệnh thử nghiệm vòng quanh $\rightarrow$ bị các Guard đập đầu hàng loạt (`GUARD_SEARCH_FILES_ROOT`, `GUARD_RECURSIVE_GREP`, `GUARD_PYTHON_WALKER`, `GUARD_DEVICE_LOCK_REQUIRED`).
  4. Hệ thống phòng thủ chạy 100% công suất nhưng hệ thống sản xuất đạt 0% sản lượng thi công.

---

## 2. Ba Nguyên Nhân Cốt Lõi (Root Causes)

### A. Repository-Wide Baseline Hash Sweep ($O(N)$ vs $O(1)$)
- **Sai lầm kiến trúc:** Chụp SHA256 của toàn bộ file dirty và untracked trong repo tại bước S0 Precheck (`git status -z --untracked-files=all`). Trên một repo làm việc thực tế với >500 file nháp, test, log, artifact, bất kỳ công cụ tiện ích nào chạy trong pipeline (như `find_existing_logic.py`) ghi thêm 1 dòng receipt token vào đĩa cũng làm thay đổi working tree.
- **False Positive:** Cơ chế phát hiện sửa lén (Scope Gate) thấy hash của file ngoài scope bị lệch $\rightarrow$ quy kết là Worker phá hoại và tự động kích hoạt Full Rollback.

### B. Vòng Đời File Rác Nằm Chung Git Working Tree
- Các file tiện ích như `find_existing_logic_receipts.jsonl`, cache `farm_logic_index.json` được ghi trực tiếp vào thư mục mã nguồn repo thay vì thư mục runtime (`D:/Taadaa/runtime/audit_logs/`).
- Cache có TTL quá ngắn (24h) khiến pipeline mỗi lần chạy lại tốn 30s-60s để reindex toàn bộ AST cây mã nguồn, dễ dính timeout ở S0.

### C. Ép Buộc Canary Máy Thật Cho Repo Công Cụ Hạ Tầng
- Chốt chặn an toàn thiết bị (Gate 6) áp dụng mặc định cho toàn bộ thư mục `D:/Taadaa/*` mà không phân biệt repo sản phẩm (`tiktok-*`, `automation-core`) với repo hạ tầng CLI (`tools`, `Hermes`).
- Khi sửa code trên repo `tools`, hệ thống từ chối cờ `--no-canary`, bắt buộc chạy Canary trên điện thoại Android, trong khi `canary_runner` không hỗ trợ target `tools` $\rightarrow$ sinh lỗi `CANARY_FAILED`.

---

## 3. Kiến Trúc "Scoped Transaction" Khắc Phục Triệt Để

### 1. Giới Hạn Baseline Trong Phạm Vi Tracked Files
- Tại bước S0 Precheck của Pipeline: chuyển `git status` sang `--untracked-files=no`.
- Bỏ cơ chế duyệt và chụp hash hàng trăm file untracked/nháp. Pipeline chỉ theo dõi các file đã được Git theo dõi (tracked), cô lập hoàn toàn các file nháp tạm ngoài luồng.

### 2. Tách Biệt Hoàn Toàn Runtime Artifacts Khỏi Git Tree
- Chuyển toàn bộ receipt, cache, state chạy ngầm sang thư mục `D:/Taadaa/runtime/` hoặc khai báo tường minh trong `.gitignore`.
- Tăng TTL của index cache lên 30 ngày để đảm bảo tốc độ precheck luôn đạt $O(1)$ (<0.2 giây).

### 3. Tầng Thi Công Ưu Tiên Số 0 (Exact Patch Direct Layer O(1))
- Ngay tại bước S2 Patch: trước khi dispatch Worker qua các mô hình AI đắt đỏ (Sol / Agy / Haiku / Claude CLI), pipeline ưu tiên thử áp dụng patch trực tiếp bằng `apply_patch.py`.
- Nếu S1 Plan đã cung cấp exact anchor duy nhất (`wc -l == 1`), `apply_patch.py` áp dụng thành công trong 0.05s, không tiêu tốn token và hoàn toàn miễn nhiễm với sự cố hết quota của Worker.

### 4. Phân Biệt Repo Hạ Tầng (Tooling) vs Repo Thiết Bị Farm
- Trong logic suy luận Gate 6 (`is_farm_device_related` / `is_taadaa_farm_repo`): kiểm tra tên repo. Nếu repo là `tools` hoặc `Hermes`, chấp nhận cờ `--no-canary` hợp lệ vì đây là công cụ dev/CLI, không gắn với vòng đời app trên Samsung S7.

### 5. Scoped Diff Hash Integrity Check
- Hàm tính `get_git_diff_hash` tại điểm Hold (S5) và điểm Confirm bắt buộc hỗ trợ lọc theo `target_files`. Tính toàn vẹn của diff chỉ đối soát trên các file mục tiêu được chỉ định trong Scope, không bị các thay đổi ngoài lề làm sai lệch.
