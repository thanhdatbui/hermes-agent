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
