# DEFERRED_LOCKED handoff-evidence gate + stale lock reaper (2026-08-13)

Tình huống: bật lại schedule TikTok + chạy row 2 toàn farm (80 máy) → hàng loạt
`skipped-device-locked` dù đã dọn hết lock file. Root cause thật có HAI lớp.

## Lớp 1 — stale device-lock (đã biết, nay có reaper chuẩn)

- Lock store: `C:\Users\Kibe\.codex\device-locks\` — file `machine_<N>.lock.json` +
  `serial_<serial>.lock.json` (PHẢI dọn cả 2 alias).
- Lock cũ (chủ đã chết) để lại từ lúc user tắt schedule → mọi lượt chạy sau bị
  block câm, batch vẫn báo exit 0 "completed" dù 64/80 máy skip.
- **Phân loại liveness ĐÚNG**: không tin field `owner_active` (dễ stale, ghi True
  dù pid chết). Dùng `automation_core.device_lock.owner_process_alive(owner)` —
  check PID Windows + đối chiếu `process_started_at` (chống reused-PID). Đây là
  cùng hàm contract lock dùng để quyết định takeover.
- **Reaper chuẩn** `scripts/reap-dead-owner-locks.py` (repo tiktok-luot nuoi acc):
  duyệt lock file m1-80, `owner_process_alive() is False` → **MOVE sang quarantine**
  `~/.codex/device-locks-reaped/<ts>/` (không xóa — phục hồi được), in danh sách.
  Idempotent (chạy lại an toàn). Cron Hermes `reap-dead-owner-locks` (mỗi 30p,
  deliver local/im lặng khi sạch) để không tái diễn mỗi lần dừng automation.
- Kết quả lượt này: 155 + 72 + 130 dead-owner locks được dọn qua nhiều đợt
  (mỗi đợt batch chết lại để orphan mới → RE-RUN reaper sau mỗi batch kill).

## Lớp 2 — DEFERRED_LOCKED handoff-evidence gate (MỚI, dọn lock KHÔNG đủ)

- `python_runner/flows/multi_machine_feed_session.py`:
  - `_prior_target_evidence()`: `root.rglob("recovery_lock_handoff.json")` quét
    TOÀN BỘ artifact root (`.ai-runs`) — KHÔNG quan tâm tuổi/run đã chết, chỉ bỏ
    qua file thuộc chính current run.
  - `_classify_prior_handoff()`: payload khớp `schema == "tiktok-consumer-lock-handoff-v1"`
    + identity match máy → nếu `_verifier_success_proof()` False → `deferred-locked`
    → máy bị `skipped-device-locked` với
    `stop_reason: DEFERRED_LOCKED: prior target handoff/non-success or incomplete release proof; evidence=<path>`.
  - `_verifier_success_proof()` cần ĐỦ: `finish_succeeded is True`, `handoff_required is False`,
    `final_status == success`, `expected_terminal_status == released`, lock release proof
    cho cả 2 alias, run_manifest `final_status == success`, `total_swipes_completed > 0`.
  - => **Handoff evidence cũ fail (finish_succeeded=false) = chặn VĨNH VIỄN tới khi dọn**,
    kể cả khi lock file đã sạch. Fail-closed cố ý (an toàn) — không phải bug, là thiết kế.
- **Dọn đúng**: `scripts/reap-stale-handoff-evidence.py` — move mọi
  `recovery_lock_handoff.json` có `finish_succeeded is not True` sang
  `~/.codex/lock-evidence-reaped/<ts>/` (giữ cấu trúc thư mục). File unparsable +
  verified-success GIỮ NGUYÊN. Lượt này: 579 tổng → 300 moved (stale), 279 kept
  (verified-success = vô hại, không chặn).
- Sau khi dọn cả 2 lớp mới chạy lại được. Trước khi rerun: re-run reaper lock
  (batch trước kill để orphan mới) + reap handoff mới sinh.

## Env checklist trước khi launch feed batch từ Hermes terminal

1. `$env:PYTHONPATH=""` (PowerShell prefix) — Hermes export PYTHONPATH trỏ
   hermes-agent venv (Py3.11) → shadow automation venv (Py3.12) → PIL
   `cannot import name '_imaging'` (ABI cp311 vs cp312). Khi chạy
   `run-feed-session.ps1` phải bọc: `powershell -Command '$env:PYTHONPATH=""; & <script> ...'`.
2. automation venv PHẢI có `automation_core.escalation` (run_tiktok import).
   Repo pin `requirements-automation-core.txt` = wheel 0.4.45 tại
   `C:\Users\Kibe\p1-venv-wheels-20260812\automation_core-0.4.45-py3-none-any.whl`.
   Venv cài 0.4.43 (thiếu escalation) → `pip install --force-reinstall --no-deps <wheel>`
   (pip có thể báo 0.4.44 do metadata lệch — miễn có escalation là được).
   Verify: `import automation_core.escalation` + `import run_tiktok` dưới venv đó.
3. `--full-scope-takeover` CHỈ reclaim ~7/80 máy với orphan lock đủ điều kiện —
   KHÔNG phải cách dọn; dùng reaper + handoff reaper rồi chạy PLAIN.

## Schedule re-enable pitfalls (TikTokScheduler)

- Task action BAKE env paths lúc register — task cũ trỏ path sai
  (`D:\OneDrive\Tiktok_Reg\...`, `...\data\taikhoan_run_safe.xlsx`) → phải
  RE-REGISTER `scripts/register-scheduler-task.ps1` (chạy `-DryRun` trước) để
  refresh path đúng, không chỉ `Enable-ScheduledTask`.
- **State=Running ≠ worker sống**: check `runs/scheduler-task.log` size (0 byte =
  không output) + scan process `python -m scheduler` qua
  `Get-CimInstance Win32_Process` trước khi kết luận schedule đang chạy.
- Bật lại schedule lúc env đang hỏng (PIL/automation_core chưa fix) → worker chết
  ngay lúc khởi động, task nằm trạng thái "Running" giả. Luôn fix env TRƯỚC, bật
  schedule SAU.

## Chẩn đoán skip-lock — thứ tự (user correction 2026-08-13)

User phản ứng gay gắt khi tôi đổ lỗi schedule/scheduler mà không verify
("Lq cặc gì schedule đã đến h chạy đâu mắc gì lock"). Thứ tự đúng:
1. Scan lock store m1-80 bằng `owner_process_alive` → tách: dead-owner (stale →
   reap) vs alive-owner (competitor THẬT — respect lock, KHÔNG dọn: có thể là
   social_reg_v1, tiktok-upload, tiktok-follow, hoặc CHÍNH batch feed khác).
2. Nếu lock sạch mà vẫn `skipped-device-locked` → đọc `stop_reason` trong
   summary.txt: chứa "prior target handoff" = gate handoff-evidence (Lớp 2).
3. Chỉ kết luận nguyên nhân sau khi có evidence từ cả 2 lớp + process scan.
4. Batch có thể tự-conflict: worker fail/treo không release lock → lần dispatch
   sau trong CÙNG batch thấy lock do chính pid mình giữ → skip. Đừng panic,
   reaper sau batch chết sẽ dọn.
