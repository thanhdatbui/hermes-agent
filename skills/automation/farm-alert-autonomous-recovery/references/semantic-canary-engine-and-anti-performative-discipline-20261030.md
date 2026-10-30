# Semantic Canary Engine, Tiered Model Ladder & Anti-Performative Canary Discipline (2026-10-30)

## 1. Bản Chất Bệnh "Canary Hình Thức" (Performative Canary Trap)
- **Triệu chứng vi phạm:** Khi vá logic nghiệp vụ phức tạp trong monolith (như `feed_swipe_smoke.py`), canary chạy lệnh cố định lướt 2 video For You generic (`--recovery-test-swipes 2`), kết thúc với exit 0 và được cấp cờ `.canary_passed`.
- **Hậu quả chết người:**
  - Nhánh code vừa sửa (ví dụ: fallback khi tab con Following/Friends bị rỗng hoặc lỗi mạng) thực tế **chưa bao giờ được thực thi** trên máy thật trong lượt test đó (do biến random tab decision `videos_until_tab_decision` chưa đếm tới).
  - Kết quả PASS là **PASS giả**. Khi mở fleet 80 máy chạy thật, toàn bộ dàn máy đồng loạt gãy cùng một lỗi (`detector-miss:feed not confirmed` trên 34 máy).
  - Phản ứng gay gắt của User: *"Ủa t đã ép cổng run canary phải chạy đúng cái lỗi vừa vá mà?... H chạy đúng bản vá của session h làm sao. Đéo đc thì gắn não llm cho nó khôn đi... Thiết kế của gate a-z như nào thì bê nguyên vào làm não cho gate canary"*.

---

## 2. Kiến Trúc Semantic Canary Engine (Đồng Nhất Thang Gate A-Z)
Thay vì dùng rule regex đường dẫn tĩnh thô thiển (`canary_matrix.json`), Canary Plan được gắn não LLM theo đúng thang mô hình của Gate B (`gate_b_planner.py`):

```
Git Diff ──▶ canary_plan.py (Tiered LLM: Gemini Web -> Sol -> Claude CLI)
                 │
                 ├──▶ cli_args_override (ép máy thật chạy đúng nhánh code vừa vá)
                 ├──▶ log_assertions (required_patterns & forbidden_patterns)
                 │
                 ▼
         canary_runner.py (Thực thi máy thật + Hậu kiểm file log.jsonl cơ học)
                 │
                 ├── Khớp required_patterns >= min_matches ──▶ CANARY_VERDICT: PASSED
                 └── Thiếu pattern hoặc dính forbidden ──▶ CANARY_FAIL (Đánh rớt ngay)
```

### Thang Mô Hình Ưu Tiên (Tiered Ladder):
1. **Ưu tiên 1 (Primary):** `gemini-web` (Argon 4 Pool qua OmniRoute `:20129`, timeout 120s, miễn phí token).
2. **Fallback 1:** `gpt-web-sol` (Sol Worker qua OmniRoute `:20129`, timeout 120s).
3. **Fallback 2 (Chặn cuối):** `claude-cli` local qua `stdin` (timeout 150s, tránh nghẽn pipe cmd.exe).

---

## 3. Quy Trình Vận Hành Bắt Buộc

### Bước 1: Sinh Semantic Plan từ Git Diff
Lệnh lập plan:
```bash
python D:/Taadaa/tools/canary_plan.py --repo "<path_repo>" --base HEAD~1 --machines <N> --out-file "<path_plan.json>"
```
- Planner đọc `git diff`, phân tích hàm bị ảnh hưởng và tự động sinh `cli_args_override` (ví dụ: `--feed-distribution '{"for-you": 0.0, "following": 0.5, "friends": 0.5}' --recovery-test-swipes 4`).
- Tự động sinh `log_assertions` chứa chuỗi/regex bắt buộc phải có trong `log.jsonl` sau khi chạy xong.

### Bước 2: Runner Thực Thi & Hậu Kiểm Cơ Học
Lệnh chạy:
```bash
python D:/Taadaa/tools/canary_runner.py --repo "<path_repo>" --plan "<path_plan.json>" --machine <N> --row <row> --force-preempt
```
- Runner tự động ghi đè tham số CLI thực thi máy thật theo `cli_args_override`.
- Khi runner xong, **bắt buộc đọc `log.jsonl` và `summary.txt` đối soát `log_assertions`**:
  * Nếu không kích hoạt nhánh code vừa sửa (thiếu required patterns) $\rightarrow$ **Đánh rớt ngay lập tức** (`SEMANTIC_ASSERTION_FAILED`), cấm cấp pass!
  * Nếu dính lỗi cấm (forbidden patterns) $\rightarrow$ Đánh rớt ngay lập tức.
  * Chỉ khi thỏa mãn cả trạng thái runner, log assertion và WinRT OCR màn hình đích mới cấp `.canary_receipt.json`.
