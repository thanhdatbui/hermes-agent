# Vichanger VPN app (vn.vichanger.app) — Tiktok-video farm

App tạo `tun0` cho máy farm (máy 74, 30, 34…). Workflow upload (Tiktok-video,
`tiktok_workflow`) fail-closed ở `ACQUIRE_LOCKS` khi VPN chưa lên:
`live VPN verifier failed: ... interface=tun0 tun_up=False vpn_connected=False
error=Device "tun0" does not exist` → DEVICE_LOCK_FAILED.
Recovery 3-bước UI (ATX-kill → force-stop → reboot) KHÔNG cứu được lỗi này —
đây là lỗi VPN verifier, không phải lỗi UI. Phải connect VPN trước khi chạy.

## Chẩn đoán nhanh

```bash
adb -s <serial> shell "ip addr show tun0 2>/dev/null | grep -c inet"   # 0 = chưa lên
adb -s <serial> shell "ps -A | grep -i vichanger"                      # process chạy chưa
adb -s <serial> shell "pm list packages | grep -i vichanger"           # package cài chưa
adb -s <serial> shell "am broadcast -a vn.vichanger.app.GET_IP -n vn.vichanger.app/.AdbCaller" # result=200 data="ip"
```

## Popup "No LSPosed access !!!" — LÀ NHIỄU, KỆ NÓ

- Máy 34 (tun0=1, VPN OK) cũng KHÔNG có package LSPosed trong `pm list packages`.
- Mọi máy farm đều kêu popup này khi mở app — nó không chặn connect.
- KHÔNG mất thời gian kiểm tra LSPosed / enable module / dismiss popup.

## Blocker thật: "Invalid API Key!!!" — trường API Key TRỐNG

- Open app → nhập API key (trường "API Key" trên card trắng, cần tap nút teal
  "Change" để connect). Key là SECRET của user — không đoán, hỏi user.
- Vichanger version 25.01.01, không root được (`run-as` → NO_PREFS_ACCESS),
  không lấy key từ prefs. Key không nằm trong config yaml runtime.
- Nếu máy chưa từng nhập key (hoặc bị reset), workflow fail mãi ở ACQUIRE_LOCKS
  → báo blocker ngắn + hỏi key, KHÔNG tự sửa lung tung.

## Popup "Message" (native dialog) trên Vichanger

Dialog trắng giữa màn hình, nút OK tím góc dưới-phải. Dismiss bằng tap đúng tọa
độ OK — xem phần orientation bên dưới để không tap trượt.

## BẪY ORIENTATION: screencap có thể là LANDSCAPE

Máy m74 từng trả `screencap` 1920x1080 (landscape) trong khi mặc định tưởng
1080x1920 portrait — mọi `input tap` theo tọa độ portrait trượt hết (popup OK
không tắt dù tap 5 lần). TRƯỚC KHI TAP: đọc kích thước ảnh thật:

```python
from PIL import Image
img = Image.open(png_path)   # in img.size trước khi suy tọa độ
```

Nếu tap trượt nhiều lần: crop vùng nghi có nút → `vision_analyze` hỏi tọa độ
chính xác trong ảnh gốc → map ngược (orig = crop_offset + relative) → tap.

## Lệnh bật VPN thủ công (khi đã có key)

```bash
adb -s <serial> shell "monkey -p vn.vichanger.app 1 || am start -n vn.vichanger.app/vn.vichanger.app.MainActivity"
sleep 10
adb -s <serial> shell "ip addr show tun0 2>/dev/null | grep -c inet"   # chờ = 1
```

## Note config runtime

`config-machine-74.yaml` từng bị copy nhầm `machine: "62"` từ config 62 — khi
tạo config máy mới, verify field `machine:` khớp tên file (workflow dùng
`--machine N` CLI override nên không fail, nhưng gây nhầm lẫn).

## Quy tắc user (2026-08-11, Tiktok-video máy 74)

"Pop up của app vichanger kệ mẹ nó, việc của mày là Mở tiktok chạy upload video.
Lỗi xong r ms đc recovery" → workflow chạy TRƯỚC, recovery/修复 chỉ SAU khi
workflow báo lỗi thật. KHÔNG pre-dismiss popup app, KHÔNG tự sửa VPN bằng tay
trước khi chạy. Nếu workflow fail vì VPN thiếu key → báo blocker + hỏi user,
KHÔNG tự nhập đại.