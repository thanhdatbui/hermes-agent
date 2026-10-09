# TikTok Account Switcher Inventory Probe (Read-Only)

**Purpose**: Verify whether a specific account (e.g. `miumiu67971`) is present on a farm device **without logging in/out or disturbing the active session**.

**Canonical recipe** (proven live on STT 05, 2026-09-08):

## Step-by-step

### 1. Confirm device online
```bash
ADB="C:/Program Files (x86)/xiaowei/tools/adb.exe"
SERIAL="<device-serial>"
"$ADB" devices | grep "$SERIAL"
```

### 2. Launch TikTok
```bash
"$ADB" -s "$SERIAL" shell "am start -n com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity"
sleep 8   # wait for feed to render (splash activity label may persist after feed is up — ignore it)
```

> ⚠️ **Pitfall**: `dumpsys activity activities | grep mResumedActivity` may still show `SplashActivity` even after the feed is fully rendered. Use ATX XML dump to confirm real state — if you see `Trang chủ`, `Hồ sơ`, etc., TikTok is loaded.

### 3. Get ATX PID and set up forward
```bash
PID=$("$ADB" -s "$SERIAL" shell "ps -A" | grep -E ' com\.github\.uiautomator$' | awk '{print $2}' | tr -d $'\r')
"$ADB" -s "$SERIAL" forward tcp:7912 tcp:7912
```

### 4. Confirm feed is loaded (ATX dump)
```bash
curl -s -X POST "http://127.0.0.1:7912/session/${PID}:com.github.uiautomator/jsonrpc/0" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"dumpWindowHierarchy","params":[true]}' \
  --max-time 15 | python3 -c "
import sys,json,re
d=json.load(sys.stdin)
r=d.get('result','')
all_text = re.findall(r'text=\"([^\"]{2,})\"', r)
print(all_text[:30])
"
```
Expected on feed: `['Trang chủ', 'Hộp thư', 'Hồ sơ', ...]`

### 5. Navigate to Profile tab
Find `text="Hồ sơ"` bounds in XML, then ATX-click center:
```bash
# Profile tab is typically around (972, 1883) on 1080x1920 S7
curl -s -X POST "http://127.0.0.1:7912/session/${PID}:com.github.uiautomator/jsonrpc/0" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"click","params":[972,1883]}' \
  --max-time 10
sleep 3
```

Then re-dump XML and confirm `@username` node is visible.

### 6. Tap display name to open Account Switcher
Find the clickable display-name node (resource-id `id/su7` in TikTok 46.x) on profile.
> ⚠️ **BẪY TỌA ĐỘ CỐ ĐỊNH CỦA `id/su7`**: Tọa độ của `id/su7` có thể thay đổi tùy tài khoản / UI state (vd: STT 05 có bounds `[36,280][568,364]` tâm (302, 322), nhưng STT 03 có bounds `[353,519][726,585]` tâm (540, 552)). **CẤM hardcode tap mù (302, 322)**. Phải parse bounds từ XML của node `id/su7` (hoặc text trùng username) để lấy tâm chính xác:

```python
import xml.etree.ElementTree as ET, re

root = ET.fromstring(xml_content)
for node in root.iter('node'):
    res_id = node.attrib.get('resource-id', '')
    if 'id/su7' in res_id:
        m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.attrib.get('bounds', ''))
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            print(f'Switcher anchor center: ({cx}, {cy})')
            # call click([cx, cy])
            break
```

> ⚠️ **Do NOT tap `id/sr3`** (`@username` body node) — this is the "copy handle" button, not the switcher anchor. Only `id/su7` (display name) opens the switcher.

### 7. Dump XML and read account list
```bash
curl -s -X POST "http://127.0.0.1:7912/session/${PID}:com.github.uiautomator/jsonrpc/0" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"dumpWindowHierarchy","params":[true]}' \
  --max-time 15 | python3 -c "
import sys,json,re
d=json.load(sys.stdin)
r=d.get('result','')
all_text = re.findall(r'text=\"([^\"]{2,})\"', r)
print('Accounts in switcher:', all_text)
target = 'miumiu67971'   # <-- change this
print('FOUND' if target in r else 'NOT FOUND', ':', target)
"
```

The switcher lists format: `['Chuyển đổi tài khoản', '<nick1>', '<nick2>', ..., 'Thêm tài khoản']`

---

## In-App Account Logout Flow (Đăng xuất tài khoản an toàn)

Khi cần đăng xuất một tài khoản cụ thể (vd `miumiu67971`) mà không làm ảnh hưởng các tài khoản khác trên máy (TUYỆT ĐỐI CẤM `pm clear`):

1. **Kiểm tra tài khoản active**:
   - Nếu tài khoản active hiện tại TRÙNG với tài khoản cần đăng xuất -> vào thẳng bước 3.
   - Nếu KHÁC -> mở Account Switcher (bước 6), tìm row có `content-desc="<target_nick>"` hoặc text trùng `<target_nick>`, tap vào để switch sang tài khoản đó. Chờ 3-5s để profile load xong tài khoản mục tiêu.
2. **Mở Menu hồ sơ**:
   - Node `desc="Menu hồ sơ"` nằm góc trên bên phải, bounds thường là `[948,96][1056,204]`, tâm `(1002, 150)`.
   - Tap mở Menu hồ sơ.
3. **Mở "Cài đặt và quyền riêng tư" (Settings and Privacy)**:
   - Menu trượt lên từ dưới, tìm node có `text="Cài đặt và quyền riêng tư"` (hoặc icon bánh răng cài đặt) -> tap vào.
4. **Cuộn xuống cuối và chọn Đăng xuất**:
   - Vuốt lên: `adb shell input swipe 540 1600 540 400 300` (1-2 lần).
   - Tìm node `text="Đăng xuất"` -> tap vào.
   - Dialog xác nhận xuất hiện (*"Bạn có chắc chắn muốn đăng xuất không?"*): tap nút `"Đăng xuất"` (hoặc `"Chuyển đổi tài khoản"` / `"Đăng xuất"` nếu có tùy chọn lưu thông tin).
5. **Nghiệm thu và xác minh**:
   - Mở lại Account Switcher, dump XML xác nhận `<target_nick>` đã biến mất khỏi danh sách.
   - Chụp ảnh màn hình nghiệm thu:
     ```bash
     "$ADB" -s "$SERIAL" shell "screencap -p /sdcard/logout_verify.png"
     "$ADB" -s "$SERIAL" pull /sdcard/logout_verify.png "D:/Taadaa/reports/<filename>.png"
     ```
   - Gửi ảnh qua `MEDIA:D:/Taadaa/reports/<filename>.png` cho user.

### 8. Cleanup
```bash
"$ADB" -s "$SERIAL" shell "am force-stop com.ss.android.ugc.trill"
"$ADB" -s "$SERIAL" shell "input keyevent 3"   # HOME
"$ADB" -s "$SERIAL" forward --remove tcp:7912
```

---

## Key IDs (TikTok 46.x, SM-G930, 1080x1920)

| Element | Resource ID | Notes |
|---|---|---|
| Display name (switcher anchor) | `id/su7` | Tap this to open switcher |
| @username copy button | `id/sr3` | Do NOT tap — opens "rename" or just copies |
| Account row in switcher | `id/lkp` | Has `content-desc="<username>"` |
| Profile bottom tab text | `text="Hồ sơ"` | Bounds typically [864,1864][1080,1903] |

## Notes

- The account list appears as `content-desc` on `id/lkp` nodes — also as plain `text` nodes in the switcher sheet.
- Up to 7+ accounts visible in the switcher without scrolling (tested with 7 accounts).
- **`mResumedActivity` showing `SplashActivity` is a known false-alarm** on TikTok — use ATX XML as ground truth, not `dumpsys`.
- ATX forward port: Can use fixed `tcp:7912` for single-machine read-only probe. Use dynamic `tcp:0` for multi-machine batch to avoid conflicts.
