# Live-wiring Hermes cron staging — session detail 2026-08-16

## Bối cảnh
- Repo: `D:\Taadaa\tiktok-luot nuoi acc`, master HEAD `2012f9f`, Hermes v0.18.2.
- Việc: hoàn tất Phase 9B live wiring — stage 3 cron job picker/runner/watcher
  từ `scripts/hermes_cron_schedule.json` qua `python_runner/hermes_cron/staging.py`.
- Kết quả: 3 job `phase9-staging-*` đứng **paused** (transaction create→pause→edit→verify).
  Job IDs: picker `304211820b28`, runner `dfd2bd79114e`, watcher `34950f259909`.

## Chuỗi lỗi thực tế (4 lần fail, mỗi lần rollback sạch)

### Lần 1 — `reconcile found 0 candidates`
- Triệu chứng: `FinalBlocked: reconcile found 0 candidates for <txn_id>`.
- Vì `StagedJobSpec.script` = absolute path `C:\Users\...\hermes\scripts\tiktok_picker.py`
  → Hermes CLI từ chối: `Failed to create job: Script path must be relative to ~/.hermes/scripts/` (rc!=0)
  → nghĩ là tạo thất bại → nhưng thực ra job ĐÃ được tạo? Không — create stdout rỗng id,
  rollback chạy, journal ghi `ROLLED_BACK` → sạch. Bài học: **create stdout không có
  `Created job: <id>`** thì `parse_created_job_id` → None → reconcile tìm theo tên marker
  `phase9-staging-<name>-<txn_id>` không thấy → FinalBlocked (fail-closed đúng thiết kế).

### Lần 2 — `created schedule mismatch: {'kind':'once','run_at':'...','display':'...'}`
- Sau khi đổi script = filename: create THÀNH CÔNG nhưng `_job_matches_create`
  so `record.schedule != spec.create_schedule` — record schedule giờ là dict
  `{"kind":"once","run_at":"2026-08-17T18:47:56+00:00","display":"once at 2026-08-17 18:47"}`.
- Bài học: canonical adapter `cron.jobs.list_jobs` trả schedule dạng **dict**, doc cũ giả định string.
  Phải normalize. Lưu ý `display` = human text `'once at ...'` KHÔNG khớp ISO — ưu tiên `run_at`/`expr`.

### Lần 3 — `created schedule mismatch: 'once at 2026-08-17 18:49'`
- Sau khi normalize ưu tiên display → vẫn fail vì lấy `display` (human) thay vì `run_at` (ISO).
- Fix cuối: `_schedule_display()` ưu tiên `run_at` → `expr` → `display`.

### (bỏ) — bash gọi .ps1 đường dẫn có dấu cách
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/deploy_hermes_cron_wrappers.ps1` từ bash
  bị tách ở khoảng trắng → `A positional parameter cannot be found that accepts argument 'hermes_cron'`.
- `powershell -Command "& '...' -Param ..."` (literal-quoted) chạy được script nhưng script TỰ fail:
  `deploy_hermes_cron_wrappers.ps1:23` `Join-Path $RepoRoot 'scripts' 'hermes_cron'` → resolve thêm
  một lớp `scripts` → path không tồn tại → PS 5.1 Resolve-Path trên path không tồn tại ném.
  → **Workaround thủ công**: `cp scripts/hermes_cron/$f.py $LOCALAPPDATA/hermes/scripts/$f.py` + sha256sum
  source vs installed cho cả 3; smoke chạy wrapper không activation → rc=0 im lặng.

## Spec staging đúng (đã hoạt động)
- `StagedJobSpec(script=<filename>, create_schedule=now+26h ISO+tz, schedule=<5-field>, wrapper_sha256=hash(file installed), deliver="local", repeat=1, name_prefix=f"phase9-staging-{name}-")`.
- Chạy qua `/d/Taadaa/python-envs/automation/Scripts/python.exe -B runtime/stage_tiktok_jobs.py`
  (dùng staging machinery trực tiếp, không qua .ps1 — tránh bug path).
- Journal: `runtime/cron-staging/<name>.json`; trước mỗi lần chạy lại xóa journal cũ + đổi create_schedule.

## Trạng thái sau session
- 3 job paused, chưa resume (canary chưa chạy). `staging.py` đã sửa (`_schedule_display`) — **chưa commit**,
  cần chạy test `python_runner/tests/` + commit theo quy trình sau canary OK.
- `runtime/stage_tiktok_jobs.py` là file thủ công trong runtime/ (gitignore) — nếu cần tái sử dụng,
  chép từ `C:\Users\Kibe\AppData\Local\hermes\cache\terminal\stage_tiktok_jobs.py` hoặc viết lại ngắn.
- Windows TikTokScheduler đã restart (kill 2856/16692 → schtasks /run) → process mới 29772/33456,
  chạy sạch với automation_core 0.4.45 ở Python312 (đã cài) — nhưng hermes venv vẫn 0.4.43 (CÒN DỞ).