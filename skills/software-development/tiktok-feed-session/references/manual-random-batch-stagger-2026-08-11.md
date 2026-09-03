# Manual random batch + stagger phút — session 2026-08-11 (evidence)

User: "chạy lướt all máy worker 15 ngẫu nhiên stagger = 5ph đi" → "trừ máy 74 ra" → "t nói nhầm r, stagging 1ph thôi".

## Timeline

- 06:17 — preflight: 80/80 online, lock store 18 lock (PID chết hết), `tiktok_workflow --machine 74` đang chạy (2 python procs) → máy 74 bận thật (user biết, loại khỏi pool).
- Pool: 80 máy từ `data/taikhoan_run_safe.xlsx` (sheet `Accounts`, 481 rows = 80 máy × 6 slot acc), `random.sample(pool,15)` → 1,5,18,21,25,28,31,35,36,40,51,56,57,62,78.
- Dọn lock chết của máy chọn (backup `Temp\lock-backup-20260811-0618`): M28/40/57 — `blocked` + 1 `running owner_active=True` nhưng PID 63420/76484 chết (tasklist verify) → xóa CẢ `machine_N` + `serial_N`.
- 06:19 launch batch A: stagger `300000,300000` (5ph), background, preflight pass (`navigation-only taps enabled`...).
- 06:24 user: stagger 1ph → kill process, dọn 30 lock reservation (15 machine + 15 serial, status `queued_v2`/`running`, pid 29688 chết), backup `Temp\lock-backup-20260811-0631`.
- 06:31 relaunch batch B: `--machine-start-stagger-ms 60000,60000` → exit 2 lúc 07:08 (38 phút — 14 phút ramp + session).
- 07:08 kết quả: 12 success (19–30 swipes), M5/78 `blocked-vichanger-vpn` (swipes=0), M62 `manual-needed` (25 swipes rồi `ADB_TRANSPORT_LOST_AFTER_VERIFIED_PERSISTENT_CAPTURE`). Tổng 320/450.
- 3-bước fix M5/62/78 (B1 ATX-kill + B2 force-stop + B3 reboot; warning `reboot unable to open /sys/class/sec/sec_debug/recovery_cause` vô hại).
- Sau reboot: `sys.boot_completed`=1 + focus LauncherActivity. Loop dump `exec-out cat | wc -c` trả 0 ×3 (cả 3 máy). B1 ATX-kill → vẫn 0. Chạy dump KHÔNG redirect → `UI hierchary dumped to: /sdcard/check.xml`, `ls -la` = 31408 bytes → máy OK (boot-race/redirect nuốt lỗi). Relaunch M5,62,78 → pass preflight.

## Lock states quan sát được

- Sau kill batch: toàn bộ máy trong batch có lock `queued_v2` (hoặc `running` nếu đã start), `owner_active=True`, `pid` = PID fan-out đã chết. Reservation ghi cho CẢ batch ngay khi queue — kill 1 process để lại 2×N lock file.
- Lock cũ hôm trước (không thuộc batch): `blocked`/`handoff`/`running` `owner_active=True` PID chết — `owner_active` KHÔNG phải ground truth, tasklist mới là ground truth.

## Manifest exit 2

`run_manifest.json` keys: run_id, device_id, account, mode, start/end_time, final_status, message, stop_reason, completed_steps, paths, event_counts, artifact_index, **multi_machine_summary** (LIST), **blocker_taxonomy_summary** (LIST), requested min/max videos, total_swipes_requested/completed.

Không có key `machines`. Per-machine dict: machine, account_row, serial, expected_username, account_source, source_sheet, source_row, final_status, swipes_completed, blocker_type, artifact_root, stop_reason.

`blocker_taxonomy_summary` sample: `[{"category": "pass/degraded acceptable", "count": 12, "machines": "1,18,21,...", "final_statuses": "success"}, {"category": "manual-needed popup", ...}]`.

`summary.txt`: key-value text — status `manual-needed`, message `multi-machine-feed-session completed with machine-specific manual review`, event_counts.

## Ghi chú lệnh

- `--machine-start-stagger-ms min,max`: parse `min,max` positive ints. delay list = [0, randint(min,max), ...] (per-machine, mỗi máy 1 khoảng riêng); loop chính sleep rồi submit tuần tự → min==max = cách đều đúng N phút; min<max = jitter ngẫu nhiên không cumulative.
- Heredoc python với tool bash có thể bị từ chối bởi heuristic '&' backgrounding → viết script vào `C:\Users\Kibe\AppData\Local\Temp\` rồi `PYTHONPATH= python <path>` (2 lần dính trong session này).