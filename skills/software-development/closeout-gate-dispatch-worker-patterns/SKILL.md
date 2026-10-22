---
name: closeout-gate-dispatch-worker-patterns
description: Use when closeout_gate rejects dispatch_worker changes.
version: 1.0.0
---

# Closeout Gate Patterns for `dispatch_worker.py`

## Trigger
Use when running `closeout_gate.py` on `D:/Taadaa/tools/dispatch_worker.py` or when a remediation loop struggles to reach 85/100.

---

## 1. Sol Auditor Scoring Model (100 pts)

| Category | Weight | What it checks |
|---|---|---|
| Logic Correctness | 35 | Tier ordering, fallback ladders, snapshot baseline ownership |
| Test Evidence | 25 | Actual pytest log, not mocks alone |
| Telemetry & Obs | 15 | Per-tier, per-attempt audit() calls; JSONL coverage |
| Farm Safety | 15 | Worst-case chain latency, no unbounded timeout |
| Code Architecture | 10 | No duplicate code paths; helpers extracted |

**Threshold:** >= 85 to pass; 80–84 is Grace Band (passes if tests verified).

---

## 2. Known Patterns That Score >= 85

### 2.1 Tier Ordering: Agy Primary → Haiku Fallback
```python
# Tier 1: Agy CLI (ag_cli.py)
snap1 = take_snapshot(workdir, args.file)
rc, output = run_tool([AG_CLI, "fix", ...], cwd=workdir, timeout=args.timeout)
has_changes, diff_reason = verify_changes(snap1, workdir, args.file, output)

if rc == 0 and has_changes:
    audit("agy", 1, "OK", "success", ...)
    return 0

cat = classify_failure(rc, output, diff_reason)
if cat in ("NEEDS_INPUT", "ENV"):
    audit("agy", 1, cat, f"agy_{cat.lower()}", ...)
    return rc or 1

# Tier 2: Haiku fallback — take fresh snapshot to isolate from Agy's partial edits
audit("agy", 1, cat, "fallback_to_haiku", ...)
snap_haiku = take_snapshot(workdir, args.file)   # KEY: isolate from Agy partial edits
rc_h, out_h = run_tool(haiku_cmd(args.prompt), ...)
has_changes_h, _ = verify_changes(snap_haiku, workdir, args.file, out_h)
```

**Critical Invariant (Snapshot Isolation):** Reusing `snap1` across attempts allows Agy's partial/failed edits to be falsely counted as Haiku's contribution. BẮT BUỘC chụp snapshot mới trước mỗi attempt (`snap_haiku = take_snapshot(...)` trước Haiku 1, `snap_attempt2 = take_snapshot(...)` trước Haiku 2) để từng worker/attempt chỉ được nghiệm thu dựa trên đúng diff do chính nó tạo ra.

### 2.2 Haiku Retry Ladder (Quota Fast-Path)
```python
cat_h = classify_failure(rc_h, out_h, diff_reason_h)

if cat_h == "QUOTA":
    audit("haiku", 1, cat_h, "quota_exhausted", ...)
    return rc_h or rc or 1  # DO NOT retry Haiku on QUOTA — hard stop

if cat_h in ("NEEDS_INPUT", "ENV"):
    audit("haiku", 1, cat_h, f"haiku_{cat_h.lower()}", ...)
    return rc_h or 1

# Audit attempt 1 before retrying
audit("haiku", 1, cat_h, "retry_needed", ...)

# Attempt 2: isolate snapshot from Attempt 1 partial edits
snap_attempt2 = take_snapshot(workdir, args.file)
prompt2 = RETRY_PREFIX + args.prompt
rc2, out2 = run_tool(haiku_cmd(prompt2), ...)
has_changes2, _ = verify_changes(snap_attempt2, workdir, args.file, out2)
```

### 2.3 Audit Coverage Requirements (Telemetry Score)
Every outcome MUST emit an `audit()` call with:
- `tier`: "agy" or "haiku"
- `attempt`: 1 or 2
- `category`: OK / NEEDS_INPUT / ENV / QUOTA / NO_DIFF / etc.
- `reason`: descriptive string ("success", "fallback_to_haiku", "retry_needed", "quota_exhausted", "retry_failed")
- `correlation_id`: same UUID across all attempts in one dispatch

### 2.4 Timeout: 60s Default is Correct
- Default of 60s per worker is well-calibrated for the farm.
- Raising to 1200s causes worst-case chain (Agy + 2×Haiku) to reach ~540s → approaches the 600s threshold of the historical "Hermes gateway freeze incident".

---

## 3. Common Rejection Reasons & Fixes

| Rejection Reason | Sol Score Impact | Fix |
|---|---|---|
| Reusing snapshot across attempts | −8 Logic | Isolate snapshots: `snap_haiku` before Haiku 1, `snap_attempt2` before Haiku 2 |
| Haiku retried on QUOTA | −5 Logic, −4 Farm Safety | Add `if cat_h == "QUOTA": return rc_h or 1` before retry |
| Attempt 1 not audited before attempt 2 | −6 Telemetry | Add `audit("haiku", 1, cat_h, "retry_needed", ...)` before `RETRY_PREFIX` |
| Dead code: unused declarations | −3 Architecture | Remove unused imports and constants |
| Timeout raised to 1200s without benchmark | −4 Farm Safety | Keep 60s default |
| Missing test for early exit (NEEDS_INPUT) | −4 Test Evidence | Add test asserting `len(calls) == 1` |

---

## 4. Minimal Focused Test Suite (12 tests)

```python
test_normalize_content_crlf()
test_classify_failure_hierarchy()
test_take_snapshot_and_verify_changes()
test_verify_changes_rejects_unrelated_file_edit_in_git_repo()
test_verify_changes_accepts_target_only_edit_in_git_repo()
test_has_blocked_marker()
test_main_agy_success()                            # Agy succeeds on first try
test_main_blocked_stops_immediately()              # NEEDS_INPUT → 1 call only
test_main_audit_correlation_id_consistent()        # UUID in audit records
test_main_agy_fails_falls_back_to_haiku()          # Agy → Haiku success
test_main_haiku_retry_ladder_success()             # Agy → Haiku att1 → Haiku att2 success
test_run_tool_permission_error()
```

---

## 5. Closeout Gate Invocation Pattern

```bash
# Stage specific target files only
git -C "D:/Taadaa/tools" add dispatch_worker.py tests/test_dispatch_worker.py

# Unstage any extra files (avoid "staged files mismatch" rejection)
git -C "D:/Taadaa/tools" restore --staged ag_cli.py tests/test_ag_cli.py

# Run targeted closeout review
python D:/Taadaa/tools/closeout_gate.py \
    --repo "D:/Taadaa/tools" \
    --base HEAD \
    --files dispatch_worker.py tests/test_dispatch_worker.py \
    --json-output
```

---

## 6. Safe Push & Canary Pitfall (Developer Tooling Repos)

- `safe_push.py` checks `detect_task_type(repo)` via `done_gate.py`.
- If a repo is categorized as `'automation'`, `safe_push.py` requires a verified Android Canary Receipt (`.canary_passed`).
- **CRITICAL INVARIANT:** Developer tooling repos (như `D:/Taadaa/tools`) không chạy trên thiết bị Android thật, TUYỆT ĐỐI CẤM khai báo `"tools"` vào `AUTOMATION_REPOS` trong `done_gate.py`. Nếu bị khai báo nhầm, `canary_runner.py` sẽ báo lỗi `Chưa đăng ký cooldown state cho repo: tools` và chặn `safe_push` vĩnh viễn. Đảm bảo `detect_task_type("D:/Taadaa/tools")` luôn trả về `"general"` để bypass Canary phần cứng an toàn.

---

## 7. Architectural Roles Invariant (Reviewer vs Worker)

- **Reviewer:** BẮT BUỘC định tuyến vào **Claude Sonnet CLI** (`--model claude-sonnet` qua pipe `claude -p - --model sonnet`). Không để drift sang model khác hoặc fallback khi chưa được cấu hình.
- **Worker:** BẮT BUỘC **Agy CLI (`ag_cli.py fix`) làm Primary (Tier 1)** với **Claude Haiku CLI làm Fallback (Tier 2)**.
- **Coordinator:** Chỉ thực hiện Emergency Surgery (L2) trong phạm vi O(1) nghiêm ngặt (<= 30 dòng, 1 file, focused test < 30s) khi worker kẹt/timeout.

---

## 8. Safe Push Agent Override Prohibition (`BLOCKED_AGENT_OVERRIDE`)

- `safe_push.py` kiểm tra `AGENT_SESSION_VARS` (`HERMES_SESSION_KEY`, `HERMES_HOME`, `_HERMES_GATEWAY`).
- Nếu phát hiện bất kỳ biến môi trường nào của agent, cờ `--owner-override` sẽ kích hoạt ngoại lệ `BLOCKED_AGENT_OVERRIDE` (exit code 2) để ngăn AI agent tự tiện bypass Closeout Gate.
- Cờ `--owner-override` là cơ chế cơ học ĐỘC QUYỀN dành cho người vận hành (human operator) thực thi thủ công trên terminal sạch bên ngoài Hermes khi cần ghi đè khẩn cấp.

---

## 9. Automatic Dynamic Skill Injection (Pre-dispatch Hook)

- **Mục tiêu**: Tự động inject context kỹ năng phù hợp vào prompt trước khi gửi cho Worker (Agy / Haiku), khắc phục triệt để tình trạng Coordinator quên nạp skill hoặc Worker tự ý chế lại bánh xe.
- **Kiến trúc Adapter Layer**: Tách riêng `tools/skill_injector.py` thay vì nhồi code vào `dispatch_worker.py`:
  - Trước khi dispatch: gọi `inject_skill_context(args.prompt, max_context_chars=15000)`.
  - Luôn nạp 5 Pinned Core Invariants + top 1–2 matched skills.
  - **Clean References Guard**: Tự động gọt bỏ phần lịch sử `## References` dài hàng chục KB của các skill (như `session-close-protocol`), giữ lại phần cốt lõi và quy tắc bắt buộc $\le 3000$ ký tự/skill để không bao giờ vượt trần 15k ký tự.
  - **Graceful Fail-Closed**: Nếu index thiếu/stale hoặc gặp exception, injector trả về rỗng và dispatch worker vẫn tiếp tục chạy với prompt gốc, TUYỆT ĐỐI không để bước phụ trợ làm nghẽn luồng dispatch chính.
  - **Windows 8191-Char CLI Cap Pitfall (`The command line is too long`)**: Trên Windows, API `CreateProcessW` giới hạn toàn bộ command line ở **8.191 ký tự**. Nếu `inject_skill_context` dùng `max_context_chars=15000` nhồi vào CLI argument của `claude_worker.py` hoặc `ag_cli.py`, tiến trình sẽ văng lỗi `The command line is too long` ngay lập tức! Khắc phục:
    + Cố định trần `max_context_chars=2500` trong `dispatch_worker.py` khi truyền qua argument dòng lệnh.
    + Hỗ trợ cờ `--no-skill-injection` cho các lần gọi từ test runner hoặc pipeline nội bộ (`gate_pipeline.py`).
  - **Audit Telemetry RC Integrity (Chống Silent Success)**: Khi ghi `audit("skill_injection", ...)`, BẮT BUỘC truyền `rc=1` khi trạng thái là `FAIL_CLOSED_*`, chỉ truyền `0` khi `OK` hoặc `NO_MATCH`. Tuyệt đối cấm hardcode `rc=0` gây sai lệch bằng chứng audit.
  - **Safe Block-Boundary Clamping**: Khi cắt tỉa context để fit budget, BẮT BUỘC lùi về ranh giới `<!-- END SKILL: ... -->` của block trước đó, cấm cắt ngang xương ở giữa tag làm hỏng cấu trúc prompt.
  - **Hermetic Test Fixtures (Chống Môi Trường Ô Nhiễm)**: Unit tests cho `skill_injector` BẮT BUỘC dùng fixture `hermetic_env` tạo skills_dir và index_path trong `tmp_path`, cấm chạy trực tiếp trên `DEFAULT_INDEX` thật của farm vì chỉ cần 1 skill live bị touch là `check_index_freshness` fail-closed làm rớt test ngẫu nhiên.

---

## 10. Unified Gate Pipeline (`gate_pipeline.py`) & Kỷ Luật "Không Khóc Lóc"

- **Mục tiêu**: Gom toàn bộ chuỗi 3 cổng Gate A (chốt hiện trường) $\rightarrow$ Gate B (Claude Sonnet lập plan.json + HMAC) $\rightarrow$ Gate C (`dispatch_worker.py` thi công + nghiệm thu test) thành 1 lệnh cơ học duy nhất:
  ```bash
  python D:/Taadaa/tools/gate_pipeline.py \
    --file <target_file> \
    --goal "<goal>" \
    --evidence-source <evidence_file_or_cmd> \
    --acceptance-cmd "pytest tests/<focused_test>.py"
  ```
- **Triệt tiêu bẫy lách luật**:
  + Chặn đứng tình trạng Coordinator tự ý sửa code rồi dán nhãn `[L2-surgery]` giả tạo cho commit $> 30$ dòng (như vụ TikTok rename 395 dòng).
  + Chặn đứng việc Coordinator copy markdown plan từ Claude rồi nhồi thô vào `ag_cli.py` mà không có HMAC hash của Gate B (như vụ Warcraft).
- **Kỷ Luật "Không Khóc Lóc" (Fail-fast Zero Whining)**:
  + Khi bất kỳ Gate nào thất bại, script trả về JSON 1 dòng có cấu trúc xác định:
    `{"status": "FAIL", "failed_gate": "A"|"B"|"C", "error": "...", "next_action": "..."}`.
  + CẤM TUYỆT ĐỐI Coordinator sinh văn mẫu than phiền, xin xỏ clarify vô căn cứ hay đóng băng phiên làm việc. Next action luôn rõ ràng và xác định để khắc phục tức thì.



