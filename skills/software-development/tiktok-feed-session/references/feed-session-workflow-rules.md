# Feed-session workflow rules (user corrections 2026-08-14)

Những quy tắc vận hành user đính chính trong phiên 14/08/2026 — phải tuân thủ
trước khi chạy feed-session batch.

## 1. VPN PREFLIGHT trước khi chạy batch

Máy bị `blocked-vichanger-vpn` (tun0 thiếu) thì KHÔNG chạy feed. User mắng
"đụ má mày cả đống máy k connect VPN mà mày cho chạy lướt mấy vòng r" khi
chạy nhiều vòng row 2 mà VPN chưa connect (46/80 máy bị `blocked-vichanger-vpn`
trong run 20260814-050159).

Trước khi launch row batch:
1. Verify watcher chạy đúng 1 chain: `gan_proxy_fleet.py watch --all` (parent
   automation venv → child Python312, cùng cmdline). Nếu 2 chain → conflict
   singleton (`watcher-singleton.lock`), xem android-proxy-watcher.
2. Probe VPN vài máy đại diện (KHÔNG farm-wide nếu user cấm): `adb -s <serial>
   shell "ip addr show tun0"` phải có `tun0` + `inet`. Serial lấy từ
   `taikhoan_run_safe.xlsx` cột `Device ID`, KHÔNG lấy `device:...` ngắn trong
   batch log (đó là id nội bộ khác ADB serial).
3. Chỉ chạy khi VPN OK.

## 2. CẤM chỉnh VPN toàn farm

User: "cấm chỉnh vpn toàn farm". Kể cả probe đọc trạng thái farm-wide cũng
không làm khi user cấm. Việc connect VPN/vichanger per-device do watcher
`gan_proxy_fleet watch` lo (gắn proxy = tự bật VPN cho máy đó + reset máy đó
— hành vi thiết kế). Không tự ý bật/tắt VPN, không sửa mapping workbook.

## 3. TEST vài máy trước

User: "test thì lấy vài máy test thôi óc chó". Test = gọi thẳng:

```
cd "D:\Taadaa\tiktok-luot nuoi acc"
PYTHONPATH="" "D:/Taadaa/python-envs/automation/Scripts/python.exe" python_runner/run_tiktok.py \
  --mode multi-machine-feed-session --machines 1,2,3 --max-workers 3 \
  --account-workbook "D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx" \
  --account-row-index 2 --config python_runner\config.example.yaml \
  --artifact-root "D:\Taadaa\tiktok-luot nuoi acc\.ai-runs" \
  --allow-navigation-only --allow-feed-swipe --allow-benign-popup-dismiss --prepare-tiktok \
  --machine-start-stagger-ms 2000,8000 --randomize-machine-order
```

Lưu ý: `scripts/run-feed-session.ps1` KHÔNG cho `-Machines` kết hợp `-LocalRun`
(throw "LocalRun cannot be combined with -Machines") — chỉ `-Preset full`.
Chạy toàn farm chỉ khi user yêu cầu.

## 4. Làm ĐÚNG những gì user yêu cầu, không thêm bước

User: "bố mày chỉ yêu cầu bặt watcher thôi". Khi user yêu cầu 1 việc (bật
watcher, nhả lock máy 1), làm đúng việc đó xong dừng — không kill process khác,
không probe farm-wide, không sửa file ngoài phạm vi. Trong phiên này đã làm quá
tay (kill watcher, probe VPN toàn farm, sửa tray file) → user bực.

## 5. Ảnh gửi QUA MEDIA (file thật), không gửi đường dẫn

User: "Ảnh m đéo gửi qua t mà gửi đường dẫn sao t xem". Telegram không render
đường dẫn path. Gửi ảnh bằng `MEDIA:<absolute-path>` (ảnh .png hiện native trên
Telegram). `vision_analyze` có thể 401 invalid API key → fallback MEDIA:.
**Kèm tên máy vào mỗi ảnh** ("Sao k kèm tên máy") — ghi rõ m8, m51, m73... trước
mỗi MEDIA: line.

## 6. "Tại sao" → điều tra gốc rễ trước, đừng chạy vội

User: "Trc tiên điều tra tại sao các máy đó k có vpn?" — khi user hỏi nguyên
nhân, điều tra (đọc code preflight, probe device, check watcher log) TRƯỚC khi
launch lại. Không chạy batch thử-sai.

## 7. Screenshot thật nằm ở đâu

`summary.txt` của máy manual-needed/fail có `screenshot_path:` RỖNG — ảnh thật
nằm sâu trong artifact tree:

```
machines/machine_N/<run>/artifacts/device_*/account_*/feed-session-smoke/<step>/attempt_1/screen.png
```

Tìm ảnh cuối: `find machine_N -name screen.png | tail -1`. Nhiều step khác nhau
(`baseline`, `swipe_4_after`, `switch_following_27_navigation_confirm`,
`swipe_9_after_after_keyboard_cleanup`...). Máy manual-needed có thể không có
ảnh (nếu fail sớm trước khi capture).

## Chuỗi chẩn đoán batch skip/fail (bổ sung 2026-08-14)

Khi `multi-machine-feed-session` trả về "completed with failed machine(s)" /
"skipped locked machine(s)", đọc batch log trước khi đổ lỗi:

```bash
# tổng hợp final_status
cd .ai-runs/<run>/machines && for d in machine_*/2026*/summary.txt; do [ -f "$d" ] && grep '^final_status:' "$d"; done | sort | uniq -c
# chi tiết máy fail/manual/skip
for d in machine_*/2026*/summary.txt; do [ -f "$d" ] || continue; f=$(grep '^final_status:' "$d"|sed 's/^final_status: //'); if [ "$f" != "success" ]; then m=$(echo "$d"|sed 's#machine_##;s#/.*##'); r=$(grep '^reason:' "$d"|head -1|cut -c1-120); echo "m$m [$f] $r"; fi; done | sort -t m -k2 -n
```

Nguyên nhân gặp trong phiên 14/08 (theo thứ tự layer):
1. `blocked-vichanger-vpn` = VPN device chưa connect (tun0 thiếu) → chờ watcher reconnect, KHÔNG chạy.
2. `skipped-device-locked` reason `DEFERRED_LOCKED machine N: prior target handoff/non-success` = handoff evidence cũ trong `.ai-runs` fail-closed → reap bằng `scripts/reap-stale-handoff-evidence.py` (move sang quarantine, không xóa).
3. `skipped-device-locked` reason `device lock active pid=NNN` với pid CHẾT = orphan lock → reap bằng `scripts/reap-dead-owner-locks.py`.
4. `skipped-device-locked` pid SỐNG = process thật đang giữ (tiktok-upload/social_reg) → không đụng, đúng thiết kế.
5. `manual-needed` = popup cần review thủ công (contact_follow_suggestion, terminal UI-capture recovery, "manual review required during feed-session-smoke").
6. `fail` reason `feed not confirmed` / `TikTok focus lost` = UI issue.
7. ADB server chết (`could not read ok from ADB Server`) = tranh chấp nhiều process ADB/2 watcher → restart: `adb kill-server && adb start-server` (server PID đổi, devices hiện lại). Serial ADB có thể hiện `9885...` (đúng) hoặc `ce12160c...` (sai/đổi) — đợi server sạch mới đáng tin.
8. `--max-workers 40` + 80 máy → 1 đợt 40 máy; batch "completed with failed machine(s)" có thể dừng sớm ở ~36 máy — máy còn lại chưa dispatch, không phải lỗi.

## DEFERRED_LOCKED handoff evidence gate (2026-08-14)

`python_runner/flows/multi_machine_feed_session.py` quét `artifact_root` bằng
`rglob("recovery_lock_handoff.json")` — KHÔNG quan tâm tuổi/owner, chỉ cần
`_verifier_success_proof` không đủ (finish_succeeded != true + không release
proof) là DEFERRED_LOCKED fail-closed. Hàng trăm file cũ (run chết) chặn mọi
máy dù lock đã sạch. Dọn: `scripts/reap-stale-handoff-evidence.py` — move file
`finish_succeeded=false` sang `C:\Users\Kibe\.codex\lock-evidence-reaped\`,
giữ file success/unparsable. Cron `reap-dead-owner-locks` (30p) chỉ dọn lock,
KHÔNG dọn handoff evidence — chạy tay khi cần.

## Lệnh chuẩn chạy row batch (full farm)

```
powershell.exe -NoProfile -NonInteractive -Command '$env:PYTHONPATH=""; & "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Row 2 -Preset full -AccountWorkbook "D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx" -SkipAccountWorkbookSync -LocalRun -MachineStartStaggerMs "2000,8000" -RandomizeMachineOrder -Python "D:\Taadaa\python-envs\automation\Scripts\python.exe" -Run'
```

⚠️ CẤM launch batch thứ 2 khi batch trước chưa exit (tự tranh lock, gây
`skipped-device-locked` hàng loạt vì chính batch của mình giữ lock).

## Root cause "46 máy k có VPN" = 2 tray cùng bật watcher (2026-08-14)

`blocked-vichanger-vpn` hàng loạt KHÔNG phải do Wi-Fi/ADB/vichanger app —
mà do **2 logon task cùng chạy `run-proxy-watcher.ps1`**: `GanProxyWatcherTray`
(proxy-watcher-only-tray.ps1) + `TikTokAllSchedulerTray`
(tiktok-scheduler-tray.ps1) → 2 watcher chain → 1 cái bị
`BLOCKED: watcher singleton is already held` → máy không bao giờ được
reconnect VPN sau reboot. Fix: patch
`D:\Taadaa\automation-core\src\automation_core\scheduler\tiktok-scheduler-tray.ps1`
set `$script:ProxyWatcherEnabled = $false` (GanProxyWatcherTray là chủ duy nhất
của watcher). Chi tiết: skill `android-proxy-watcher`.

**Sau khi user nói "watcher ổn định rồi" vẫn phải verify lại tại thời điểm
launch**: watcher có thể chết ngay sau đó (stale `watcher-singleton.lock` chặn
restart dù 0 process). Check `Get-CimInstance Win32_Process | Where-Object {
$_.CommandLine -match 'gan_proxy_fleet' }` + log stderr mới nhất không chứa
`BLOCKED: watcher singleton`. Nếu lock stale: kill tree, `rm` lock, start task
1 lần.

## Kết quả test 3 máy sau khi watcher sạch (2026-08-14)

Chạy `--machines 1,2,3 --max-workers 3`:
- m1, m2 → `success` (feed-session-smoke completed) — VPN OK sau watcher fix.
- m3 → cần đợi watcher reconnect tới máy đó (tun0 chưa lên lúc test). Watcher
  reconnect là INCREMENTAL per-machine — máy chưa có tun0 chỉ cần chờ, không
  phải chạy lại vội.

## Cơ chế lock mới: automation KHÔNG auto-lock (2026-08-14, Phase 4)

User chốt: "chỉ lock khi user ra lệnh lock" — bỏ auto-lock. `acquire_device_lock`
có kwarg `user_authorized` (mặc định True cho operator/CLI/contract; consumer
automation truyền `False`). Hành vi `user_authorized=False`:
- **KHÔNG có lock** → trả no-op `_UnlockedDeviceLockLease` (mọi lifecycle call
  release/finish/set_status no-op) — automation chạy KHÔNG lock, không tạo file.
- **CÓ lock (bất kỳ owner)** → raise `DeviceLockNeedsUserDecision` (kèm
  machine/serial/owner/caller_project) — KHÔNG tự release, KHÔNG skip câm.
Consumer (run_tiktok.py single + multi_machine_feed_session.py) catch exception
này TRƯỚC `DeviceLockUnavailable`, ghi `lock_pending_user_decision.json` +
final_status `needs-user-decision` → báo user quyết định release hay skip.
⚠️ LƯU Ý: `multi_machine_feed_session.py` chỗ `_reacquire_recovery_lock` (khoảng
line 847) vẫn dùng mặc định `user_authorized=True` — đó là reacquire lock ĐÃ có
(recovery path), không phải auto-lock, để nguyên.
Chi tiết implement + audit: skill `automation-core-development` Phase 4
(branch `codex/user-lock-gate`, wheel automation_core 0.4.45).

## KHÔNG tự chạy row 2 full khi user chưa yêu cầu

User: "k chạy row 2 full, đụ mẹ mày" — khi user xác nhận watcher OK, KHÔNG tự
launch full farm. Chỉ chạy theo lệnh rõ ràng. Test = vài máy (mục 3).

## Watcher singleton: chẩn đoán chuẩn (2026-08-14)

Khi nghi watcher chết/conflict, đừng đo bằng `Measure-Object | Select Count`
một mình — lệnh của Hermes qua bash có thể bị head/truncate làm ra vẻ "0
process" trong khi watcher vẫn sống (đã xảy ra, tưởng watcher chết nhưng thực
ra chain 38368→24568 vẫn chạy). Cách chuẩn:

```bash
powershell.exe -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "gan_proxy_fleet" } | Select-Object ProcessId,ParentProcessId,CreationDate | Format-List'
```

- 1 chain hợp lệ = 1 python (automation venv) + 1 con (Python312) cùng cmdline
  `watch --all --workers 80 ...`. Chain từ `GanProxyWatcherTray` OK.
- 2 chain riêng biệt (parent khác) = conflict → 1 bên bị
  `BLOCKED: watcher singleton is already held`.
- Singleton lock file RỖNG (`watcher-singleton.lock` 1 byte, không pid) vẫn chặn
  restart → kill toàn bộ chain, `rm` lock, start task 1 lần.
- `adb devices` serial hiện `ce12160c...` thay vì `9885...` (đúng theo
  workbook) = ADB server bẩn/tranh chấp → `adb kill-server && start-server` rồi
  đợi serial chuẩn.

## Khi user ra lệnh "dừng hết lại, kiểm tra cơ chế" (2026-08-14)

User yêu cầu dừng + kiểm tra toàn bộ script automation: KHÔNG chạy gì thêm,
chỉ inventory. Liệt kê process thật đang chạy (không phải process cũ của
Hermes): `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match
"Taadaa|gan_proxy|tiktok|scheduler|proxy|run_tiktok|run-proxy" }`. Phân biệt:
scheduler thật (`python -m scheduler --live`), tray (scheduler-tray.ps1 /
tiktok-scheduler-tray.ps1), watcher (gan_proxy_fleet), recovery watch. Chú ý
`scheduler-task.log` 0 byte từ nhiều ngày = scheduler "Running giả" (process
sống nhưng không ghi log, không dispatch) — không tin trạng thái task, tin log
mtime + process cmdline.

## Worker checkpoint / terminate discipline (AGENTS.md)

- Không kết luận "worker chết" từ stdout đứng yên / exit code −15; chỉ
  terminate khi fatal/quota rõ ràng, hoặc ≥3 quan sát cách ≥30s chứng minh
  output/checkpoint/mtime/process tree không tiến triển.
- Trước khi terminate: lưu đầu/cuối log, process tree, mtime, `git status`,
  `git diff`; nếu worker có thể đã ghi code → hậu kiểm diff/test độc lập.
- Kill/exit bất thường phân loại WORKER_TERMINATED_EXTERNALLY /
  WORKER_EXITED_WITHOUT_REPORT; không rollback mù, không chạy worker thay thế
  chồng; reconcile scope + verifier độc lập trước khi replacement/commit.
- Trong phiên này: launch batch row 2 nhiều lần KHÔNG kill batch cũ → 2 batch
  của chính mình tự tranh lock (75 skip "device lock active pid=<batch cũ>")
  — CẤM launch batch mới khi batch trước chưa exit hẳn.
