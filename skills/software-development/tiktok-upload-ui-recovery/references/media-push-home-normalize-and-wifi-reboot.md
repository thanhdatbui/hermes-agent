# Media-Push Home-Normalize + Wi-Fi-After-Reboot (2026-08-11, m74)

Hai root cause class-level phát hiện khi chạy upload m74 (Samsung S7 farm), đã verify live.

## 1. VIDEO_PICK phải bắt đầu từ Home root — Profile/video-detail KHÔNG hợp lệ

### Triệu chứng
- Worker exit 2, report `MANUAL_REVIEW`, reason `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`:
  `Recaptured surface did not prove a labelled bottom-centre create control`.
- Log có dòng `[WAIT_FEED] Root surface confirmed with indicator: 'hồ sơ'` ngay trước
  `Checkpoint saved: MEDIA_PUSH` rồi `>>> State: VIDEO_PICK`.

### Root cause
Sau `MEDIA_PUSH`, `_wait_for_feed()` chấp nhận **bất kỳ root surface TikTok nào**
(`trang chủ`, `hồ sơ`, `đề xuất`) làm "feed-ready". Nhưng `VIDEO_PICK` cần **Home**
(`trang chủ`) vì chỉ Home mới có labelled bottom-centre create control (`+`).
Profile/video-detail không có nút `+` → `_find_bounded_create_button()` trả None → fail-closed.

### Chuỗi fix (2 lớp, đều generic — KHÔNG workaround riêng m74)
1. **Lớp 1** (commit `4b3d5fd`): thêm `_normalize_to_home_for_video_pick` trong
   `_handle_media_push`: sau push, semantic tap bottom tab `Trang chủ`, chờ root
   `trang chủ` + create control, fail-closed `VIDEO_PICK_HOME_NOT_REACHED` nếu không đạt
   trong budget (không fallthrough vào pick từ Profile).
   - Test: (a) root Profile-only → normalize Home; (b) không có create control → fail closed;
     (c) Home có create control → vào pick như cũ.
2. **Lớp 2**: máy thật còn kẹt ở **video-detail fullscreen** (mở video cũ từ Profile):
   không có bottom nav → `taps=0`, không tìm thấy tab `Trang chủ`.
   - Detect: screenshot có back arrow + search bar `Tìm nội dung liên...` + caption tác giả,
     KHÔNG có bottom nav (3-surface phân biệt: Home có bottom nav + nút `+`; Profile có
     bottom nav; video-detail KHÔNG có bottom nav).
   - Fix: Back semantic bounded 1–2 lần (có evidence recapture sau mỗi Back) → về Profile
     (CÓ bottom nav) → tap `Trang chủ` → verify create control → mới vào VIDEO_PICK.

### Pitfall chẩn đoán
- Đừng tin `WAIT_FEED Root surface confirmed` làm bằng chứng "sẵn sàng pick" — chỉ là
  "đang ở TikTok". Verify **create control cụ thể** trước pick.
- Đừng suy luận lifecycle: video-detail có thể là video CŨ mở từ Profile (nhìn ngày
  đăng/`0 lượt xem`), không phải video vừa post. User confirm: acc xem video của mình
  thường ở màn video-detail có like/comment — surface này là trạng thái thường gặp, phải
  xử lý bằng Back→Home, không phải "lỗi UI".

## 2. Máy mất Wi-Fi sau reboot → watcher kẹt WIFI_NOT_READY, không gán proxy

### Triệu chứng
- Upload worker fail `[DEVICE_LOCK_FAILED] ACQUIRE_LOCKS`:
  `required Android VPN is not connected: interface=tun0 tun_up=False ... Device "tun0" does not exist`.
- Watcher stderr lặp: `[WIFI_NOT_READY] Wi-Fi/connectivity unavailable after unlock; readiness callback deferred`.
- `watch-events.jsonl` của máy dừng ở `WATCH_PROXY_READINESS_PENDING` (không có
  `WATCH_EVENT_LOCK_ACQUIRED` / `WATCH_PROXY_APPLICATION_SUCCESS`).

### Root cause
`automation_core.device_recovery.wait_for_wifi()` **chỉ quan sát** (ip addr wlan0 + ping),
không bao giờ bật Wi-Fi (docstring: "never toggles Wi‑Fi"). Sau reboot máy không
auto-connect → radio ON nhưng supplicant DISCONNECTED (RSSI -127) → readiness gate defer
mãi → watcher không apply proxy.

### Chẩn đoán nhanh (ADB)
```bash
adb -s <serial> shell dumpsys wifi | grep -E 'mWifiInfo|Supplicant state'
# SSID: <unknown ssid> ... Supplicant state: DISCONNECTED, RSSI: -127  => mất wifi
adb -s <serial> shell ip addr show tun0     # "Device tun0 does not exist" => chưa gán proxy
```

### Fix thủ công ngay (không cần reboot lại)
```bash
adb -s <serial> shell svc wifi disable && sleep 3
adb -s <serial> shell svc wifi enable       # restart supplicant -> auto-reconnect saved network
# chờ ~30-60s: Supplicant COMPLETED, wlan0 UP + IP; watcher tự apply proxy -> tun0 UP
```
- Android 8 / SDK 26 KHÔNG có `cmd wifi connect-network` — toggle `svc wifi` là cách đúng.
- Không cần nhập credentials: dùng saved network (BOX 1.1, Dat-1...).
- Sau khi wlan0 có IP, watcher GanProxy tự hoàn tất `WATCH_PROXY_APPLICATION_SUCCESS` —
  không cần restart watcher.

### Fix bền vững (đang implement, đúng hướng)
- automation-core `watch_device_reconnect`: thêm `auto_enable_wifi: bool = False`
  (mặc định False, consumer khác giữ hành vi); khi `wait_for_wifi` fail → `svc wifi enable`;
  nếu radio ON mà vẫn chưa connect → toggle `svc wifi disable→enable` MỘT lần, bounded bởi
  stop_event, log `[WIFI_AUTO_ENABLE]`.
- gan-proxy `gan_proxy_fleet.py`: bật `auto_enable_wifi=True` khi gọi `watch_device_reconnect`.
- Watch event path: `D:\CodexRuntime\codex_gmail_debug-gan-proxy\<run_id>\machine-<n>\watch-events.jsonl`.

## Mẹo vận hành khác
- Launch upload worker qua pipe: `echo YES | python -m tiktok_workflow ...` (workflow hỏi
  xác nhận REAL MODE; background không có stdin → EOFError nếu không pipe).
- Lock stale sau worker fail: `owner_active=false, status=handoff` → archive vào
  `~/.codex/device-locks/backup_*` rồi xóa trước khi chạy lại (không xóa thẳng).
