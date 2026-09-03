# Row machine-count variance + device-lock overlap (2026-09-03)

Ca toi Row 5 bao 66 may trong khi Row 1 du 80 may la BINH THUONG - do assignment manifest
chi gan block cho may con du dieu kien o workbook, khong phai loi rot may.

## Fact

- Manifest D:/Taadaa/runtime/kibe/cron-state/manifests/2026-09-03/assignment-*.json:
  blocks per account_row: {1: 80, 3: 74, 5: 66} (ngay 2026-09-03).
- Row 5 = 66 may: 1,2,3,4,5,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,
  27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,
  54,55,56,57,58,60,63,65,66,67,68,70,74,76.
- 14 may KHONG co block Row 5: 6,59,61,62,64,69,71,72,73,75,77,78,79,80.
- Row 3 log thuc te (runtime/kibe/live/2026-09-03/row-3-153015/log.jsonl):
  74 requested/completed = 68 success + 4 blocked-vichanger-vpn (30,41,64,65 mat WiFi)
  + 2 manual-needed (7,33).

## Verify (dem block theo row, khong doan)

Dem blocks per account_row trong assignment manifest bang Counter truoc khi ket luan
rot may. Row 5 thieu may so voi Row 1/Row 3 la binh thuong.

## Pitfall 1 - f-string backslash trong python -c (Windows)

r.split(":")[1] dat TRONG f-string expression gay
SyntaxError: f-string expression part cannot include a backslash (2 lan trong session).
Fix: tach bien trung gian truoc khi f-string, vi du gan parts = [...] truoc
roi moi print(sorted(parts)).

## Pitfall 2 - 2 run Row 5 chong nhau gay skipped-device-locked

- row-5-184555 va row-5-193008 cung chay toi 2026-09-03.
- Run sau log skipped-device-locked cho may da bi run truoc giu lock
  (vd may 1/4/56).
- Lock files: C:/Users/Kibe/.codex/device-locks/machine_*.lock.json
  (moi file co pid, started_at); PID con song kiem bang ps -W / tasklist.
- Khi watchdog bao so may thap bat thuong, check log run co dong
  skipped-device-locked truoc khi ket luan rot may.

## Alert dedup (chong spam Telegram)

- _claim_machine_alert_once giu 1 alert / 1 may / 1 ca tai
  runtime/kibe/live/alert-claims/<date>-row<N>/machine_<M>.claimed
  (status=delivered vs in_flight).
- May mat WiFi tu dau ca (64/65) chi ban 1 lan; trigger sau cung ca khong gui lai.
- Anh alert: runtime/kibe/artifacts/alert_machine_<M>.png.
