# Tiktok_Reg recovery 2026-08-06 (tiếp) — transport reboot, VPN set_proxy, workbook restore

Session detail cho run recovery 10 máy (STT 30,31,34,36,38,39,54,55,57,66) +
retry 6 máy. Bổ sung cho `tiktok-reg-recovery-20260806.md`.

## 1. uiautomator `Killed` EXIT=137 — toàn farm, reboot là fix duy nhất

Triệu chứng (máy 54 trước tiên, sau đó cả 7 máy):
```
$ adb -s <serial> shell "uiautomator dump /sdcard/wd.xml 2>&1; echo EXIT=$?"
Killed
EXIT=137
```
Logcat xác nhận root cause:
```
E AndroidRuntime: at android.app.UiAutomation.connect(UiAutomation.java:223)
E AndroidRuntime: at com.android.commands.uiautomator.DumpCommand.run(...)
E AndroidRuntime: java.lang.RuntimeException: Bad file descriptor
```
→ `UiAutomationService` bị treo (stale ATX/uiautomator giữ service), KHÔNG phải
ADB mất. atx-agent process vẫn sống (`ps -A | grep atx`) nhưng persistent
capture không hoạt động → core báo
`ADB_TRANSPORT_LOST_AFTER_VERIFIED_PERSISTENT_CAPTURE` (circuit breaker mở sau
khi persistent backend từng verified rồi fail — đây là CẤP CORE, consumer chỉ
xử lý được bằng cách reset máy).

Đã thử KHÔNG ăn:
- `pkill -f uiautomator` → `Operation not permitted`
- `am force-stop com.github.uiautomator` → kill process cũ nhưng atx-agent
  spawn lại ngay (pid mới), dump vẫn Killed
- kill + restart atx-agent (`/data/local/tmp/atx-agent server -d`) → vẫn Killed
- `settings get secure accessibility_enabled` = 1 nhưng
  `enabled_accessibility_services` = null

**Fix duy nhất: `adb reboot` mềm.** Sau reboot: `uiautomator dump` trả
`EXIT=0` (`UI hierchary dumped to: /sdcard/wd.xml`). Trình tự chuẩn:
```bash
adb -s <serial> shell "ip addr show tun0 | grep inet"   # ghi nhận VPN trước
adb -s <serial> reboot
adb -s <serial> wait-for-device
sleep 25 && adb -s <serial> shell getprop sys.boot_completed   # =1
# rồi phải gán lại VPN (mục 2) — reboot KHÔNG tự lên VPN
```

## 2. VPN sau reboot: watcher chạy nhưng KHÔNG gán lại — fix = tự gọi set_proxy()

Sau khi reboot 7 máy: `tun0` KHÔNG lên dù watcher `gan_proxy_fleet.py watch`
vẫn chạy (2 process). Không có fleet-run/log mới trong
`D:\CodexRuntime\codex_gmail_debug-gan-proxy` sau reboot → watcher không xử lý
máy reboot (chỉ xử lý khi có reconnect event mới / hoặc kẹt).

Mở app thủ công thấy vichanger vào `LoginActivity`:
- `text="Vi Changer" / "API Key" / "Change"` (cần API key)
- hoặc popup `No LSPosed access !!!` (nút OK bounds [1308,655][1500,799])
- process `vn.vichanger.app` chạy nhưng `tun0` không có `inet`

**Fix hiệu quả — tự gọi `set_proxy` từ vi_changer_runner** (đúng cơ chế watcher:
mở app + broadcast `START_VPN` với proxy value → app connect, ~5-40s):
```python
# D:\Taadaa\gan-proxy\scripts
from vi_changer_runner import set_proxy, vpn_connected
set_proxy(ADB, serial, proxy, timeout=45)   # proxy từ PROXYgandienthoai.xlsx cột proXy
vpn_connected(ADB, serial)                   # True sau khi tun0 có inet
```
Kết quả thực tế: cả 6 máy (30,31,36,54,57,66) lên `tun0` sau `set_proxy`
trong 1 lượt. Proxy mapping đọc từ
`D:\OneDrive\codex_gmail_debug\PROXYgandienthoai.xlsx` (header `Máy / device ID / proXy`).

Sau đó verify toàn farm trước retry:
```bash
adb -s <serial> shell "ip addr show tun0 | grep -c inet"      # =1
adb -s <serial> shell "uiautomator dump /sdcard/wd.xml 2>&1; echo E=$?"  # E=0
```

## 3. Khôi phục mail bị xóa nhầm (STT 54) — restore từ backup + xóa Audit Pending sai

Mail 54 bị xóa nhầm theo logic mail-die cũ (thực chất chỉ bị Microsoft
"Protect your account" chặn, KHÔNG die). User: *"k đc xoá khỏi excel, mail có
die đéo đâu, cấm tự tiện xoá ngoài rule xác định mail die"*.

Restore pattern (đã làm, script `scripts/restore_stt54_source.py` +
`scripts/remove_audit_stt54.py`):
1. Đọc dòng đúng từ backup pre-delete:
   `.runtime/Taadaa/Tiktok_Reg/workbook-backups/gmail_clean_v2_before_captcha_delete_<email>_<ts>.xlsx`
   (dòng 191: `('54','eulaliaphilomenaclementina7@hotmail.com','sOWjyO6488',...)`).
2. Backup source hiện tại trước khi sửa (`gmail_clean_v2_before_restore_stt54_<ts>.xlsx`).
3. `ws.insert_rows(target_idx, 1)` tại vị trí gốc: trước dòng đầu tiên có máy > 54
   (giữ thứ tự máy 54 liền nhau), copy toàn bộ giá trị từng cột.
4. Reopen + verify mail có mặt.
5. Xóa Audit Pending sai tương ứng (sheet `Audit Pending`, tìm theo email;
   backup tracking trước khi `delete_rows`).

Lưu ý: header tracking `Audit Pending` đọc qua openpyxl values_only ra toàn
None (sheet không có header thật) — tìm theo giá trị email, không theo header.

## 4. STT 30 — `[04_add_account]` Không tìm thấy nút "Thêm tài khoản" (2 lần cùng signature)

Flow: vào Profile OK → account dropdown sheet "verified" (screenshot
`30_03_dropdown_*.png`) → tap Add account → dump lúc fail
(`fail_04_add_account_*.xml`) vẫn là **Profile screen**, không phải sheet:
```
rid=...u68 text/desc=Lưu bản nháp | bounds=[240,231][618,327]
rid=...tk1 text/desc=Chỉnh sửa | bounds=[642,231][1020,327]
rid=...scn text/desc=@ninhvan04061999 | bounds=[335,594][745,639]
rid=...s8h text/desc=Thêm tiểu sử | ...
```
→ "verified account dropdown sheet" là **false positive**: verifier nhận nhầm
Profile (có avatar/chevron) là sheet đã mở, nút "Thêm tài khoản" thật không
xuất hiện. Lặp đúng signature 2 lần (run 06:52 và 10:24) → dừng, cần fix
verifier account-sheet (phân biệt Profile root vs sheet thật — sheet có
"Chuyển đổi tài khoản"/"Thêm tài khoản khác" node, Profile có "Lưu bản nháp"/
"Chỉnh sửa") trước khi retry. KHÔNG retry mù lần 3.

## 5. Kết quả retry lần 3 (run 20260806-102439, sau reboot + VPN)

- STT 30: FINAL_BLOCKED `[04_add_account]` (mục 4)
- STT 31/34/36/57/66: còn chạy khi hết phiên — 34 fix OTP đã ăn (hết "Skip
  stale"), nhưng máy chuyển sang `target_account_unverified` vì Gmail UI dump
  thiếu selected_account node (uiautomator treo lúc đó).
- Bài học: sau reboot + VPN, retry mới có nghĩa — các run trước fail vì
  transport/VPN chứ không phải business flow.
