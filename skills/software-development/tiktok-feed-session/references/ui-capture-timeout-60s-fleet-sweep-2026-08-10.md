# UI-capture timeout 60s — fleet sweep 9 consumer repos (2026-08-10)

## Quyết định (user, 08-10)

- Máy SM-G930F cũ splash TikTok load > 8s → capture `capture_deadline_exceeded` FAIL dù feed thực sự load xong (evidence: M60 ảnh thấy feed "hawhyu.1" chạy bình thường cùng lúc summary báo `capture_deadline_exceeded`).
- User: "8s qua ngắn... lên 60s luôn cho chắc vì timeout chờ cũng k mất gì. Nếu hợp lí thì update toàn bộ repo luôn k chỉ repo này."
- **Kết luận: nâng UI-capture deadline lên 60s cho MỌI repo automation consumer.**
- Rationale: timeout là TRẦN TRÊN — màn bình thường dump xong 1-3s trả về ngay, không chậm; chỉ máy thật chậm mới dùng tới 60s. Đổi lại máy hang thật chờ tối đa 60s trước khi vào ladder (~50s chậm hơn 8s) — chấp nhận được.

## NHẦM PHỔ BIẾN: "90s splash wait" KHÔNG TỒN TẠI

Grep "90" thấy 2 chỗ — cả 2 KHÔNG phải splash-wait:
- `python_runner/core/capture_recovery.py:3953-3954` — `boot_timeout=90` (chờ máy BOOT lại sau reboot) + `verification_timeout=90` (verify dialog).
- `python_runner/flows/feed_swipe_smoke.py:306` — `DEFAULT_VERIFY_DIALOG_MAX_SECONDS = 90.0` (verify dialog OTP/link-email).
- Capture UI XML SAU launch TikTok chỉ có `deadline_seconds` cap 8s — CHÍNH LÀ CHỖ CẦN NÂNG.

## 9 repo automation consumer (dưới D:\Taadaa, đúng 9 theo user)

1. `automation-core` — là CORE shared, default tại `src/automation_core/ui.py`
2. `gan-proxy` — không có capture UI (grep rỗng)
3. `Hotmail` — `flows/hotmail_login.py:186` → `capture_ui_xml(client, timeout=20, retries=3, recovery_package="com.android.chrome")`
4. `register gmail` — `gmail_reg_v10.py:691` → `capture_ui_xml(..., timeout=20, retries=3, recovery_package=GMAIL_PACKAGE)`
5. `Tiktok_Reg` — `calibrate.py:75` + `social_reg_v1.py:973` → `timeout=20, retries=3`
6. `tiktok-add-bao-mat-f2a` — `python_runner/core/ui_dump.py:21` → wrapper `capture_ui_xml(adb, timeout=timeout, **kwargs)`
7. `tiktok-log-in` — `login_runner/device_inspector.py:109` + `source_navigation.py:375`
8. `tiktok-luot nuoi acc` — 2 chỗ cap cứng 8s:
   - `python_runner/core/capture_recovery.py:3510` — `"deadline_seconds": min(8.0, max(2.0, self.timeout))`
   - `python_runner/core/ui_capture.py:141` — `bounded_deadline = min(8.0, max(0.1, float(timeout))) if deadline_seconds is None`
   - + các `_bounded_timeout(maximum=8.0/10.0)` (L1173, 1293, 1899, 2091, 2190, 2775) — command/rpc timeout capture
9. `Tiktok-video` — `scripts/tiktok_workflow/adapter.py:235` → `timeout=15` + `state_machine.py:103`

## Vị trí core cần biết

- `automation_core/ui.py:1353` — `def capture_ui_xml(adb, timeout: float = 15, **kwargs)` = wrapper public; consumer truyền 15-20s.
- `automation_core/ui.py:204/1068` — `capture_ui_observation(..., deadline_seconds: float = 3.0)` + `capture_ui_observation` default 3s — core shared; KHÔNG đụng core bừa (rule: không sửa automation-core source; `venv-core024` dùng chung với tiktok-video đăng video).

## Thứ tự làm (tránh conflict worker)

- Worker 1 đang giữ `tiktok-luot nuoi acc/python_runner/core/capture_recovery.py` (spec 20s) → **KHÔNG dispatch worker 2 sửa cùng file lúc worker 1 còn chạy** → chờ worker 1 xong, rồi nâng 20s→60s + patch `ui_capture.py` + các `_bounded_timeout` còn lại.
- Consumer call sites (Hotmail/register gmail/Tiktok_Reg/Tiktok-video/tiktok-add-bao-mat-f2a/tiktok-log-in) nâng timeout 15-20 → 60.
- Mỗi repo: chạy pytest liên quan + `py_compile` + `git diff --check`; commit+push riêng từng repo (convention "xong"=commit+push cmt tiếng Việt).

## Pitfall liên quan (đã dính cùng phiên)

- **8s → 20s worker 1 rồi nâng 60s**: khi đổi yêu cầu giữa chừng, đừng để 2 worker đè cùng file; đợi worker giữ file xong rồi nâng tiếp.
- `search_files` fail trên path tiếng Việt (`tiktok-luot nuoi acc`) → dùng `terminal` + `grep -rn` qua git-bash (xem SKILL.md §6b).
- `_bounded_timeout` có maximum riêng (8/10s) cho từng nhóm lệnh — nâng deadline chưa đủ nếu command timeout vẫn cap 8s ở lớp dưới.