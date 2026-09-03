# Popup account-update + ATX restart + workbook truth (2026-08-15)

Session: avatar farm Tik2 68/68 máy (né 1, 2, 38). Bài học 3 nhóm.

## 1. Popup "Tài khoản của bạn cần được cập nhật" — account switcher blocker

**Triệu chứng (máy 23, kéo dài nhiều vòng retry):**
- ACCOUNT_SWITCHER log: chọn account OK (`Target account selected via core ✓`) rồi ngay sau đó
  `Restored TikTok subpage detected; Back recovery 1/12 ... 12/12` → `PROFILE_ROOT_NOT_CONFIRMED` → MANUAL_REVIEW.
- ATX restart + persistent dump KHÔNG cứu được (vì không phải lỗi dump — XML vẫn đọc được).
- `dumpsys activity` cho thấy `SplashActivity` persist sau khi tap nick trong switcher = app đang reload, không vào feed.

**Cách tìm root cause (manual probe):**
1. Mở app → feed → tab Hồ sơ (tap 960,1830).
2. Tap mũi tên xuống cạnh tên hiển thị (máy 23: x=672, y=547; tên hiển thị ~540,547) → bottom sheet "Chuyển đổi tài khoản" liệt kê nick đã lưu (có cả nick Tik2 cần).
3. Tap nick Tik2 → popup bảo mật: *"Tài khoản của bạn cần được cập nhật — Để tăng cường tính bảo mật, hãy liên kết số điện thoại hoặc địa chỉ email của bạn trước khi chuyển đổi tài khoản"* với 2 nút: "Liên kết số điện thoại hoặc e..." + "Để sau" (`com.ss.android.ugc.trill:id/btn_later`).

**Fix (2 commit):**
- automation-core `6c6b6e8`: `PopupRule("account_update_required_vi", ("tài khoản của bạn cần được cập nhật", "liên kết số điện thoại hoặc"), TAP, _text("Để sau"))` trong `TIKTOK_POPUP_RULES`.
- tiktok-video `06aad66`: sau `select_exact_account` gọi `dismiss_shared_tiktok_popup(adb, package="com.ss.android.ugc.trill", artifact_dir=run_dir)`.
- Kết quả: máy 23 → `AVATAR_SMOKE_SUCCESS` (exit=0, verified=True).

**Pitfall version gate:** cài editable core (0.4.40→0.4.44) làm launcher fail `automation-core version mismatch: expected=0.4.40; actual=0.4.44`. Phải bump `$defaultAutomationCoreVersion` trong `run_tiktok_upload_batch.ps1` (dòng ~86) + test assert hardcode cùng lúc. Commit `5fc4313`.

**Pitfall test popup:** node dismiss trong XML test PHẢI có `bounds` (`[360,1060][720,1180]`) — thiếu bounds → `detected=True` nhưng `action_taken=None`. Assert tap = `any(call[:2] == ["input","tap"] for call in adb.calls)` (tap theo tọa độ, không chứa text).

## 2. B1 ATX-kill → restart atx-agent

- `_recover_uiautomator` (core) kill atx-agent nhưng không restart → persistent UI chết sau B1.
- `capture_persistent_ui` trả `UNHEALTHY/HTTPERROR` khi atx-agent wedged (process ở `futex_wait_queue_me`/`do_wait` S-state).
- Fix: `_restart_atx_agent` = `["/data/local/tmp/atx-agent","server","-d"]` + verify `capture_persistent_ui` XML + log `[ATX_RESTART]`. Chèn sau cả 4 call site B1. Commit `b9351b7`.
- Dump UI ưu tiên persistent: `adapter._dump_ui_real` thử `capture_persistent_ui` trước, fallback `capture_ui_xml`. Commit `850e883`.
- Máy 26, 29 pass nhờ ATX restart; máy 29 cần thêm reboot VPN (VPN_REQUIRED_NOT_CONNECTED).
- Restart tay: `adb shell '/data/local/tmp/atx-agent server -d'` riêng 1 lệnh (kill+start cùng lệnh → race, process không sống).

## 3. Workbook là nguồn sự thật (user: "đừng tự chế")

- 55-máy batch avatar ban đầu dùng config default (Tik1 cho 1-37, Tik2 cho 40-74) → **nick Tik2 của máy 1-37 chưa bao giờ được xử lý** (mỗi máy 2 nick Tik1+Tik2 cùng device). Máy 39: nick Tik1 có avatar cũ, nick Tik2 chưa — phải chạy `-Tik 2` riêng.
- Chạy `-Tik 2` cho cả nhóm thiếu (3,5,6,9,10,11,12,13,23,26,29,31,35,73,75-80) → 7 máy (31,73,75,77,78,79,80) fail `Missing required fields: ID TikTok` = workbook thiếu ID → cần user điền.
- Manifest worker-id phải = owner_id: `-WorkerId hermes-kibe-avatar-m23-atx-dump` vs manifest owner `hermes-kibe-avatar-m23-reboot` → `AssignmentError` preflight. Chạy `machine_inventory` trực tiếp với đúng worker-id để verify eligible.

## Commits session
- automation-core: `6c6b6e8` feat(popup): rule account_update_required_vi
- tiktok-video: `b9351b7` fix(atx) restart atx-agent sau B1 · `850e883` fix(adapter) dump persistent-first · `06aad66` fix(account-switcher) dismiss popup · `5fc4313` chore(runner) bump core 0.4.44 · + PROJECT_RULES.md rule workbook (3db4d36)
