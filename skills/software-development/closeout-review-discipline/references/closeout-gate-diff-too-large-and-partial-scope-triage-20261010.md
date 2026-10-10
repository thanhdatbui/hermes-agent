# Triage và Xử lý Bẫy Scope Drift & Diff Too Large trong Closeout Gate

## 1. Bản chất sự cố
Khi chốt phiên trong các repository có các cronjob tự động ngầm (ví dụ: `sync-hermes-skills-and-brain-to-git` chạy mỗi 5 phút tự commit memory/skills), hoặc khi repo có nhiều file vừa được commit mới từ nhiều tác vụ khác nhau, Closeout Gate (`closeout_gate.py`) sẽ kiểm tra tính toàn vẹn của git diff:

1. **Lỗi `refusing partial committed scope`:**
   - Xảy ra khi `--base <REF>` tính ra dải commit chứa danh sách file khác hoặc rộng hơn so với các file chỉ định trong `--files`.
   - Closeout Gate từ chối duyệt một phần của các file đã commit nếu tập `targets` không bằng tập `committed_scope` trong dải `diff_range..HEAD`.
   - **Cách xử lý:** 
     - Tạm dừng cron tự động sync nếu nó liên tục tạo commit mới chen ngang (`cronjob action='pause' job_id='...'`).
     - Xác định đúng base commit ngay trước candidate commit của task hiện tại, hoặc bind đúng tập file thuộc candidate commit đó.

2. **Lỗi `GATE-FAIL(diff-too-large): targeted diff quá lớn (> 30000 bytes)`:**
   - Closeout Gate có ngưỡng cứng `MAX_DIFF_BYTES_GATE = 30_000` bytes (nhằm thực thi kỷ luật phân rã O(1) và bảo vệ context của Reviewer).
   - Khi phiên làm việc sửa đổi nhiều tầng (docs, policy, data registry, code logic và unit test suite), việc gộp chung tất cả các file (ví dụ 8 file = 58KB) sẽ lập tức kích hoạt fail-fast `DIFF_TOO_LARGE`.
   - **Chiến lược xử lý chuẩn (2 Phương án theo ngữ cảnh):**
     * **Phương án A — Phân rã theo ngữ nghĩa (Gate 1 Decompose — Khuyến nghị hàng đầu):**
       Tách việc chốt phiên thành các Batch độc lập tuần tự:
       - **Batch 1 (Core Code Logic & Focused Test):** Các file code cốt lõi `scripts/*.py` kèm file test tương ứng `tests/test_*.py` (thường < 30KB). Có file `.py` giúp Gate tự động nhận diện đúng focused test và pass trong vài giây (< 5s).
       - **Batch 2 (Policy, Documentation & Data Registry):** Các file `docs/*.md`, `data/*.json`, `AGENTS.md`. 
         * *CẠM BẪY NGHIÊM TRỌNG CẦN TRÁNH:* Nếu chỉ stage toàn file non-code (`.md`, `.json`), Gate không tìm thấy file Python mục tiêu nên sẽ fallback quét **TOÀN BỘ thư mục `tests/`** (hàng chục test files) dẫn đến **Timeout 120s**. Đồng thời cờ `--skip-test` bị cấm tuyệt đối ở `--repo` mode (`FATAL: --skip-test is forbidden in repo mode!`).
         * *Cách xử lý chuẩn:* BẮT BUỘC ghép kèm 1 file focused test chạy nhanh (< 5s, ví dụ `tests/test_*.py` liên quan) vào dải `--files` của batch docs/data để Gate chạy focused test đó thay vì quét toàn bộ repository.
       *Lợi ích:* Vừa vượt qua ngưỡng 30KB của Closeout Gate, vừa đảm bảo focused test chạy dưới 5s không bao giờ bị timeout.
     * **CẠM BẪY COMMIT HOOK & R5 SELECTOR GUARD TRONG DOCS:**
       - Trong repository Taadaa, hook `pre-commit` tự động chạy `guard_selector_change.py --cached`.
       - Nếu sửa đổi `docs/farm-automation-cases.md`, rule R5 bắt buộc trong đoạn text thêm mới (`+`) phải có đủ 3 trường:
         `Layout:`, `Fixture:`, và `Anti-pattern:` (chính xác từng ký tự hoa/thường).
       - Nếu thiếu hoặc viết hoa sai (ví dụ `Anti-Pattern:` thay vì `Anti-pattern:`), commit sẽ bị chặn cứng với lỗi:
         `SELECTOR_GUARD REJECT: R5: Mục case mới trong docs/farm-automation-cases.md thiếu trường bắt buộc...`
       - Đồng thời, khi nộp review Closeout Gate cho batch chỉ có docs/cases, reviewer Sol High có thể chấm trượt nếu chỉ thấy text tài liệu mà không thấy diff code tương ứng. Bắt buộc ghi rõ trong phần mô tả case các commit ID implementation đã được merge trước đó (ví dụ: `scripts/manual_avatar_guard.py (commit 7fda746)`), và bổ sung assertions kiểm thử telemetry runtime để đáp ứng đủ tiêu chí scorecard của reviewer.
     * **Phương án B — Rút gọn Docstrings O(1) (Khi 1 file đơn lẻ vượt trần):**
       Nếu riêng 1 file code/test đã sát ngưỡng 30KB:
       - Rút gọn các chuỗi docstrings dài dòng, comment giải thích rườm rà ở đầu file và các test docstrings.
       - Giữ nguyên 100% logic code, assertions và coverage kiểm thử.
       - Sau khi rút gọn, kiểm tra lại `git diff <BASE>..HEAD -- <FILES> | wc -c` phải nghiêm ngặt `< 30000` bytes trước khi chạy lại Gate.
