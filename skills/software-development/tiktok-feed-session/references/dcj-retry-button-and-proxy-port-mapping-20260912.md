# DCJ Retry Button + Proxy Port Mapping (Case 147 — 12/09/2026)

## Lỗi: "profile username still mismatched after switch" (M33)

### Root cause chuỗi
1. Sau khi `tap_expected_account` trong Account Switcher, TikTok hiển thị màn hình lỗi mạng **"Đã xảy ra lỗi / Thử lại sau"** với nút **"Thử lại"** (`id/dcj`).
2. Code kiểm tra `recaptured_xml = str(latest_identity.get("xml_text") or "")` trả về string-repr của object thay vì XML thuần → `"id/dcj" in recaptured_xml` = `False` → nút không được tap.
3. Switch thất bại 3 lần → `auto_login_recovery` → phiên chạy >10 phút.

### Fix (commit 1623c41)
Trong `verify_and_switch_profile` của `feed_swipe_smoke.py`:
- Đọc XML trực tiếp từ `latest_identity.get("xml_path")` hoặc Path artifact / `ui.xml`
- Check `dcj`, `thử lại`, `đã xảy ra lỗi` trong XML
- Nếu tìm thấy: `ctx.adb.shell(["input", "tap", cx, cy])` với cx/cy tính từ bounds node, sleep 3s, re-read identity

### Nút "Thử lại" (id/dcj) — đặc điểm XML
```xml
<node resource-id="com.ss.android.ugc.trill:id/dcj"
      text="Thử lại"
      clickable="false"   <!-- Quan trọng: clickable=false nhưng tap ADB vẫn ăn -->
      bounds="[296,1358][785,1514]" />
```
- **Center**: `(540, 1436)` (tính từ bounds `[296,1358][785,1514]`)
- `clickable="false"` không ngăn ADB `input tap` — bấm vào toạ độ tâm hoạt động tốt
- Nằm trong màn hình lỗi mạng sau khi switch account

---

## Proxy Port Mapping — Kibe Farm

### Cấu trúc
- **sing-box mixed inbound** (có auth, route qua MikroTik): `192.168.110.2:20001` đến `192.168.110.2:20080`
  - Công thức: **port = 20000 + machine_number**
  - M1=20001, M2=20002, ..., M33=20033, ..., M80=20080
- **MikroTik trực tiếp** (Kibe 14 máy, cần auth Android tự xử lý): `192.168.110.2:10001` đến `192.168.110.2:10007`

### Xác minh proxy máy N
```bash
adb -s SERIAL shell "settings get global http_proxy"
# Kết quả đúng: 192.168.110.2:200XX (XX = machine_number)

# Test port còn sống:
adb -s SERIAL shell "toybox nc -w 3 192.168.110.2 200XX </dev/null && echo OPEN || echo CLOSED"
```

### Sửa proxy ADB (khi bị gán sai)
```bash
adb -s SERIAL shell "settings put global http_proxy 192.168.110.2:200XX"
adb -s SERIAL shell "am force-stop com.ss.android.ugc.trill"
```

### Cạm bẫy quan trọng
- **PC không test được proxy bằng urllib** — proxy 20033 trả 502 khi gọi từ PC vì auth chỉ hoạt động qua Android credential forwarding. Đừng kết luận proxy chết dựa trên kết quả curl/urllib từ PC.
- Nếu M33 baseline fail "network error" ngay từ đầu → kiểm tra proxy ADB trước khi debug code.
- Tôi (Coordinator) đã từng swap sai M33 từ 10001 sang 20033 rồi revert lại — phải biết đúng port cho từng máy.

### set_proxy_farm_adb.py
Script `D:/Taadaa/AI-Tools/scripts/set_proxy_farm_adb.py` gán proxy hàng loạt theo mapping.
**CẢNH BÁO**: Chạy script này ghi đè proxy hiện tại của tất cả máy chỉ định — verify port đúng trước khi chạy.

---

## Canary chuẩn cho feed-session (không block session)

```bash
# Chạy canary — timeout TỐI ĐA 90s (Hard Gate #5 sẽ chặn nếu > 90s)
powershell.exe -ExecutionPolicy Bypass \
  -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" \
  -Machines 33 -Row 3 -RecoveryTestSwipes 1 \
  -SkipAccountWorkbookSync -Run
# timeout=90

# Poll log kết quả:
LATEST_LOG="D:/Taadaa/tiktok-luot nuoi acc/.ai-runs/YYYYMMDD-HHMMSS/machines/machine_33/.../log.jsonl"
tail -n 20 "$LATEST_LOG" | python -c "
import sys, json
for l in sys.stdin:
    d = json.loads(l)
    print(f\"{d.get('step','?')[:50]} | {d.get('action','?')} | {d.get('result','?')}\")
"
```

Bước kiểm tra kết quả nhanh sau canary:
- `grep "mismatched\|profile_preflight_verify\|follow\|for-you" log.jsonl` → đủ để thấy luồng switch
- Nếu `profile_preflight_verify_N_retry` có `result=success` → fix thành công
