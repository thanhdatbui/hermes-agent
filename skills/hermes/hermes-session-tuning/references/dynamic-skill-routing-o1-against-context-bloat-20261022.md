# Dynamic Skill & Rule Routing O(1) Against Context Bloat (2026-10-22)

## 1. Bối Cảnh Thực Tế & Tử Huyệt Context Bloat
Hermes Agent trên Windows quản lý 190+ skills cùng hàng nghìn ký tự Persistent Memory và Invariants.
Khi tất cả skills được nạp tĩnh đồng thời vào system prompt:
1. **Token Bleeding Baseline:** Tiêu hao 60k–100k input tokens ngay trước khi user đưa ra yêu cầu đầu tiên.
2. **Sớm chạm Compression Threshold:** Session nhanh chóng chạm ngưỡng nén 300k tokens (`threshold: 0.3`).
3. **Hiện tượng `[SKILL_PRUNED]`:** Quá trình summarization nén buffer theo khoảng cách lịch sử chứ không theo mức độ liên quan tới task hiện tại. Khi đó, các kỹ năng hoặc luật an toàn cốt lõi có nguy cơ bị rơi rụng.

---

## 2. Giải Pháp: Dynamic Skill & Error Routing O(1)
Thay vì nạp toàn bộ 190 skills tĩnh:
- **Build Index (`tools/build_skill_index.py`):** Quét metadata front-matter (`name`, `category`, `description`, `size_tokens_est`) xuất ra `tools/skills_index.json` trong <0.5s.
  - **BẮT BUỘC** chạy lại mỗi khi thêm/sửa SKILL.md bất kỳ.
  - **STALE INDEX TRAP**: Tests hoặc gate gọi `check_index_freshness()` sẽ trả về False (→ FAIL_CLOSED_STALE_INDEX) nếu bất kỳ SKILL.md nào mới hơn index. Phải chạy `python D:/Taadaa/tools/build_skill_index.py` trước khi chạy closeout gate hoặc test có freshness check.
- **O(1) Keyword Matcher (`tools/skill_lookup.py`):**
  - Chấm điểm keyword theo tên, category và description.
  - **Khóa cứng 5 Core Invariants (Pinned):** Luôn tự động nạp `taadaa-farm-ops-rules`, `farm-anti-overengineering`, `session-close-protocol`, `evidence-first-delivery`, `agent-verification-loop`.
  - **Fail-Closed:** `NO_MATCH_FALLBACK` chỉ trả về 5 Pinned Core Skills. TUYỆT ĐỐI CẤM nạp lại toàn bộ 190 skills.
  - **Freshness Check chuẩn xác**: So sánh `mtime` của từng `SKILL.md` trong 2 cấp `category/skill_name/SKILL.md`, KHÔNG chỉ mtime thư mục category. Trả về `[INDEX_STALE]` nếu bất kỳ SKILL.md nào mới hơn index.
  - Returns `latency_ms`, `total_indexed` trong result dict.
- **Selective Loader (`tools/load_selected_skills.py`):**
  - Chống Path Traversal bằng `is_relative_to(skills_root)`.
  - Escape thẻ HTML comment `-->` thành `--&gt;`.

---

## 3. Tử Huyệt Pinned References 100k Chars & Giải Pháp `clean_skill_content`
`session-close-protocol` và `evidence-first-delivery` có phần `## References` dài tới ~100.000 ký tự.
`clean_skill_content()` trong `skill_injector.py`:
1. Cắt bỏ từ `\n## References` trở xuống, thêm `[TRUNCATED REFERENCES FOR CONTEXT BUDGET]`.
2. Cap nội dung mỗi skill ở 3000 ký tự.
3. Phân bổ 2 tầng ngân sách: `max_pinned_budget = 10000`, phần còn lại cho matched skills.
4. Hard clamp cuối: `full_context = full_context[:effective_max]`.

---

## 4. Cơ Giới Hóa: `skill_injector.py` → `dispatch_worker.py`
- `inject_skill_context(task_prompt, tier, max_context_chars=15000, max_pinned_budget=10000)`.
- `effective_max = 8000 if tier == "T0" else min(max_context_chars, 15000)`.
- Fail-closed khi index stale/missing: trả về `context_block=""`, dispatch tiếp tục với raw prompt (KHÔNG block dispatch).
- Điểm chèn trong `dispatch_worker.main()` trước Tier 1:
  ```python
  effective_prompt = args.prompt
  if getattr(args, "enable_skill_injection", True):
      try:
          from skill_injector import inject_skill_context
          inj = inject_skill_context(args.prompt, tier="T1", max_context_chars=15000)
          if inj.context_block:
              effective_prompt = f"{inj.context_block}\n\n---\n[TASK CONTRACT]\n{args.prompt}"
          audit("skill_injection", 1, inj.status, inj.reason, workdir, args.file, 0, correlation_id)
          _log(f"Skill injection: {inj.status} ({len(inj.injected_skill_ids)} skills, {inj.used_chars} chars, cid={correlation_id})")
      except Exception as exc:
          audit("skill_injection", 1, "FAIL_CLOSED_ERROR", str(exc), workdir, args.file, 1, correlation_id)
          _log(f"Skill injection failed (fallback), cid={correlation_id}: {exc}")
  ```
- CLI flag `--no-skill-injection` để bypass khi debug.
- `effective_prompt` dùng cho cả Tier 1, Tier 2 Attempt 1 và Attempt 2 retry.

---

## 5. Bài Học Sycophancy / Flip-Flop (Operator Chấn Chỉnh)
Khi user nói "phức tạp quá", phản xạ sycophancy là quay xe 180°. Operator phản ứng: *"trên nói 1 kiểu xuống nd k cần thiết"*.
CẤM flip-flop khi Operator nói chê phức tạp. Phân định rõ: từ chối framework RAG nặng bên ngoài; nhưng giữ vững kiến trúc O(1) nhẹ đã đề xuất. Giải thích dân dã: *"O(1) là một nhát ăn ngay, đúng bệnh đúng thuốc"*.

---

## 6. Closeout Gate History
- **Phân hệ 1** (build_skill_index + skill_lookup + load_selected_skills): **85/100 APPROVED** (Strict).
  - Reviewer yêu cầu: freshness check đúng mtime SKILL.md; đồng bộ DEFAULT_SKILLS_DIR; path traversal test; integration test với thư mục production thật.
- **Phân hệ 2** (farm_error_kb): 61/100 **REJECTED** → rút khỏi scope (không có integration point, risk schema mismatch với `inspect_machine.py`).
- **Phân hệ 3** (skill_injector + dispatch wiring): 77/100 tại thời điểm đóng phiên. Remediation chưa hoàn tất:
  - Đã fix stale index trap (check_index_freshness).
  - Đã thêm structured audit với correlation_id.
  - Còn todo: full test suite pass với audit record count update.

---

## 7. Test Coverage (43 tests xanh tại thời điểm Phân hệ 1 APPROVED)
- `tests/test_build_skill_index.py`, `tests/test_skill_lookup.py`, `tests/test_pinned_always_returned.py`
- `tests/test_load_selected_skills.py` (path traversal `../../../etc/passwd` rejection)
- `tests/test_index_staleness_warning.py` (staleness ở level SKILL.md, không phải category dir)
- `tests/test_skill_injector.py` (budget, T0 tier, fail-closed stale, hard clamp ceiling)
- `tests/test_dispatch_worker_skill_injection.py` (wiring, bypass, prompt content)
- `tests/test_dispatch_worker.py` (existing 20 tests; `test_main_audit_correlation_id_consistent` cần update count ≥1 thay vì ==1 vì skill_injection audit record nay được thêm mới)
