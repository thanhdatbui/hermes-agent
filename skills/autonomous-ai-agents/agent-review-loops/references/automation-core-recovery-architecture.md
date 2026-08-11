# automation-core recovery architecture — root cause "manual hoài" + policy mới (hit 2026-08-11)

Nguồn: đọc code thật `D:\Taadaa\automation-core` (recovery.py, recovery_runner.py, results.py, global_recovery.py). Dùng khi debug recovery consumer hoặc triển khai AI escalation / FAILED_LOCKED.

## Flow thật (recovery_runner.py `_run_one`)

```
detect() → success? → verify → VERIFIED_SUCCESS (release lock)
fail → classify() → disposition == HARD_STOP → HARD_STOP (manual, KHÔNG vào loop)
reserve() → loop:
  CLASSIFIED → reserve_handler() → spec = registry.require(failure_class)
  next_attempt > policy.max_meaningful_attempts (mặc định 8 = 1 detect + 7 live)
      → finalize_blocked(FINAL_BLOCKED) → **_release(lock)**   ← fail cuối HIỆN RELEASE LOCK
  spec.recover() → spec.recapture() (bắt buộc trả artifact sanitized=True, nếu không → RecoveryContractError)
  → verifier() → authorize_retry() → detect() lại
```

- `RecoveryHandlerRegistry.require(failure_class)` raise `NO_HANDLER_IMPLEMENTED:<class>` khi thiếu handler; handler legacy (mapping cũ chỉ có recover) bị đánh dấu incomplete và cũng fail validate.
- Handler cần ĐỦ 3 callbacks: recover / recapture (trả artifact `sanitized=True`) / verifier.

## 2 root cause "fail kiểu gì cũng MANUAL_REQUIRED" (user complaint 2026-08-11)

1. **NO_HANDLER → HARD_STOP**: `require()` raise KHÔNG được bắt trong `_run_one` → propagate lên `run_all` bắt generic Exception → `ORCHESTRATOR_ERROR` → HARD_STOP (manual). Tức là thiếu handler cho đúng failure_class, không phải "8 vòng không đủ".
2. **Classifier disposition sai**: classifier trả `NON_RETRYABLE`/`HARD_STOP` thì recovery loop không bao giờ chạy — thẳng manual.

Kết luận: muốn auto hơn phải (a) đăng ký đủ handler cho các failure_class thực tế, (b) classifier phân loại retryable đúng, (c) thêm AI escalation thay manual (dưới).

## Policy mới user chốt (triển khai 2026-08-11, plan: automation-core/.hermes/plans/2026-08-11_ai-escalation-failed-locked.md)

1. **AI escalation**: recovery hiện tại fail (NO_HANDLER / budget exhausted / HARD_STOP lỗi lạ) → KHÔNG trả manual ngay — dispatch AI fix agent QUYỀN CAO (Hermes agent: log + UI dump → ATX-kill → force-stop → soft reboot → clear cache → retry), budget riêng ~3 vòng; fix được → verifier → release lock; vẫn fail → FAILED_LOCKED.
2. **FAILED_LOCKED vĩnh viễn**: fail cuối GIỮ lock (phải đổi `_release(lock, blocked)` tại recovery_runner — hiện release), không retry tự phát, không spam; máy nằm im chờ user.
3. **Check/open lock thủ công**: lệnh Hermes/CLI liệt kê máy FAILED_LOCKED (machine, serial, failure_class, log ngắn, thời điểm) + lệnh mở lock → release + recovery.
4. **Core ≠ executor**: automation-core chỉ cung cấp hook/state/event (vd state `AI_ESCALATION_REQUIRED` + event); consumer adapter (hoặc Hermes gateway) là nơi thực thi AI fix thật — core KHÔNG spawn Hermes. Không có escalation handler → vẫn FAILED_LOCKED (fail-closed, không tự bỏ lock).

## Trạng thái liên quan (global_recovery.py)

TERMINAL / VERIFIED_SUCCESS / FINAL_BLOCKED / UNKNOWN_AFTER_CRASH / REPLACEMENT_REQUIRED — recovery runner chỉ release lock khi SUCCESS; FAILED_LOCKED là trạng thái MỚI cần thêm (hoặc tái dùng FINAL_BLOCKED + giữ lock).

## Lưu ý thiết kế

- `RecoveryPolicy.max_meaningful_attempts = 8` (results.py) — consumer có thể thắt chặt, không nới.
- Retry mặc định chỉ cho disposition RETRYABLE / BENIGN_RECOVERABLE.
- Budget AI escalation cần cap (cost) + scope quyền rõ (agent quyền cao = adb full — sandbox theo máy, không cho lệnh ra ngoài).
- Lock giữ vĩnh viễn ảnh hưởng capacity — check/open phải nhanh, list phải có log ngắn để user quyết định.

## FAILED_LOCKED + AI escalation — implementation fail-closed pitfalls (AG Opus audit rounds, Phase 1 `d302dee` + Phase 2 `9e592af`/`6d83f8c`, worktree `codex/failed-locked-phase1` 2026-08-11)

Những gì auditor (AG Opus) bắt được khi triển khai — check lại từng mục nếu làm terminal-state/recovery mới:

1. **Terminal state MỚI phải vào MỌI status-set, không sót chỗ nào**: `global_recovery.py` `RecoveryWorkerLease` có 3 nơi check terminal (`mark_terminal` whitelist, `acquire` guard, `watchdog_action` set) — sót 1 chỗ thì stale lease FAILED_LOCKED bị `REQUEST_CHECKPOINT → REPLACE_WORKER` → auto-retry. Scheduler `_device_lock_available` chỉ chặn `owner_active=True` — FAILED_LOCKED là non-active → coi lock "free" → re-fire reacquire; `_terminal_result_proven` cũng phải hiểu state mới. Grep toàn repo mọi set status trước khi tin "terminal".
2. **`finalize_blocked` có preconditions (state RETRYING + artifacts + attempts≥2) không dùng được cho fail sớm**: budget-exhausted thực tế xảy ra từ CLASSIFIED/RECOVERY_RESERVED (chưa artifact). Cần finalizer RIÊNG (`finalize_failed_locked`) chấp nhận 5 state nguồn `CLASSIFIED/RECOVERY_RESERVED/RECOVERING/RECAPTURED/GUIDED_RECOVERY_REQUIRED`, evidence tối thiểu redacted (reason/signature/attempts/artifact paths nếu có), KHÔNG giả tạo artifacts/attempts; thêm edge vào CẢ `_allowed` (recovery.py) lẫn `_TRANSITIONS` (results.py) + `TERMINAL_REQUIRES_COMPLETION_GATE`/`RecoveryCompletionGate.verify` chấp nhận state mới. Giữ nguyên contract FINAL_BLOCKED cũ.
3. **Exception pre-record → FAILED_LOCKED, KHÔNG phải HARD_STOP**: generic `except Exception` / `except RecoveryContractError` ở nhánh chưa có queue record (hoặc state ngoài source-states) nếu fall về HARD_STOP là weak fail-close — lock có thể bị release/handoff. Mọi nhánh không chắc chắn phải kết thúc FAILED_LOCKED + giữ lock; lỗi phải hiện trong reason/evidence (không nuốt).
4. **Cấm `except RecoveryContractError: pass` im lặng trong recovery path**: `mark_escalation_required`/`append` AI event fail mà pass hết → mất audit trail escalation (event ESCALATION_REQUIRED không durable). Chỉ swallow đúng trường hợp "no durable record yet" (match message/code cụ thể); lỗi khác (lease contention, corrupt store) phải propagate hoặc chuyển FAILED_LOCKED.
5. **Lock phải được giữ EXPLICIT ở MỌI terminal path**: path hook-thành-công (ESCALATION_REQUIRED pending) mà không gọi `_failed_locked_hold` → lock bị abandon theo GC/`__del__`, file-based lease hết hạn âm thầm. Guard `_release` cũng nên check `result.status == FAILED_LOCKED → return ngay` (explicit, không dựa vào việc status "không nằm trong release-set").
6. **String-match exception (`str(exc) == "MEANINGFUL_ATTEMPT_BUDGET_EXHAUSTED"`) là fragile**: dùng exception type riêng (vd `RecoveryBudgetExhaustedError` kế thừa `RecoveryContractError`) + export vào `__all__`; backward-compat giữ nguyên `str(exc)`.
7. **Test setup: cấm module-level `sys.modules["tools"] = ...`** — ảnh hưởng toàn session; dùng monkeypatch-scoped fixture. (Vụ này là fix baseline collection `tools.verify_wheel_metadata` — commit riêng `9e592af`, chỉ thêm path/import setup, không đổi logic tool.)
8. **Dead code sau "first hook authoritative"**: `EscalationRegistry.call` loop mà mọi vòng đều return → trailing `return None` unreachable + loop gây hiểu lầm; chỉ gọi `_hooks[0]` + comment contract.

Kết quả verify thật (chuỗi audit): Phase 1 r1 MINOR_FIXES (5 finding) → fix → r2 APPROVED → commit `d302dee`; Phase 2 r1 MINOR_FIXES (7 finding F1–F7) → fix → r2 MINOR_FIXES (còn NF1 newline EOF + NF2/NF3 informational) → fix newline → r3 APPROVED. Pattern: mỗi vòng chỉ fix finding có locator đối chiếu được; finding informational/NIT không đáng vòng audit riêng nhưng material change (kể cả 1 newline) mở slot mới — fix gộp rồi re-audit 1 lần.
