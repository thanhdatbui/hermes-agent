# Mechanical Planner & Worker Gateways Architecture (Claude CLI Approved)

> Reviewer Status: VERDICT: APPROVED by Claude Code CLI (36/36 tests passed).
> Core Repositories & Modules: `D:/Taadaa/tools/dispatch_planner.py`, `D:/Taadaa/tools/dispatch_worker.py`.

---

## 1. Bối cảnh & Nguyên lý Thiết kế: "Dẹp Prompt Suông — Khóa 100% Bằng Gate Cơ Học"

Tránh mọi sự phụ thuộc vào lời nhắc nhở mềm (soft prompts/system prompt instructions). Toàn bộ luồng kiểm tra quota, chuyển đổi fallback, phân loại lỗi và kích hoạt quyền cứu sinh được code hóa cứng trong Python scripts:

```
[Mục tiêu Lập Kế Hoạch]
         │
         ▼
 [dispatch_planner.py]
  ├── Tier 1: Claude Sonnet CLI (claude_worker.py --role planner)
  │    └── Gate: check_claude_quota() fail-closed (5h >= 85%, weekly >= 90%, stale/error)
  ├── Tier 2: Sol Planner (sol_planner.py :20129) [Timeout 300s, forward --file & --context]
  └── Tier 3: Coordinator Fallback (exit 100, emit [PLANNER_FALLBACK_COORDINATOR] token)

[Mục tiêu Thi Công Code]
         │
         ▼
 [dispatch_worker.py]
  ├── Tier 1: Sol Web Worker (sol_worker.py :20129) [100% Free]
  ├── Tier 2: Agy CLI (ag_cli.py fix) [29 acc Pro pool via wincred CredWriteW]
  ├── Tier 3: Claude Haiku CLI (claude_worker.py --role worker)
  └── Tier 4: Coordinator Fallback (emit [WORKER_FALLBACK_COORDINATOR] token -> L2 Emergency Surgery)
```

---

## 2. Đặc Tả Chi Tiết Planner Gateway (`dispatch_planner.py`)

### A. Kiểm Tra Quota Fail-Closed (`check_claude_quota`)
- **Nguồn dữ liệu:** `claude_worker.get_claude_quota_status()`, trả về thang đo 0–100 (`fh` cho 5-hour, `sd` cho weekly).
- **Quy tắc Fail-Closed:**
  - Nếu `quota is None` hoặc `quota["is_stale"] is True` $\rightarrow$ Trả về `(False, "quota_unavailable_or_stale", ...)` ngay lập tức.
  - Nếu xảy ra ngoại lệ bất kỳ trong quá trình đọc $\rightarrow$ Trả về `(False, "quota_check_error", ...)`.
  - Tuyệt đối cấm fallback về `True` khi mất dữ liệu quota.
- **Ngưỡng khóa cứng (Hard Thresholds theo `AGENTS.md`):**
  - 5-Hour: `fh >= 85.0` $\rightarrow$ Chặn.
  - Weekly: `sd >= 90.0` $\rightarrow$ Chặn.
  - Các giá trị an toàn (`fh < 85.0`, kể cả `1.0%` hoặc `80.0%`) được chạy bình thường.

### B. Phân Biệt Lỗi Hạ Tầng vs Lỗi Ngữ Nghĩa
- **Lỗi ngữ nghĩa / Từ chối (Semantic Rejection / Refusal / Invalid Input):**
  - Trả về mã lỗi sớm (`return rc`), ghi audit `REJECTED_SEMANTIC`.
  - Tuyệt đối KHÔNG tự động fallback mù quáng sang Sol Planner khi input người dùng bị sai cú pháp hoặc yêu cầu bị từ chối rõ ràng.
- **Lỗi hạ tầng (Timeout 124, Quota 125, Crash mạng):**
  - Ghi audit `FAILED` và tự động kích hoạt Tier 2 (Sol Planner).
  - Tier 2 bắt buộc truyền đủ `--file` và `--context`.

### C. Cơ Chế Thoát Hiểm Cứu Sinh (Tier 3 Coordinator)
- Khi cả Tier 1 và Tier 2 đều thất bại do lỗi hạ tầng, script xuất ra:
  ```text
  [PLANNER_FALLBACK_COORDINATOR] {"status": "PLANNER_FALLBACK_COORDINATOR", ...}
  ```
- Thoát với exit code `100`.
- Coordinator trong session chính nhận được mã này được cấp quyền cơ học tự lập plan / chốt Patch Contract O(1) mà không bị vi phạm rule.

---

## 3. Đặc Tả Chi Tiết Worker Gateway (`dispatch_worker.py`)

### A. Thứ Tự Tier Tối Ưu Chi Phí & Tốc Độ
1. **Tier 1 (Primary):** `Sol Web Worker` (`sol_worker.py` qua `:20129`) — 100% Free, tận dụng reasoning pool 115 accounts.
2. **Tier 2 (Fallback 1):** `Agy CLI` (`ag_cli.py fix`) — 29 accounts Google One Pro, đồng bộ OAuth token vào Windows Credential Manager (`gemini:antigravity`) trước mỗi lần gọi.
3. **Tier 3 (Fallback 2):** `Claude Haiku CLI` (`claude_worker.py --role worker`) — Anthropic fallback cuối cùng.
4. **Tier 4 (Cứu sinh):** Coordinator Emergency Surgery O(1).

### B. Kiểm Tra Cú Pháp Python In-Memory (`_verify_python_syntax`)
- Sau khi worker sửa file `.py`, dispatcher tự động phân tích cú pháp bằng `ast.parse(target.read_bytes(), filename=str(target))`.
- **Lợi ích an toàn vượt trội:** Khác với `py_compile.compile` (tạo rác bytecode `.pyc` trong `__pycache__` làm bẩn working tree và khiến Closeout Reviewer trừ điểm), `ast.parse` kiểm tra 100% cú pháp in-memory, hoàn toàn không có tác dụng phụ ghi đĩa.
- Nếu cú pháp vỡ (`SyntaxError`) $\rightarrow$ Không chấp nhận diff, tự động chuyển tier tiếp theo để sửa lại.

### C. Cách Ly Token Cứu Sinh `[WORKER_FALLBACK_COORDINATOR]`
- Chỉ in token `[WORKER_FALLBACK_COORDINATOR]` khi lần thử cuối thất bại do lỗi hạ tầng (`TIMEOUT`, `QUOTA`).
- Nếu worker trả về `NEEDS_INPUT` (cần user làm rõ) hoặc `ENV` $\rightarrow$ Return ngay, CẤM in token cứu sinh để Coordinator không được tự ý sửa mò.

---

## 4. Thiết Quân Luật Về Timeout
- **Planner Timeout:** Mặc định $\ge$ **300s (5 phút)**.
- **Worker Timeout:** Mặc định $\ge$ **180s - 300s (3 - 5 phút)**.
- Reasoning models (Sonnet, Sol Web High, Agy CLI Agent) cần 20s–45s chỉ để suy nghĩ (TTFT). Tuyệt đối cấm đặt timeout ngắn (<60s) làm chém ngang lưng tiến trình đang xử lý.

---

## 5. Danh Mục Kiểm Thử (36/36 Tests Passed 100%)
- `D:/Taadaa/tools/tests/test_dispatch_planner.py`: 9 tests (kiểm tra positional/flags, fail-closed quota on error/stale/none, boundaries 80%/85%/1%/89%/90%, Tier 1 success, Tier 2 forward --file, Tier 3 token emission).
- `D:/Taadaa/tools/tests/test_dispatch_worker.py`: 27 tests (normalize content, failure classification, snapshot diffs, target-only edits, syntax check verification, token isolation on quota vs needs_input).
