# Breaking the 82–84/100 Plateau: SystemUI Recovery & Pre-Push Commit Rebinding

**Date:** 2026-10-09  
**Repository:** `tiktok-luot nuoi acc` / `automation-core`  
**Tags:** `closeout-gate`, `sol-auditor`, `plateau-break`, `systemui-occlusion`, `pre-push-rebinding`

---

## 1. Bối cảnh & Hiện tượng (82 -> 84 -> 88 APPROVED)
Khi vá tính năng khôi phục hệ thống (SystemUI popup/dialog occlusion) trong flow startup thiết bị, Closeout Gate (Sol Auditor :20129) trải qua 3 vòng chấm điểm:
- **Vòng 1 (82/100 - REJECTED):** Code chỉ có `try/except: pass` nuốt lỗi, chưa có test case phủ nhánh SystemUI, thiếu telemetry.
- **Vòng 2 (84/100 - REJECTED):** Đã thêm test và log, nhưng bị trừ điểm vì:
  1. Chỉ dựa vào broadcast `CLOSE_SYSTEM_DIALOGS` mà không có fallback nếu broadcast bị chặn hoặc không hiệu lực.
  2. Chưa có telemetry định lượng (`elapsed_ms`, `fallback_used`).
  3. Test chỉ bao phủ luồng phục hồi thành công và failure, chưa kiểm tra nhánh fallback.
- **Vòng 3 (88/100 - APPROVED):** Bổ sung hàm phục hồi có fallback 2 tầng (`CLOSE_SYSTEM_DIALOGS` -> `input keyevent 4`), telemetry có cấu trúc đầy đủ, và 3 test cases riêng biệt (success, persistent failure, fallback keyevent).

---

## 2. Checklist phá vỡ điểm nghẽn 82–84/100 trên System/Device Recovery Hooks

### A. Kiến trúc Recovery 2 tầng (Primary Broadcast + Fallback Escape)
Reviewer luôn trừ điểm `Code Architecture` và `Logic Correctness` nếu recovery hook chỉ gửi 1 lệnh đơn lẻ mà không có fallback khi lệnh đó không tác dụng trên các biến thể ROM/Android:
```python
def recover_systemui_occlusion(
    ctx: DeviceContext,
    package_name: str,
    *,
    artifact_prefix: str = "device_prepare",
) -> dict[str, str | None]:
    timeout = ctx.timeout("adb_seconds", 5) if hasattr(ctx, "timeout") else 5.0
    start_t = time.monotonic()
    logger.info("SystemUI dialog occluding %s on %s; broadcasting CLOSE_SYSTEM_DIALOGS", package_name, getattr(ctx, "device_id", "unknown"))
    broadcast_ok = False
    try:
        res = ctx.adb.shell(["am", "broadcast", "-a", "android.intent.action.CLOSE_SYSTEM_DIALOGS"], timeout=timeout)
        broadcast_ok = getattr(res, "ok", True)
    except Exception as exc:
        logger.warning("Failed to broadcast CLOSE_SYSTEM_DIALOGS: %s", exc)

    time.sleep(0.3)
    focus = get_focused_activity(ctx)
    fallback_used = False
    if focus.get("package") == "com.android.systemui":
        try:
            ctx.adb.shell(["input", "keyevent", "4"], timeout=timeout)
            fallback_used = True
            time.sleep(0.3)
            focus = get_focused_activity(ctx)
        except Exception as exc:
            logger.warning("Failed BACK keyevent fallback for SystemUI occlusion: %s", exc)

    elapsed_ms = int((time.monotonic() - start_t) * 1000)
    recovered = focus.get("package") == package_name
    if hasattr(ctx, "logger") and ctx.logger is not None:
        ctx.logger.log(
            device_id=getattr(ctx, "device_id", "unknown"),
            account=getattr(ctx, "account", None),
            step=f"{artifact_prefix}/systemui_occlusion_recovery",
            action="close_system_dialogs",
            result="recovered" if recovered else "persisted",
            extra={
                "package": package_name,
                "focused_package": focus.get("package"),
                "broadcast_ok": broadcast_ok,
                "fallback_used": fallback_used,
                "elapsed_ms": elapsed_ms,
            },
        )
    return focus
```

### B. Bộ 3 Test Cases bắt buộc cho nhánh Recovery
Để đạt >= 23/25 điểm `Test Evidence`:
1. `test_..._recovery_success`: Giả lập focus SystemUI -> gửi broadcast -> focus trở lại TikTok -> assert SUCCESS và broadcast gọi.
2. `test_..._recovery_fallback_keyevent`: Giả lập focus SystemUI -> broadcast xong vẫn SystemUI -> gửi `keyevent 4` -> focus trở lại TikTok -> assert cả broadcast và keyevent 4 đều được gọi.
3. `test_..._recovery_persists_failure`: Giả lập focus SystemUI liên tục không nhả -> assert flow trả về ExitStatus.FAIL và ghi stop_reason fail-closed rõ ràng.

---

## 3. Pre-Push Commit Mismatch Trap & Khắc phục
- **Vấn đề:** Khi Closeout Gate chạy trên staged candidate (`staged`), file audit `gate_audit.jsonl` ghi nhận `commit=HEAD` (SHA trước khi commit). Sau khi commit, commit mới có SHA khác, khiến pre-push hook từ chối lệnh `git push` (`[BLOCKED - PRE-PUSH HOOK]: Gate check FAILED — commit mismatch`).
- **Khắc phục chuẩn O(1):**
  Ngay sau khi git commit, chạy lại lệnh Closeout Gate với `--base HEAD~1`:
  ```bash
  python D:/Taadaa/tools/closeout_gate.py --repo "<repo_path>" --base HEAD~1 --files <files...> --json-output
  ```
  Lệnh này thẩm định commit vừa tạo, ghi audit record mới nhất khớp 100% với commit SHA hiện tại, và cho phép pre-push hook pass mượt mà.
