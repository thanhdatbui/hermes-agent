# VPN/Proxy Hard-Stop, Ad Swipe-Up, Device-Lock Guard & GET_IP Retry (20-21/08/2026)

## 1. Step-0 Guards bắt buộc trong AI Auto-Recovery `agent.py` (thứ tự)
Commits: `b6b30c7` (hard-stop VPN) → `34433f3` (device lock guard) → `765c506` (đưa lên đầu pipeline).

1. **Lỗi hạ tầng VPN/Proxy** → DỪNG HẲN machine, KHÔNG chạy ADB / auto-resume (tránh lộ IP thật).
   - Keyword match (error_reason lower): `vichanger`, `vpn`, `proxy`, `get_ip`, `tun0`.
   - Vi phạm thật bị user phạt: máy 33/35 nhận "TỰ ĐỘNG LƯỚT TIẾP" khi VPN fail → user: *"Ủa hạ tầng vpn k có thì sao lại tự động lướt tiếp. Sai rule r nhé"*.
2. **Cross-project device lock** → `inspect_device_lock(machine)` từ automation-core; nếu `owner_active` + status ∈ (running, queued, recovery, failed_locked) → DỪNG NGAY, không can thiệp.
   - Vi phạm thật: máy 1/44 đang bị botmail lock nhưng recovery vẫn đụng → user: *"Máy 1 vs 44 đang bị tiến trình botmail lock mà m vẫn can thiệp đc à? Dừng ngay"*.
   - NOTE: `inspect_device_lock(machine=N)` raise `DeviceLockTransactionError` khi không có lock → bọc try/except hoặc xử lý như "không lock".
3. Sau đó mới tới auto-rollback pre-check (`code_patcher.record_alert`) và pipeline thường.

## 2. Revert handler NHIỄU do lock collision (máy 1/17/38 → revert `90ddc3c`)
- Root cause thật: script khác (hotmail login / add mail) đang chiếm máy, KHÔNG phải lỗi script nuôi.
- User: *"cơ chế lock của nó k đc cron tôn trọng nên chạy cả tiktok nuôi trùng vào hotmail login dẫn tới lỗi. Chứ k phải do script nuôi bị lỗi"*.
- Các handler đã revert: `dismiss_email_account_setup_screen`, `detect_add_account_screen`/`dismiss_add_account_screen`, `detect_email_update_popup`/`dismiss_email_update_popup`.
- Lesson: khi nhiều handler popup "máy lạ" sinh hàng loạt từ nhiều máy cùng lúc, nghi ngờ nguyên nhân MÔI TRƯỜNG (lock collision, VPN) thay vì vá code nuôi.

## 3. Quảng cáo / Sponsored → VUỐT LÊN là chính, Đóng chỉ fallback
- User chốt: *"Sửa lại, đóng chỉ là fallback. Gặp dạng quảng cáo thế này cứ vuốt qua (lưu rule để sau cứ gặp quảng cáo thì vuốt cho nó qua)"*.
- Ad in-feed & overlay: swipe UP (`540,1600→540,400`, ~300ms) như lướt video, tối đa 2 lần; chỉ tap Đóng khi vuốt không qua.
- CẤM áp swipe cho popup quyền hệ thống PackageInstaller (vẫn tick "Không hỏi lại" + TỪ CHỐI).

## 4. Swipe retry = VUỐT LÊN (user sửa: *"Vuốt lên nói nhầm"*)
- `_swipe_recovery_on_stuck` dùng `input swipe 540 1600 540 400 300` (Y giảm = vuốt lên). Đúng.
- PITFALL: rule "không nhận diện được thì vuốt 2 lần" từng KHÔNG hoạt động vì luồng chạm manual_guard / bắn alert Telegram TRƯỚC khi tới swipe recovery. Thứ tự đúng: swipe-recovery chạy → mới báo manual.

## 5. Live room: xem trước 5-9.5s rồi mới đóng (`64bf4d6`)
- `dismiss_tiktok_live_room` thêm `watch_live_sec = round(random.uniform(5.0, 9.5), 2)` + `time.sleep` trước tap X (945,45).
- Khớp rule feed `live_room_exit` 6-14s. User: *"thấy màn hình live thì chờ tý coi live r ms đóng r đó, nãy code chỗ đó có kèm rule đó chưa"*.

## 6. ViChanger GET_IP retry 3×2s (`3a715bb`) — tránh false-positive
- Broadcast `am broadcast -a vn.vichanger.app.GET_IP -n vn.vichanger.app/.AdbCaller` có thể fail TỨC THỜI dù proxy SỐNG (máy 4 17:36 alert "proxy dead/unreachable" nhưng IP thật vẫn chạy).
- Fix: `check_android_vpn` (automation-core/preflight.py) retry 3 lần, cách nhau 2s, chỉ fail sau 3 lần. Vẫn fail-closed (tun0 UP nhưng không verify IP → allowed=False).
- PITFALL patch: file preflight.py KHÔNG import `time` — phải thêm `import time`; dùng python script thay block theo dòng (patch fuzzy bị lệch indent 2 lần).

## 7. Diagnostic recipe proxy/VPN máy (verified máy 4)
```python
# 1. Kiểm tra proxy từ PC với URL-encode password (chứa #, !)
from urllib.parse import quote
proxy = f'http://{quote("mobi4")}:{quote("TaadaaMobi#2026!")}@test.taadaa.click:5104'
requests.get('http://api.ipify.org', proxies={'http': proxy, 'https': proxy}, timeout=12)
# 2. So sánh IP với kết quả browser trên máy (api.ipify.org) — khớp = proxy sống
# 3. Broadcast GET_IP đúng component mới ra result=200 kèm data="IP"
adb.shell(['am', 'broadcast', '-a', 'vn.vichanger.app.GET_IP', '-n', 'vn.vichanger.app/.AdbCaller'])
# -> "Broadcast completed: result=200, data=\"27.69.65.12\""
# 4. Lưu ý: proxy format workbook = host:port:user:pass; URL đúng cần user:pass@host:port
```
- Dict nhớ mapping: máy 4 = port 5104 = mobi4; proxy test.taadaa.click, pass TaadaaMobi#2026! (URL-encode %23 %21).
- Ảnh browser máy 4: Samsung Internet mặc định (không phải Chrome) — mở `android.intent.action.VIEW` với URL api.ipify.org.