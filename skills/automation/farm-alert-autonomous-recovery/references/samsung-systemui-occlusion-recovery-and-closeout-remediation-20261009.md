# Samsung SystemUI Occlusion Recovery & Closeout Gate Remediation

**Date:** 2026-10-09  
**Scope:** Taadaa Farm (Cụm Samsung S7 M201-280 / M1-80), `tiktok-luot nuoi acc` / `automation-core`  
**Tags:** `samsung-systemui`, `global-actions`, `occlusion-recovery`, `closeout-gate`, `sol-auditor`

---

## 1. Bản chất sự cố Samsung SystemUI Occlusion
- **Hiện tượng:** Máy báo lỗi `login/account screen detected` hoặc `prepare-tiktok failed to focus TikTok after launch`.
- **Căn nguyên thực tế:**
  - Thiết bị Samsung Galaxy S7 bị cấn phím nguồn hoặc event hệ thống kích hoạt menu **"Tùy chọn thiết bị"** (`com.android.systemui:id/global_actions_bg`) hoặc prompt **"Chế độ khẩn cấp"** (`com.sec.android.emergencymode.service`).
  - Giao diện này thuộc package `com.android.systemui`, khiến SurfaceFlinger bật DimLayer đen/tối màn hình và đẩy ứng dụng mục tiêu (TikTok) xuống background.
  - Các hàm kiểm tra focus thông thường chỉ retry mở app lại mà không thể dẹp được system dialog đang ghim trên foreground.

---

## 2. Chuẩn xử lý kỹ thuật (Recovery Pattern)

### A. Cơ chế giải phóng 2 tầng (Broadcast + Keyevent Fallback)
```python
def recover_systemui_occlusion(
    ctx: DeviceContext,
    package_name: str,
    *,
    artifact_prefix: str = "device_prepare",
) -> dict[str, str | None]:
    """Dismiss system dialogs/overlays occluding the target package, with keyevent fallback."""
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

---

## 3. Tiêu chí vượt Closeout Gate (Sol Auditor >= 85/100)

Khi sửa đổi các nhánh recovery hoặc startup hooks, Reviewer (Sol Auditor :20129) kiểm tra rất khắt khe các tiêu chí sau:
1. **Tránh nuốt lỗi (No broad exception swallowing):** Không dùng `except: pass` im lặng; bắt buộc log warning với `exc` cụ thể.
2. **Telemetry & Observability định lượng:**
   - Bắt buộc ghi nhận `elapsed_ms` (thời gian xử lý).
   - Ghi nhận cờ trạng thái: `broadcast_ok`, `fallback_used`, `result` (`recovered` / `persisted`).
3. **Bao phủ kiểm thử (Test Coverage):**
   - Không chỉ test đường đi thành công (`happy path`).
   - BẮT BUỘC có test case cho trường hợp fallback keyevent được kích hoạt.
   - BẮT BUỘC có test case cho failure persistence (khi popup vẫn không tắt -> trả về trạng thái FAIL rõ ràng, fail-closed an toàn).
