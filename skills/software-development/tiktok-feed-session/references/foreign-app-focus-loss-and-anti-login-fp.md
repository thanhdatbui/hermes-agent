# Foreign App Focus Loss & Anti-False-Positive Login Screen

## Overview
When non-TikTok foreign applications (e.g., Samsung Pay `com.samsung.android.spay`, Samsung/OEM launchers `com.sec.android.app.launcher`, SystemUI overlays, or other background-popped apps) take the foreground:
1. They must be recognized as focus loss and recovered via TikTok relaunch.
2. They must NOT be falsely classified as in-app TikTok `manual-needed:login` screens despite matching action/credential text terms (e.g. "Đăng nhập", "Tiếp tục", "Thanh toán").

## 1. Generalized Focus Loss Recognition (`_is_launcher_focus_loss`)
In `python_runner/flows/feed_swipe_smoke.py`:
- Treat any foreground package outside `tiktok_pkgs` as focus loss, UNLESS it is a recognized Android PackageInstaller dialog (`is_packageinstaller_dialog(row)`, `PACKAGEINSTALLER_DIALOG_SCREEN`, `popup_type="packageinstaller_permission"`).
- Covers `com.samsung.android.spay`, `com.sec.android.app.launcher`, `com.android.systemui`, and arbitrary foreign apps.

```python
def _is_launcher_focus_loss(ctx: DeviceContext, row: dict[str, Any]) -> bool:
    expected_package = str(ctx.config.get("tiktok_package", "com.ss.android.ugc.trill"))
    tiktok_pkgs = {expected_package, "com.ss.android.ugc.trill", "com.zhiliaoapp.musically", "com.ss.android.ugc.aweme"}

    extra = row.get("extra") if isinstance(row.get("extra"), dict) else {}
    focus_package = str(
        extra.get("focused_package")
        or extra.get("focus_package")
        or row.get("focused_package")
        or row.get("focus_package")
        or ""
    )
    reason_lower = (str(row.get("reason") or extra.get("reason") or "") + " " + str(row.get("safety_reason") or extra.get("safety_reason") or "")).lower()

    if focus_package in tiktok_pkgs:
        return False

    if (
        is_packageinstaller_dialog(row)
        or (isinstance(extra, dict) and is_packageinstaller_dialog(extra))
        or row.get("detected") == PACKAGEINSTALLER_DIALOG_SCREEN
        or row.get("popup_type") == "packageinstaller_permission"
        or focus_package in {
            "com.android.packageinstaller",
            "com.google.android.packageinstaller",
            "com.android.permissioncontroller",
        }
    ):
        return False

    if focus_package:
        return True

    return "tiktok focus lost" in reason_lower or "focus lost" in reason_lower
```

## 2. Baseline Startup Recovery (`_capture_baseline_with_startup_retry`)
In `python_runner/flows/feed_swipe_smoke.py`:
- In `_capture_baseline_with_startup_retry`: If `_is_launcher_focus_loss(ctx, row)` triggers, invoke `_relaunch_and_poll_tiktok_focus` with `POST_SWIPE_LAUNCHER_RECOVERY_WAIT_SECONDS` and recapture under `step="baseline_launcher_recovery_recapture"`.

## 3. Anti-False-Positive Login Screen (`core/classifier.py` & `core/benign_popup.py`)
In `python_runner/core/classifier.py` and `python_runner/core/benign_popup.py`:
- If all non-system UI packages in the XML hierarchy belong to foreign applications (no TikTok package and no PackageInstaller package), classify the screen as `unknown` with `manual_needed=False`.
- Prevents `has_sensitive_marker` or `login_terms` from misclassifying Samsung Pay / launcher screens as `manual-needed:login`.
- Priority ordering: `_is_public_profile_screen` must be checked before `detect_allowed_generic_popup` so public profile pages with recommendation lists ("Tài khoản được đề xuất") are correctly recognized as `profile`, not generic popups.
