# Lease-Release Review Pattern (Case 162 + 163, 13/09/2026)

Vòng review OmniRoute (`review` combo, closeout_gate.py `--input <diff>`) REJECT 4 lần
liên tiếp trước khi APPROVED cho cùng một candidate thay lock `blocked` bằng
`lease.release()`. Mỗi lần REJECT chỉ ra đúng một lỗi thiết kế — pattern chuẩn
dưới đây là tổng hợp để lần sau viết đúng ngay từ đầu.

## Pattern chuẩn: failed-session lease release

```python
released_ok = False
try:
    if can_publish:  # timing is None or _worker_publication_allowed(timing)
        try:
            _write_recovery_handoff_evidence(..., succeeded=False,
                final_status="retained", lock_status="retained")
        except Exception:
            pass
finally:
    try:
        lease.release()
        released_ok = True
    except Exception as rel_exc:
        print(f"[WARN] lease.release() failed: {rel_exc}", flush=True)
    if released_ok and can_publish:
        try:
            _write_recovery_handoff_evidence(..., succeeded=False,
                final_status="released", lock_status="released")
        except Exception:
            pass
```

## 5 invariant reviewer enforce (theo thứ tự REJECT)

1. **Giữ `succeeded=False` trong audit evidence.** Phiên fail/manual-needed mà
   ghi `succeeded=True` + `lease.finish(succeeded=True)` là làm sai lệch metric
   kết quả session. Dùng `lease.release()` trực tiếp, tách bạch `succeeded`
   (kết quả phiên) khỏi `lock_status` (trạng thái khóa).
2. **Release không được đứng sau publication gate.** `if not
   _worker_publication_allowed(timing): return` đặt trước `lease.release()`
   khiến lease kẹt đến khi external reaper dọn — đúng deadlock cần xóa.
   Tính `can_publish` nhưng LUÔN gọi `lease.release()`.
3. **`lease.release()` nằm trong `finally`.** Evidence-write trước release mà
   raise thì control nhảy ra outer `except`, lease không bao giờ release.
   Evidence lần 1 bọc try/except riêng, release đặt trong `finally`, log rõ
   exception thay vì `pass` câm.
4. **Fenced log + finalize chạy TRƯỚC release, nhưng toàn bộ phải nằm trong
   outer `try/finally` chứa release.** Release trước `_safe_fenced_log` gây
   lease-handoff race (worker khác acquire máy trong khi worker cũ vẫn log
   bằng fence đã nhả). Thứ tự đúng: fenced log → finalize → evidence(retained)
   → release → evidence(released), với release trong `finally` bao trọn để
   `_finalize_child` raise cũng không leak lock.
5. **Quét hết mọi `set_status("blocked")` trong file, không chỉ 2 anchor Gate 2.**
   Trong phiên này còn 3 callsite `lock_holder["lease"].set_status("blocked")`
   ở preflight abort (cohort-mismatch / proxy-VPN) — reviewer không chỉ ra
   nhưng candidate thiếu chúng là thiếu scope. Grep toàn file trước khi freeze.

## Pitfall: đừng để reviewer chấm file ngoài scope

`closeout_gate.py --repo` extract toàn bộ worktree diff, gồm cả dirty files
ngoài scope (`device_prepare.py`, `sync-safe-workbook.py`) → reviewer REJECT
vì nhận xét cả code không thuộc candidate (stay-awake, serial recovery).
Khi worktree bẩn ngoài scope: tự build diff file scoped
(`git diff origin/master -- <allowlist> > D:/Taadaa/tmp_review_candidate.diff`,
path dạng Windows) rồi gọi `closeout_gate.py --input <file>`.
