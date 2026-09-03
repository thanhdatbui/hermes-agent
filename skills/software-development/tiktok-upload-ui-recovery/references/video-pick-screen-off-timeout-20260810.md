# VIDEO_PICK Screen-Off/Timeout — root cause + fix (2026-08-10)

## Triệu chứng chuỗi (batch 24 máy, đêm 09→10-08)

Batch 24 máy Tik1 low-count fail đồng loạt `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`,
exit 2, dù đã fix: coordinate-fallback guard lần 2, display baseline `wm size`,
caption-composer verifier, profile-detail Back navigation (mỗi fix +test green,
batch vẫn fail 100%). Retry single máy 74 (cùng code) cũng fail 5/6 lần.

Log đặc trưng mỗi lần:
```
[VIDEO_PICK] Visual create-button gate rejected screenshot: white=0.000, dark=0.976
[VIDEO_PICK] Ladder cạn; coordinate create-entry tap 1 lần tại (540, 1857) scale=wm_size override
[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Coordinate create-entry tap did not prove composer/editor after recapture (fail-closed)
```

## Root cause thật: SCREEN OFF do timeout

- Trước VIDEO_PICK: MEDIA_PUSH + gallery cleanup xoá file cũ + push video mới
  + media scan mất ~60-90s KHÔNG tương tác với màn hình.
- Farm screen timeout tắt display → `dumpsys power` → `mWakefulness=Asleep`.
- Visual gate chụp màn đen (`dark≈0.97`); UI dump/tap đều vô nghĩa — coordinate
  tap vào màn tối không mở composer → recapture vẫn tối → fail-closed oan.
- Worker có wake ở CONNECT_DEVICE (`wake_unlock_read_state`) nhưng KHÔNG wake lại
  trước VIDEO_PICK capture.

## Phân biệt dark ratios (quan trọng — đừng nhầm root cause)

| Trạng thái | dark ratio | Đặc điểm khác |
|---|---|---|
| Screen OFF (timeout) | `dark≈0.97` (gần đen tuyệt đối) | `dumpsys power` = Asleep; screencap sau khi bật = UI bình thường |
| Profile DETAIL (xem video mình) | `dark≈0.6` | dump có back `Quay lại`, `lượt xem`/`Cài đặt quyền riêng tư`, không navbar |
| Feed tối (video đen chiếm màn) | `dark≈0.3-0.6` | dump có `Đề xuất`, bottom nav |

Cách chẩn đoán nhanh khi visual gate reject:
```bash
adb -s <serial> shell dumpsys power | grep -i wakefulness   # Asleep = screen off
adb -s <serial> exec-out screencap -p > now.png             # vision_analyze nếu cần
```

## Fix (code SỐNG)

`_ensure_screen_on(adapter)` trong state_machine.py:
1. `adb.shell(["dumpsys", "power"])` → nếu `mWakefulness=Awake`/`ON` → return True
2. else `input keyevent 224` (KEYCODE_WAKEUP — an toàn, không đụng UI control)
3. sleep 2 → verify lại dumpsys → Awake = True, còn lại False (fail-closed)

Gọi ở 2 chỗ:
- ĐẦU `_handle_video_pick` — trước dump UI đầu tiên
- Trong `_recover_video_pick_create_entry_coordinate` — trước pre-tap dump + evidence

Regression: `test_video_pick_ensure_screen_on_wakes_sleeping_display` +
`test_video_pick_ensure_screen_on_stays_when_awake` (fake Adb trả Asleep rồi Awake,
assert có input 224; awake sẵn → không input). Full suite 377 passed.

## Pitfall kèm: coordinate confirm rồi ADB rớt (đừng sửa handler)

Run 00:58 m74: `[VIDEO_PICK] Coordinate create-entry fallback confirmed
composer/picker after exact one tap` → NGAY SAU đó
`ADB_TRANSPORT_LOST_AFTER_VERIFIED_PERSISTENT_CAPTURE` → attempt 2 bị chặn
`already tapped once` → MANUAL_REVIEW. Coordinate tap ĐÃ mở composer (handler
đúng) — ADB rớt là transient (uiautomator stress farm nhiều máy song song).
Khi gặp chuỗi này: dọn lock + chạy lại run MỚI (reset `coordinate_tapped`),
máy đang ở composer → `_is_final_composer_surface` reuse → CAPTION_FILL tiếp.
KHÔNG sửa handler.

## RETRY LOOP fingerprint (cùng phiên — đã có §6, tóm tắt)

Máy fail trước POST liên tục → mỗi run re-reserve video → entry `reserved` trẻ
(< 1800s) chặn run sau → vòng lặp `MEDIA_FINGERPRINT_PENDING`. Unblock khi đã
chứng minh an toàn (mọi run `post_submission_state=None`, ledger verified chỉ
tới video N-1): backup rồi **XÓA file entry** — không đặt `status='released'`
(some builds vẫn raise `unresolved ledger status=released`). Field `machine`
là STRING — so `str(e.get('machine'))`, không int.