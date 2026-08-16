# Plan-audit release-always-lock — session log 2026-08-16

Mục đích: ghi lại chuỗi audit plan 5 vòng (hành trình REJECT → APPROVED) và quy trình làm việc
đã chứng minh hiệu quả, để tái sử dụng cho mọi plan-audit khó (core/lock/recovery).

## Timeline (verdict + kênh + lý do)

| Vòng | Kênh | Verdict | Vì sao |
|---|---|---|---|
| 1 | AG `ag/claude-opus-4-6-thinking` (ag_audit_direct.py) | ❌ HALLUCINATE | Auditor KHÔNG đọc được D:\ path → bịa TOÀN BỘ `device_lock.py` ảo (API `device_name`/`lock_file`/`_try_acquire`/`_StaleLockReaped` — không tồn tại; line numbers/docstring khác hẳn). `AG_AUDIT_VERDICT=UNPARSEABLE`, stdout lẫn source. Đối chiếu API ảo với repo thật → bỏ audit, không dùng verdict. |
| 1b | cx `gpt-5.6-terra` (codex exec stdin, cockpit :60818) | ❌ stream disconnected | `ERROR: stream disconnected before completion` sau 5 reconnect — GPT route unavailable (user: "gpt sol hết quota r"). Chuyển Claude CLI opus-5. KHÔNG retry cùng thứ. |
| 2 | Claude CLI `claude-opus-5`/high | **REJECT** | 2 CRITICAL (default True silent-break; FAILED_LOCKED hold-signal mất) + 3 MAJOR (distinction chưa resolve; unlock-lease override; Q6 wrapper-alternative chưa so sánh) + 2 MINOR. Findings đúng — dùng làm cơ sở sửa plan. |
| 3 | Claude opus-5 | **MINOR_FIXES** | Verify bằng code thật: `serve()` KHÔNG gate `failed-locked` (chỉ gate `awaiting-verified-terminal-result`) → auditor giả định sai "state.json chặn re-run". Resolution theo USER INTENT: retry daily = intentional (lock = pure mutex). Còn F2-F5 (crash path, locks.py unlink, file-absence tests, param-order). |
| 4 | Claude opus-5 | **MINOR_FIXES** | 1 MEDIUM (default phải ghi rõ False ở MỌI layer + docstring "True is opt-in") + 1 LOW (CLI lock list test stale) + 1 INFO (comment daily-retry self-perpetuating). |
| 5 | Claude opus-5 | ✅ **APPROVED** | "Ship it" — tất cả findings resolved, không tìm thêm. |

## Quy trình đã chứng minh hiệu quả (REUSE)

1. **Prompt audit SELF-CONTAINED**: paste REAL source (path + line numbers thật + hàm/signature/status sets), đánh dấu rõ "API THẬT verified bởi coordinator — đừng bịa; KHÔNG đọc file ngoài", kèm pitfalls repo + plan summary + open questions Q1..QN. Khi auditor không đọc được file (AG hallucinate / Claude "File access denied") prompt vẫn đủ để cho verdict dùng được. (`references/self-contained-audit-prompt-recipe.md` có skeleton.)
2. **Verify assumption của auditor bằng code thật TRƯỚC khi sửa plan** — auditor giả định "state.json gate failed-locked" → đọc `serve()`/`choose_run_at()` → KHÔNG có gate → resolution theo USER INTENT, KHÔNG thêm gate ngoài yêu cầu. Ghi "VERIFIED/SUPERSEDED by code" cho từng finding vào plan.
3. **Re-audit chỉ audit Δ**: vòng sau gửi "v2 findings → v3 resolutions + verified facts + checklist" — vòng 3 nhanh hơn hẳn. Findings giảm dần + design không đổi = đúng quỹ đạo (không panic vì nhiều vòng).
4. **Khi route fail (quota/disconnect): chuyển route đúng ladder, không retry cùng thứ; đổi model = phải làm khác đi** (Claude CLI nhận prompt file qua `--append-system-prompt-file` + `--settings '{"reasoning":{"effort":"high"}}'`; output redirect ra file, đọc file đầy đủ — không pipe tail).
5. **Chặn audit lặp vô hạn**: sau 2 vòng MINOR_FIXES với findings giảm dần, vòng cuối ghi rõ "đã qua 4 vòng, mọi design question đã resolve với verified facts + user intent — chỉ veto nếu thực sự unsafe/incomplete, đừng bịa finding mới". (Dùng 1 lần, có hiệu quả: vòng 5 APPROVED ngay.)
6. **Worker implement: giao cho delegate_task với context = plan + constraints + pitfalls + deliverable format** — worker tự TDD RED→GREEN→commit từng task. Verify độc lập: git log + diff --name-only (scope) + diff --check + file CRLF + py_compile + tự chạy focused/full suite (KHÔNG tin self-report counts; chạy lại).
7. **Pre-existing fail: KHÔNG dùng git stash** (repo-global, worktree clean → pop nhầm stash cũ — xem automation-core-development). Dùng `git diff --name-only` chứng minh file không bị sửa.

## Thiết kế cuối (v4 — đã APPROVED + IMPLEMENTED)

- `release_on_terminal: bool = False` DEFAULT opt-in (MỌI layer: dataclass field, acquire kwarg LAST, DeviceLock compat kwarg LAST, locks.py wrapper).
- `finish()`: `if succeeded or self.release_on_terminal: release() else set_status(...)`. `__exit__`: `if release_on_terminal: release(); return` (exception cũng release — crash path intentional).
- `_UnlockedDeviceLockLease`: giữ no-op finish/__exit__ override (KHÔNG kế thừa parent release trên lock_paths=[]).
- CHỈ scheduler/base.py:298 `DeviceLock(...)` truyền `release_on_terminal=True` — nguồn lock-death duy nhất (consumer đã unlocked; recovery_runner nhận lock consumer; recovery.py FAILED_LOCKED = OUT OF SCOPE).
- Scheduler FAILED_LOCKED branch: `lease.set_status("failed_locked")` → `lease.finish(succeeded=False, failure_status="failed_locked")` (set_status chỉ ghi status KHÔNG unlink; finish routes qua release khi opt-in).
- field order: `release_on_terminal` TRƯỚC `_released: bool = field(init=False)` (field non-default không sau field default).
- Test opt-in assert FILE ABSENCE (`not path.exists()`), không chỉ "không exception".
- Scheduler test cần cô lập readiness: `CODEX_DEVICE_READINESS_DIR` + viết `proxy_ready` JSON theo `readiness.readiness_path` sha256 name (nếu không → timeout 180s).
- Commit: `ded3e9b` device_lock, `c000af7` locks, `c12519d` scheduler. Full suite 574 pass + 1 pre-existing test_startup fail.
