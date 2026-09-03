# ADB load tuning & UI-capture timeout inventory — 2026-08-13

Session: user hỏi "còn cách nào giảm tải adb lag dẫn tới lỗi UI capture k, hay lỗi này klq ADB".
Kết luận: **có liên quan ADB một phần, nhưng không phải toàn bộ** — phải phân loại signature trước khi tuning.

## Timeout inventory thực tế (grep scripts/tiktok_workflow)

| Chỗ | Timeout | Loại |
|---|---|---|
| `adapter.py:51` `DEFAULT_UI_WAIT_TIMEOUT` | 60s | UI wait |
| `adapter.py:241` `capture_ui_xml(timeout=60)` | 60s | UI capture |
| `state_machine.py:274` `dump_current_ui(timeout=60)` | 60s | UI capture |
| `state_machine.py:4134/4148/6093` | 60s | wait feed/profile |
| `state_machine.py:6567/6690-6698` `_wait_for_element` | 60s | wait picker |
| `media_manager.py:116` `adb push` | 120s | push video (KHÔNG phải UI) |
| `state_machine.py:4263-4264` reboot | 120s boot + 180s verify | reboot recovery (KHÔNG phải UI) |
| `device_transport.py:156` exec-out screencap | 30s | screenshot |
| `device_transport.py:172` `_run_cmd` | 30s | ADB shell cmd |

**Rule user chốt: UI capture timeout = 60s là doc TỪ TÂM để UI load — không tăng lên 120/180s.**
Tăng timeout chi làm worker chiếm ADB lâu hơn. Chỉ `adb push` và reboot có timeout dài hơn.

## 3 nhóm lỗi UI capture — phân loại signature

1. **ADB transport lag thật**: `ADB command timeout: ... shell screencap -p /sdcard/screenshot.png` rồi
   `ADB screenshot captured via exec-out fallback` thành công → host/device tải, fallback cứu được.
   → Giảm MaxParallel, ưu tiên exec-out.
2. **UiAutomator/ATX treo**: `uiautomator_idle_state_error`, `uiautomator_null_root_node`,
   `ui_dump_timeout` → ATX/UiAutomator stale trên device. → B1 ATX-kill + `uiautomator quit`.
   KHÔNG phải ADB server load.
3. **Backend chưa provision**: `DEVICE_NOT_PROVISIONED` → persistent UI backend chưa sẵn sàng;
   retry ADB mù vô ích, cần provisioning riêng (atx-agent server + POST /uiautomator).

## Tuning đã áp (2026-08-13)

1. User env: `ADB_SERVER_SOCKET=tcp:localhost:5037` + `ADB_MDNS_OPENSCREEN=0`
   - Ghi nhận: `D:\Taadaa\reports\adb_environment_tuning.md` (13/08 23:40)
   - Nguồn gốc: adb.exe crash `0xc0000409` STATUS_STACK_BUFFER_OVERRUN trong ucrtbase.dll
     khi nhiều lệnh ADB song song port 5037.
   - Verify: `[Environment]::GetEnvironmentVariable(name,'User')`; revert: set $null + `adb kill-server`/`start-server`.
2. `run_tiktok_upload_batch.ps1`: `$MaxParallel` default 30 → 16 (ValidateRange vẫn 1-30).
   - Preflight 80 máy: `Peak active runners: 16/16` OK.
3. `device_transport.py::screenshot`: ưu tiên `exec-out screencap -p` TRƯỚC (1 lệnh ADB duy nhất,
   stream PNG), fallback shell screencap + pull. Đo máy 62: exec-out 0.98s / 416KB.
4. Test version gate `0.4.35` → `0.4.40` trong `tests/test_machine_inventory.py` (test stale — launcher
   đã dùng 0.4.40 từ trước).

## Multi-port ADB — KHÔNG giúp

- ADB server chỉ nghe 1 port (5037 mặc định); mọi client đi qua server đó.
- Mỗi device chỉ gắn được 1 server; muốn chia nhóm phải tách máy từng nhóm riêng port.
- Bottleneck thật: device CPU/GPU render TikTok + USB hub, không phải host port 5037.
- Multi-port chỉ giúp host-side client contention; farm này device-side + USB hub là bottleneck.
- Kết luận: không làm multi-port.

## Hướng chưa làm (nếu cần tiếp)

- Bật `lightweight` capture trong core cho capture thường (settle_delay_seconds, deadline_seconds,
  max_local_recaptures — tránh recovery nặng ATX-kill/relaunch/reboot).
- Tăng settle delay sau tap trước khi dump XML.
- Tắt animation device (`window_animation_scale 0`, `transition_animation_scale 0`,
  `animator_duration_scale 0`) — test 1 máy trước khi áp cả farm.

## Đo cải thiện = LIVE batch, KHÔNG preflight (user correction 13/08)

User yêu cầu "test xem có cải thiện không" → tôi chạy preflight rồi báo kết quả → user phản đối:
*"là sao chưa chạy mà đo prelight cái đéo gì v"*. Preflight chỉ đo inventory (máy eligible/lock),
KHÔNG đo cải thiện upload. Bài học: khi user hỏi cải thiện → chạy live ngay với manifest mới
đúng scope + MaxParallel đã giảm + background + so signature với batch cũ.

## Kết quả live batch Tik2 (49 máy, MaxParallel 16) — tuning KHÔNG sửa fail-closed gates

Batch `batch_tik2_list_49_20260813_092614`: 48 LỖI / 1 SKIPPED_LOCKED (49 mục tiêu).
Signature (đếm report.json):
- 19x `[VIDEO_PICK_TARGET_UNVERIFIED]` — similarity 0.11-0.18 < 0.35, 3 vòng retry, fail-closed
- 17x `[POST_SUBMISSION_UNKNOWN] post_submission_state=UNKNOWN` — không có ACCEPTED evidence
- 3x `DEVICE_STARTUP_FAILED non_xml_ui_dump`, 2x `OPEN_TIKTOK_FAILED`,
  2x `DEVICE_STARTUP_FAILED clear_all/empty-recents`, 1x `uiautomator_idle_state`,
  1x `UI_DUMP_FAILED DISMISS_POPUPS`, 1x `ACCOUNT_SWITCHER_FAILED`,
  1x `VIDEO_PATH_ERROR` (thiếu video), 1x FAILED rỗng

So batch cũ (`batch_tik2_list_43_20260813_002831`): VIDEO_PICK 18/43 (42%) → 19/48 (40%);
POST_UNKNOWN 14/43 (33%) → 17/48 (35%) — **KHÔNG đổi**. Lỗi ADB/UI thuần chỉ ~5/48 (10%).
→ Kết luận: tuning ADB giúp transport lag nhưng không đụng được 2 gate fail-closed lớn.

## Chẩn đoán Tik1 success vs Tik2 fail (cùng code, 13/08)

So cột "Video Đã Đăng" 2 workbook TRƯỚC khi nghi code:
- **Tik1.xlsx**: 73/80 máy đăng 7-15 video (đang vận hành)
- **Tik2.xlsx**: 1/80 máy đăng (máy 62, dang=1) → **Tik2 chưa bao giờ chạy được hàng loạt**

Quy luật mapping: folder slot k máy m = `(m-1)*8+k` (Tik1=+1, Tik2=+2). Máy 5: Tik1 folder 33,
Tik2 folder 34 — cả 2 đủ 45 file mp4. Lỗi Tik2 không phải thiếu file số đông, mà:

- **MediaStore/Gallery stale** (từ lần thử 00:28 sáng nay: push→kill→xóa file để entry cũ):
  picker `recent Video grid` hiện tile cũ → similarity thấp → `VIDEO_PICK_TARGET_UNVERIFIED`
  fail-closed ĐÚNG. m45/52: `best similarity=0.179/0.116 < 0.350` 3 vòng.
- **Receipt cursor drift**: m38 `[POST_RECEIPT_CURSOR] Workbook next=1 nhưng receipt đã completed
  [1,2]; chuyển sang video #3` → resolve video #3 dù workbook dang=0.
- **Thiếu video thật**: m14 `106\3.mp4 not found` — folder 106 thiếu 3.mp4 + 16.mp4 dù count 45
  file (dư/missing).
- **VIDEO_PICK OK nhưng vẫn fail**: m38 tile verified similarity=0.608 → POST →
  `VERIFY_POST: submission state UNKNOWN` → MANUAL_REVIEW (fail-closed đúng, không phải ADB).

Bước tiếp theo hiệu quả nhất: chụp picker thật 1 máy fail (vd m45 `ce0716071586c80602`) để xem
tile TikTok đang hiện gì khi similarity 0.17 — xác nhận chụm MediaStore stale hay video khác.