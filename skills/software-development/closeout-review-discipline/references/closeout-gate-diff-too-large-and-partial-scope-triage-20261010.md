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
       - **Batch 1 (Policy, Documentation & Data Registry):** Các file `docs/*.md`, `data/*.json`, `AGENTS.md` (thường < 15KB). Review qua gate và commit trước.
       - **Batch 2 (Core Code Logic & Unit Tests):** Các file `scripts/*.py`, `tests/*.py` (thường < 30KB). Review qua gate và commit sau.
       *Lợi ích:* Giữ nguyên vẹn toàn bộ docstrings và tài liệu kỹ thuật mà vẫn bảo đảm blast radius <= 30KB cho mỗi lượt review.
     * **Phương án B — Rút gọn Docstrings O(1) (Khi 1 file đơn lẻ vượt trần):**
       Nếu riêng 1 file code/test đã sát ngưỡng 30KB:
       - Rút gọn các chuỗi docstrings dài dòng, comment giải thích rườm rà ở đầu file và các test docstrings.
       - Giữ nguyên 100% logic code, assertions và coverage kiểm thử.
       - Sau khi rút gọn, kiểm tra lại `git diff <BASE>..HEAD -- <FILES> | wc -c` phải nghiêm ngặt `< 30000` bytes trước khi chạy lại Gate.
