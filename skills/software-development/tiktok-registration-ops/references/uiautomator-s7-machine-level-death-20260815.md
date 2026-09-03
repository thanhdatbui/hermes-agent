# uiautomator machine-level death on S7 (SM-G930F) — evidence timeline 2026-08-15

Context: máy 38 (SM-G930F, Android 7, RAM 3.6GB) đang chạy reg TikTok qua Outlook-app
magic-link. uiautomator chết dần trong ngày; bài học cuối cùng: **vẫn chạy ATX-kill
ladder TRƯỚC, chỉ reboot khi ladder hết tác dụng** — và Outlook foreground (không phải
RAM) là thủ phạm giết UiAutomationService.

## Timeline

| Giờ | Sự kiện | dump |
|---|---|---|
| 10:50 | inbox dump OOM "Killed" (mail TikTok tab Ưu tiên không thấy — thật ra nằm tab Khác) | EXIT=137 |
| 11:26 | `adb reboot` → uiautomator sống (22KB dump OK) | EXIT=0 |
| 11:40 | reboot lần 2 → sống (31KB OK) | EXIT=0 |
| 11:47 | mở Outlook → dump lại chết | EXIT=137 |
| 12:38 | `pkill -9 -f atx-agent` + `am force-stop com.github.uiautomator` → **SỐNG LẠI KHÔNG CẦN REBOOT** (phát hiện then chốt) | EXIT=0 |
| 12:39 | atx-agent tự mọc lại (`futex_wait_queue_me` S-state = wedged) — tool 数控安卓投屏 đang mirror máy | — |
| 13:00 | user tắt tool → kill atx + force-stop → sống bền ~20s+ | EXIT=0 |
| 13:41 | kill lần nữa + force-stop lặp 2 lần → sống (sau đó Outlook foreground → chết lại) | EXIT=0 |
| 13:52 | sau nhiều chu kỳ: `am force-stop` KHÔNG còn giết được process, dump EXIT=137 trên MỌI màn hình (launcher/TikTok/Outlook) | EXIT=137 vĩnh viễn |

## Phát hiện quyết định

1. **Outlook app foreground = uiautomator chết, KHÔNG phải RAM**:
   - force-stop TikTok (giải phóng 621MB) → MemFree 355MB, MemAvailable 2.1GB → dump VẪN EXIT=137.
   - Bằng chứng loại trừ OOM: RAM dư thừa vẫn fail.
   - Outlook (WebView nặng + accessibility riêng) làm UiAutomationService crash trên Android 7.

2. **atx-agent tự mọc lại với cmdline `atx-agent server -d --stop`** — process STOP treo
   (không phải agent chạy), nằm `futex_wait_queue_me` (S-state). `pkill -9 -f atx-agent`
   giết được nhưng tool mirror (数控安卓投屏) hoặc process stop sót spawn lại. Sau khi user
   tắt hẳn tool thì hết tự restart.

3. **Sau nhiều chu kỳ kill, service xuống cấp vĩnh viễn**: `am force-stop com.github.uiautomator`
   không còn giết được process (PID tồn tại, `SyS_epoll_wait`), `pkill -9 -f uiautomator` báo
   `Operation not permitted` (vô hại), dump EXIT=137 kể cả trên launcher. Chỉ reboot cứu, và
   reboot chỉ cứu TẠM.

## Quy trình đúng (thứ tự bắt buộc)

```bash
# 1) ATX-kill ladder (skill android-device-automation L387)
adb -s <serial> shell "pkill -9 -f atx-agent"        # SIGKILL, KHÔNG SIGTERM
adb -s <serial> shell "am force-stop com.github.uiautomator"   # lặp 2 lần nếu cần
adb -s <serial> shell "pkill -9 -f uiautomator"      # "Operation not permitted" = vô hại
adb -s <serial> shell "uiautomator dump /sdcard/wd.xml" && echo "EXIT=$?"   # phải EXIT=0

# 2) Chỉ khi VẪN EXIT=137 sau ladder mới reboot thiết bị:
adb -s <serial> reboot && sleep 45 && adb -s <serial> wait-for-device && sleep 25
adb -s <serial> shell "getprop sys.boot_completed"   # =1
adb -s <serial> shell "uiautomator dump /sdcard/wd.xml"
```

## Đọc trạng thái khi dump chết (thay thế)

- `dumpsys activity activities | grep mResumedActivity` — foreground app/activity.
- `dumpsys activity top` — thấy `app:id/drawer_mail_header` = drawer Outlook đang mở.
- `dumpsys window windows` — focus.
- `screencap` + PIL pixel-scan cluster màu (xem dưới) — tìm nút màu đặc trưng KHÔNG cần uiautomator.

## Pixel-scan tọa độ khi uiautomator chết (chain đã thành công 12:16)

Thành công chain thủ công: mở Outlook → tap row mail TikTok 11:47 (540,398) → chụp ngay →
PIL tìm cluster đỏ hồng (nút "Xác minh email": `r>180, g<120, b<120, r-g>80`) → center
(539,1632) → tap → TikTok mở `TransparentCodeVerificationActivity` (link magic-link HOẠT ĐỘNG).

Pitfalls:
- `vision_analyze` báo ảnh 720x1280 / 1080x1450 dù `screencap` ra 1080x1920 (crop theo model)
  → tọa độ vision phải nhân tỷ lệ; tap tọa độ vision trật (mở Settings thay vì mail).
- vision trả tọa độ KHÔNG ỔN ĐỊNH giữa 2 lần gọi cùng ảnh (nút "Xác minh email": y=849 rồi
  y=1085 — chênh 236px) → tap mù rủi ro thoát app.
- PIL đọc file ảnh gốc 1080x1920 trực tiếp — KHÔNG bị crop như vision. Center cluster = tọa độ thật.
- Quy trình an toàn: mở app → tap row → **chụp ngay** → pixel-scan → **tap ngay** (không chụp
  lại giữa chừng — màn có thể đổi), mỗi bước verify `mResumedActivity`; thoát về launcher = tap trật.

Script pixel-scan mẫu (tìm cluster màu thỏa predicate, group theo y liên tục):
```python
from PIL import Image
img = Image.open(path).convert("RGB"); w, h = img.size; px = img.load()
rows = {}
for y in range(0, h, 4):
    c = sum(1 for x in range(0, w, 4)
            if (r := px[x, y][0]) > 180 and px[x, y][1] < 120 and px[x, y][2] < 120 and r - px[x, y][1] > 80)
    if c > 5: rows[y] = c
# group y liên tục (gap <= 12) → với mỗi group tìm x extent → center = tọa độ thật
```
