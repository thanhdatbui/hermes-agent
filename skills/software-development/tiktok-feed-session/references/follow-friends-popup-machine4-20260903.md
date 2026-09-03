# Follow-Friends Popup M4 2026-09-03 — DeviceContext unwrap + shell list + :id/e8c + preflight pre-dismiss

Live XML máy 4 (9885e6484432423046, @projaompqxj): tiêu đề `Follow bạn bè của bạn` + 2 nút `Follow lại` + nút X `resource-id :id/e8c / content-desc Đóng` tại [916,606][1036,726]. Popup che header profile → false-positive `profile account mismatch`.

## 1. Bug A — `capture_required_ui(ctx)` nhận DeviceContext thay vì AdbClient
- `dismiss_follow_friends_suggestion_popup(ctx)` gọi `capture_required_ui(ctx, ...)` → luôn throw `ATX_SESSION_UNAVAILABLE` → reason `follow_friends_popup_initial_capture_failed`, popup không bao giờ được xử lý.
- Fix: unwrap ở mọi callsite trong dismisser: `capture_required_ui(getattr(ctx, "adb", ctx), ...)` + safety-net trong `core/ui_capture.py` (`adb = getattr(adb, "adb", adb)` ở cả `capture_required_ui` và `capture_required_ui_result`, metadata ghi lên `real_adb`).
- Rule: mọi helper nhận `DeviceContext` nhưng gọi capture/tap đều phải unwrap `ctx.adb` trước. Test bằng Mock sẽ che bug này vì Mock chấp nhận mọi kiểu arg.

## 2. Bug B — `AdbClient.shell(str)` tách từng ký tự
- `ctx.shell(f"input tap {x} {y}")` với signature `shell(args: Sequence[str])` → `["shell", "i","n","p",...]` → exit 127 `/system/bin/sh: i: not found`.
- Fix 2 lớp: (a) mọi tap trong `flows/benign_popup.py` dùng list `["input","tap",str(x),str(y)]`; (b) safety-net trong `automation-core/src/automation_core/adb.py`: `shell/exec_out` chấp nhận `str | Sequence[str]`, dùng `shlex.split` nếu là str.
- Rule: KHÔNG bao giờ truyền f-string vào `adb.shell`. Contract kiểm tra: `tap_action` phải gọi `shell` với list.

## 3. Nút X `:id/e8c` (máy 4) thiếu trong allowlist
- Trước đây chỉ có `:id/c3t`, `:id/e63`. Máy 4 dùng `:id/e8c`.
- Fix tại 3 nơi: `_find_follow_friends_semantic_close_control` (flows/benign_popup.py), `_find_follow_friends_close_button` (automation-core tiktok_popup.py), dismiss-target loop (automation-core tiktok/benign_popup.py) → chấp nhận `(c3t, e63, e8c)`.
- Rule: khi gặp resource-id đóng mới, grep cả 3 file trên, không sửa 1 nơi.

## 4. Preflight `read_profile_identity()` chưa pre-dismiss popup
- Chỉ `_verify_profile_after_session` có đặc trị popup; preflight đọc identity trực tiếp → username rỗng → mismatch.
- Fix: thêm block pre-dismiss trong `read_profile_identity()` (detect → dismiss → recapture `profile_identity_post_popup`) + sau dismiss ở verify_profile, nếu `_profile_screen_confirmed_from_xml == False` thì re-tap tab Hồ sơ và recapture (`verify_profile_post_popup_nav`).

## 5. Canary máy lẻ bị chặn hạ tầng (không phải lỗi popup)
- `run-feed-session.ps1 -Machines 4 ... -Run` → `cohort artifact and assignment manifest are both required for a live cohort child`; `-Preset full` kéo cả 74 máy vẫn cùng lỗi; direct `run_tiktok.py --mode feed-session-smoke --device ... --prepare-tiktok` → CONFIG_ERROR (prepare-tiktok chỉ cho run-plan/multi-machine).
- Canary máy lẻ cần parent cấp CohortArtifact/manifest hợp lệ hoặc chạy qua cohort pipeline. Khi báo cáo: tách rõ "code fix + unit test pass" khỏi "canary blocked by infra".
