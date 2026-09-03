# TikTok Follow mode2 — Probe điều hướng Follower máy 1 (2026-08-12)

Probe thành công toàn bộ chuỗi: resolve serial → guard (online/lock/workflow process) →
acquire lock → VPN preflight → tap "Hồ sơ" semantic → dump profile → tap tab Follower →
2 dump follower list/item → release lock. Máy 1 = `9885b64957334f5a46` (SM-G930F,
TikTok 46.3.3), serial hash `2b8f46746584…`, project `tiktok-follow`.

## Node evidence (dump thật qua `tools/dump_selectors.py`, PROBE_OK — KHÔNG suy luận)

### Bottom nav (màn feed)
- Tab **Hồ sơ**: content-desc=`Hồ sơ`, resource-id=`com.ss.android.ugc.trill:id/o3i`,
  FrameLayout `[864,1794][1080,1920]` → tap center (972,1857) rc=0
  - Lưu ý: dump feed còn node `content-desc="Hồ sơ shwesinyokehlwar3"` (id `user_avatar`)
    — tap phải dùng node fullmatch `Hồ sơ` (bottom nav), KHÔNG dùng node có hậu tố username.
  - Nút text `Hồ sơ` (TextView `[864,1864][1080,1903]`) là node con, không clickable.

### Màn Profile (sau tap Hồ sơ)
- Username acc: `@lipsellczaw` — resource-id `com.ss.android.ugc.trill:id/sf5`,
  Button `[412,594][667,639]`
- Tab **Follower**: text=`Follower`, resource-id=`com.ss.android.ugc.trill:id/sdn`,
  TextView `[456,735][624,777]` → tap center (540,756) rc=0 (clickable=false nhưng tap OK)

### Màn Follower list (sau tap Follower)
- Activity marker: `com.ss.android.ugc.trill/com.ss.android.ugc.profile.business.ur.following.ui.FollowRelationTabActivity`
  ← dùng làm bằng chứng navigation thành công qua `dumpsys activity`
- Header user: `lipsellczaw` (id `yby`) + nút "Thêm người" (id `aev`)
- 4 tab header (resource-id `android:id/text1`): `Đã follow 26` `[68,265][354,322]` ·
  `Follower 1` `[426,265][654,322]` · `Bạn bè 0` `[726,265][923,322]` · `Được đề xuất`
  `[995,265][1080,322]` — cột số là COUNT thật (Đã follow 26 = đang follow 26; Follower 1)
- Search bar: icon `kux` (ImageView `[66,409][126,469]`) + EditText `ui8` `[144,385][996,493]`

### Follower item đầu (đủ cấu trúc cho mode2)
- display name: `l Thuận duyên l` → **`com.ss.android.ugc.trill:id/txt_user_name`**,
  TextView `[252,569][590,626]`
- username: `thuanduyen777` → **`com.ss.android.ugc.trill:id/txt_desc`**,
  TextView `[252,632][627,680]`
- nút follow: `Follow lại` → **`com.ss.android.ugc.trill:id/tcj`**, Button clickable=true
  `[672,583][936,667]` — KHÔNG tap (cấm follow trong probe)
- nút phụ: `Khác` (id `ote`, ImageView `[936,553][1080,697]`)

## Quy trình đã chạy (template tái sử dụng cho máy khác)

1. Resolve serial: `taikhoan_run_safe.xlsx` (sheet đầu, headers `May/Device ID/ID`) —
   **dedupe unique serial** (6 dòng/1 máy cùng serial, xem pitfall trong SKILL.md).
2. Guard: `adb devices` online → scan `C:\Users\Kibe\.codex\device-locks`
   (`machine_1.lock.json` + `serial_<s>.lock.json`, PID alive qua wmic) →
   scan process `wmic process where "Name='python.exe' or Name='pythonw.exe'" get
   ProcessId,CommandLine` cho `tiktok_workflow --machine 1` (accept real python only).
3. `acquire_device_lock(..., bypass_proxy_readiness=True)` rồi TỰ check VPN ngay:
   `check_android_vpn(adb, required=serial_is_mapped_in_workbook(PROXYgandienthoai.xlsx,
   serial, serial_headers=("phoneId","deviceId","serial")))` → máy 1: required=True,
   connected=True, tun_up=True, tun0.
4. Foreground: poll `dumpsys activity` tới khi resumed/current focus chứa
   `com.ss.android.ugc.trill` (máy đã ở SplashActivity — không cần launch; nếu cần:
   `am start -W -n <pkg>/com.ss.android.ugc.aweme.splash.SplashActivity`, KHÔNG dùng
   `.main.MainActivity` — lỗi `Error type 3` đã biết).
5. Mọi dump qua `tools/dump_selectors.py` (đòi PROBE_OK); tap semantic = parse dump →
   chọn node fullmatch → tap center từ bounds → recapture. Dump treo (rc!=0) → chỉ
   `pkill -9 -f atx-agent` + `pkill -9 -f uiautomator` (recovery chuẩn), retry 1 lần.
6. Release trong `finally` + verify cả 2 lock file không tồn tại.

## Kết quả guard/lock/VPN

- Lock acquired `75fee93d…`; release: `machine_1.lock.json` + `serial_9885b64957334f5a46.lock.json`
  (verify sau release: cả 2 không tồn tại; lock ngoại máy 13/15/78 giữ nguyên).
- Không bấm Follow, không switch acc, không force-stop/reboot, không sửa workbook, không commit.
- Artifacts: `D:\taadaa\tiktok-follow\runs\probes\manifest_20260812T062735Z_2b8f46746584_mode2-nav.json`
  + `capture_20260812T062629Z_…_profile.*` / `…_follower-list.*` / `…_follower-item.*`
  (49 nodes, fg `com.ss.android.ugc.trill`).

## Pitfall riêng của session

- **`Path + str` crash ngay cuối**: ghi manifest sau khi mọi dump đã PROBE_OK bị
  `TypeError: WindowsPath + str` → manifest mất. Cách cứu: rebuild manifest từ artifact
  (đọc lại dump JSON/XML thật + log stdout), KHÔNG chạy lại probe (tránh tap trùng).
- Feed có 2 node chứa "Hồ sơ" (bottom-nav `o3i` fullmatch + avatar `user_avatar` có
  hậu tố username) — chọn node fullmatch.
