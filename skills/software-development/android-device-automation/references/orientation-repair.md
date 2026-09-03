# Orientation repair reference

## Verified narrow-scope recipe

For an explicitly named set of Android serials, first prove no registration
worker is active, then use the approved ADB executable with `-s` on every device.
Keep the operation settings-only.

```sh
ADB='C:/Program Files (x86)/xiaowei/tools/adb.exe'
for s in SERIAL_A SERIAL_B SERIAL_C; do
  "$ADB" -s "$s" shell settings get system accelerometer_rotation
  "$ADB" -s "$s" shell settings get system user_rotation
  "$ADB" -s "$s" shell wm size
  "$ADB" -s "$s" shell dumpsys input | grep -E 'DisplayViewport|SurfaceOrientation|orientation=' | head -20
done

for s in SERIAL_A SERIAL_B SERIAL_C; do
  "$ADB" -s "$s" shell settings put system accelerometer_rotation 0
  "$ADB" -s "$s" shell settings put system user_rotation 0
done
```

Verify using the same settings plus `wm size` and `dumpsys input`. A successful
command return is insufficient: portrait is evidenced by settings values `0/0`,
`DisplayViewport orientation=0`, and a logical frame whose height exceeds width
(for example `[0, 0, 1080, 1920]`). Only if that verification fails may the
operator consider the explicitly authorized fallback `wm set-user-rotation lock 0`;
never reboot automatically.

## ⚠️ Do NOT use `content insert` for rotation

```text
adb shell content insert --uri content://settings/system
  --bind name:s:accelerometer_rotation --bind value:i:0
```

**Hangs on Samsung Galaxy S7 / OneUI (ADB timeout ≥15 s) and kills the session.**

Added as a Samsung TouchWiz workaround in commit `594ba5a` (2026-08-19), then
confirmed removed from both files on 2026-08-23:

- `python_runner/flows/device_prepare.py::ensure_portrait_rotation` → commit `6bf8f52`
- `automation-core/src/automation_core/startup.py::lock_portrait_rotation` → commit `48ed1ee`

`settings put` alone is sufficient and never hangs.

**Alert signature to recognise**: `adb command timed out: ... shell content insert ... accelerometer_rotation` while the machine screenshot shows TikTok on the Đề xuất feed — healthy. This is a rotation-prep failure, NOT a TikTok/feed/account/CAPTCHA failure.

Full diagnosis, confirmed fix, and regression tests: `tiktok-feed-session/references/rotation-preparation-timeout.md`.

## Session evidence

In the tested farm, all three targets initially reported
`accelerometer_rotation=1`, `user_rotation=0`, logical viewport `1920x1080`, and
`orientation=1`. After the two `settings put` writes, each reported `0/0`, logical
viewport `1080x1920`, and `orientation=0`. No app was launched and no reboot was
performed.
