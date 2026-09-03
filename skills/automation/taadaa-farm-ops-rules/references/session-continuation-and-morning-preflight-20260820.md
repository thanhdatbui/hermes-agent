# Session Continuation ("Làm tiếp") & Morning Preflight — verified 20/08/2026

## Bối cảnh
User nhắn `Làm tiếp` vào ~03:52 sáng 20/08, không kèm ngữ cảnh, ngay sau một loạt
fix/review/commit 19/08 tối (3 repo). Việc "đang dở" thực ra đã xong ở phiên trước —
phiên này chỉ cần khôi phục ngữ cảnh + verify + preflight ca 06:00.

## Quy trình khôi phục ngữ cảnh (thứ tự)
1. `session_search(sort="newest")` (browse mode) → liệt kê session gần nhất.
   - Session Farm Alerts: `20260819_102526_c188a2dd` (Tiếp nhận thông báo lỗi máy)
   - Session điều hành: `20260818_222242_18ef2f6d` (Tắt schedule automation trên Windows)
2. Đọc bookend cuối mỗi session bằng `session_search(session_id=..., around_message_id=<id cuối>, window=6)`.
   - Xác định: user đã hướng dẫn gì cuối cùng, commit nào là cuối, còn việc gì dở.
   - Ở đây: chuỗi fix auto-recovery đã xong (review REJECTED → sửa 3 điểm → re-review
     APPROVED → push); việc còn lại chỉ là theo dõi ca sáng Row 2 (test chốt cơ chế mới).
3. Nếu session quá dài, scroll 1 lần ở giữa (window ±15) để đọc phần đang dở/đã chốt.

## Verify 3 repo (tất cả phải khớp commit cuối của session trước)
```bash
for r in "D:/Taadaa/automation-core" "D:/Taadaa/tiktok-luot nuoi acc" "D:/Taadaa/tiktok-follow"; do
  echo "=== $r ==="; cd "$r" && git status -s && git log --oneline -3
done
```
- Untracked bình thường KHÔNG phải việc dở: `.hermes/plans/*.md` (mọi repo),
  `docs/hermes-farm-alerts-contract.md` (automation-core), `HANDOFF_*.md` (tiktok-follow).
- 20/08: automation-core `6d0444b`, feed `ba9d0ef`, follow sync origin — sạch.

## Preflight ca sáng 06:00 (danh sách kiểm tra)
```bash
# 1. Devices
"C:/Program Files (x86)/xiaowei/tools/adb.exe" devices | grep -c 'device$'   # = 80
# 2. Locks — không được có machine_<N>.lock.json
ls "C:/Users/Kibe/.codex/device-locks/" | grep -i machine | grep -v backup
# 3. Cron health
cronjob list   # 10 jobs, last_status: ok
# 4. follow_state per-nick — nick nào dính hôm nay
grep -l '"follow_failed": true' "D:/Taadaa/tiktok-follow/runs/state/"*.json
ls "D:/Taadaa/tiktok-follow/runs/state/" | grep row_2   # Row 2 hôm nay phải sạch
# 5. LANES đúng ngày
grep -n "LANES\|JITTER" "D:/Taadaa/tiktok-luot nuoi acc/python_runner/hermes_cron/blocks.py"
#    LANES = (("A", (2,4,2)), ("B", (1,3,1))) ; ngày CHẴN = Lane A = Row 2/4/6
# 6. Picker scheduled
cronjob list | grep picker   # next_run_at 06:00
```

## PITFALL #1 — report.jsonl stale (đã vấp 20/08)
`D:\Taadaa\runtime\kibe\cron-state\report.jsonl` tail ra hàng loạt
`FAILED_LOCKED FEED_FAIL FEED_WATCH` m-4..m-74 → mới đọc tưởng farm đang chết loạt.
Sự thật: **file mtime 18/08 15:05 — entry cũ 2 ngày, hoàn toàn vô hại**.
- Luôn `ls -l --time-style='+%Y-%m-%d %H:%M:%S'` file TRƯỚC khi tin nội dung.
- Nguồn alert thật: `~/AppData/Local/hermes/cron/output/<job_id>/` (file mtime mới)
  hoặc nhóm Farm Alerts Telegram.
- Entry này cũng không có key `ts` — parse theo `ts` sẽ ra `?` (dấu hiệu phụ).

## PITFALL #2 — follow_state file cũ (không hậu tố _row_)
`follow_state_9.json` (1773B) bên cạnh `follow_state_9_row_1.json` = di sản migration
trước khi có per-nick cooldown (19/08). Đừng đọc nhầm là state hiện hành; chỉ tin
file dạng `follow_state_<m>_row_<r>.json`. File không `_row_` có mtime mới (02:50)
do script cũ vẫn ghi — vô hại.

## PITFALL #3 — cron output silent ≠ lỗi
`no_agent` jobs (taikhoan-run-safe-sync, sync-hermes-skills, tik4-render-watchdog,
phase9-runner...) ghi `Status: silent (empty output)` khi không có gì cần báo —
đó là trạng thái HEALTHY (silent watchdog). Chỉ để ý khi có output/error.

## Kết quả 20/08 (mẫu báo cáo chuẩn)
- 80/80 devices, 0 lock, 10 cron ok (runner 03:47, watcher 03:52).
- follow_state: duy nhất `follow_state_28_row_1.json` dính follow_failed ngày 20/08
  (do test tối 19/08 03:15) — KHÔNG ảnh hưởng ca sáng vì ngày chẵn chạy Row 2.
- Lane A (Row 2) đúng ngày chẵn; picker scheduled 06:00.
- Kết luận: không có việc dở, chờ 06:00 picker kích hoạt rồi theo dõi mẻ đầu.
