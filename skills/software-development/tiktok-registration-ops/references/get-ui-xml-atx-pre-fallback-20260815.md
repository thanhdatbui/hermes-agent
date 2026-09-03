# get_ui_xml atx-pre fallback + full reg-success chain (máy 38, 2026-08-15)

Session: hoàn tất đăng ký `florencenaomierayven6@hotmail.com` → `florencen2026` (@florencen2026) trên máy 38 (SM-G930F, S7, Android 7, RAM 3.6GB). Run cuối `✅ SUCCESS` exit 0, tracking row 300.

## Root cause chính: get_ui_xml trả XML STALE

- `get_ui_xml` (consumer/flow, `social_reg_v1.py` L752) dùng shell `uiautomator dump` — trên S7 bị `Killed`/EXIT=137 (uiautomator service chết vĩnh viễn khi mở app nặng như Outlook).
- Sau exec-out fail → **file fallback `/sdcard/window_dump.xml` trả XML CŨ** (dump từ màn TRƯỚC) — vd trả 12244 B text "Nhập địa chỉ email" trong khi màn thật là password/DOB/feed.
- Hệ quả: `[8b]`/resume thấy "Nhập địa chỉ email" (stale) → `type_into_node` type email vào field THẬT của màn password/DOB → hỏng màn → loop 6 vòng → PENDING. Lặp lại 5+ lần (resume14→19) vì màn mỗi lần bị [8b] phá lại.
- Trong khi `capture_ui_xml` (automation_core.ui, atx-agent service port 7912) SỐNG — đọc màn thật 33-43KB. User hỏi: "cùng UI mà 1 cái sống 1 cái chết?" → 2 cơ chế đọc khác nhau.

## Fix đã merge (social_reg_v1.py get_ui_xml)

Trong vòng `for dump_path in [...]` (file fallback), TRƯỚC khi dump file:

```python
# Trên máy yếu (S7/Android 7), file dump thường là XML CŨ (stale) từ lần dump
# trước — ưu tiên atx-fallback (tươi) TRƯỚC file fallback.
try:
    from automation_core.adb import AdbClient
    from automation_core.ui_capture import ProvisioningPolicy
    from automation_core.ui import capture_ui_xml as _cap
    _client = AdbClient(adb_path=ADB_PATH, serial=device_id,
                        default_timeout=max(10, int(_remaining_timeout("atx-pre", cap=45))))
    _cap_res = _cap(_client, timeout=max(10, int(_remaining_timeout("atx-pre", cap=40))),
                    retries=1, retry_delay_seconds=0.8,
                    provisioning_policy=ProvisioningPolicy.REQUIRE_PROVISIONED)
    if _cap_res is not None and _cap_res.xml and "<hierarchy" in _cap_res.xml:
        log(f"   [ui-xml] attempt {attempt} atx-pre OK len={len(_cap_res.xml)}")
        return _cap_res.xml
except Exception as e:
    ...
```

- `ADB_PATH` module-level = `C:\Program Files (x86)\xiaowei\tools\adb.exe`.
- File fallback giữ nguyên như tier cuối (chỉ dùng khi atx cũng fail).
- Evidence fix hoạt động: log `[ui-xml] attempt 1 atx-pre OK len=43788` → texts màn thật "Sửa hồ sơ" / florencen2026 → resume đi đúng → SUCCESS.

## Chain reg thành công (các bước tay + canonical)

1. Màn magic-link "Kiểm tra hộp thư của bạn" + "Gửi lại email" (florencen).
2. **Mở mail mới nhất trong Outlook**: verify mail mới VỀ trước (resend bị throttle — user tự bấm Đăng ký mới có mail 16:45; inbox TIMES thấy `16:45`).
3. **Mail detail: button "Xác minh email" dưới fold** — mail mở chỉ header + "Trả lời". Scroll `input swipe 540 1500 540 600 600` → button bounds mới center (539,1043) → tap.
4. TikTok verify → màn "Ngày sinh của bạn là ngày nào?" (DOB) + field.
5. `fill_birthday(device, "", stt=38)` trực tiếp: DOB fallback 01/01/1999; seekbar swipe làm UI đọc fail (`[7d] DOB mismatch`) NHƯNG màn chuyển sang "Nhập địa chỉ email" + florencen → tap "Tiếp tục" (540,1663) → **"Tạo mật khẩu"**.
6. "Tạo mật khẩu": field bị email type nhầm (35 dots) → xóa (tap field → MOVE_END → 45× keyevent 67) → type `Fl0renc3n!@2026` → tap "Tiếp tục" (540,1681).
7. "Tạo biệt danh": nút disabled khi trống → type `florencen2026` (13/30) → đóng keyboard → nút enabled → tap (540,1806) → **home feed**.
8. `--resume` (với fix atx-pre) → `[login-success]` + profile `@florencen2026` + `[tracking] deferred result saved` → `✅ SUCCESS` exit 0.

## Pitfalls kèm

- Rotation lock: `settings put system accelerometer_rotation 0` + `user_rotation 0` — check/set lại trước resume (user bực khi màn xoay ngang).
- Nút "Tiếp tục" bounds dịch theo keyboard: mở (540,1806), đóng (540,1681/1663) — luôn dump lại.
- Bounds tap link trong mail: (539,1631) khi button hiện sẵn; (539,1043) sau scroll.
- BACK từ email-detail thoát Outlook (đã có rule) — dùng in-app back arrow.
- "Tài khoản không tồn tại" + "Tạo tài khoản mới" = REG mới (tracking cũ stale) — proof email chưa reg.
- User chỉ thị: tới DOB rồi thì "bê nhánh cũ đã thành công chạy tiếp, đừng loằng ngoằng" — ưu tiên canonical handler đã có, không thêm branch mới giữa reg.
