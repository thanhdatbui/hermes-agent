# Cohort target identity mismatch: expected_username — stale-manifest recipe

Alert thật có dạng (từ `python_runner/flows/multi_machine_feed_session.py`
`_verify_cohort_binding`, ~L832-889):

`[cohort-identity] machine <N> cohort target mismatch:
cohort target identity mismatch: expected_username`
(blocker_type=`cohort-target-mismatch` trong `run_manifest.json` /
`summary.txt`).

Fail-closed này SO SÁNH `expected["account"]` trong cohort artifact đông cứng
(`cron-state/cohorts/<day>/<cohort-id>.json` → `entries_by_machine["<N>"]`)
với `expected_username` đọc từ safe workbook hiện tại. Lệch = drift giữa
kế hoạch ngày và dữ liệu nguồn, KHÔNG phải bug picker/runner.

## Root-cause class (case 2026-09-03 Máy 1)

1. Picker chốt manifest lúc 06:00 (`generated_at` trong
   `manifests/<day>/assignment-*.json`) từ `hermes_cron_source_config.json`
   có mtime CŨ HƠN lần sửa DAT (swap M1↔M6 tối 01/09, backup
   `taikhoan_dat_v2_updated .xlsx.bak_swap_m1_m6_20260901_214926.xlsx`).
2. Source config cũ: M1 Row 5 = `janayerton71` (DAT trước swap có 7 ID/M1,
   config chỉ chứa 6 slot → `buithudung2011` bị loại).
3. Sau swap, cron `hermes_taikhoan_sync_cron` re-sync safe workbook theo DAT
   mới (`runtime/taikhoan-sync-state.json` → `last_sync`): M1 Row 5 hiện là
   `buithudung2011`, `janayerton71` chuyển sang M61.
4. Cohort ca tối (block 3, slot 18:35, vd `cohort-v1-6e59622f...`) vẫn giữ
   M1 Row 5 = `janayerton71` → runner đọc safe mới lấy `buithudung2011` →
   verify fail → watchdog alert.

## Điều tra (thứ tự rẻ → đắt)

1. `manifests/<day>/ACTIVE.json` → manifest path; mở manifest, lọc
   `entries` theo `machine==N` (account_row/account/slot_time/session_index)
   và `blocks` theo `block_index`.
2. Mở cohort đúng ca (`started_at` chứa slot giờ alert):
   `entries_by_machine["<N>"]` → account/account_row/session_index.
3. `hermes_cron_source_config.json`: lọc `feed_source.accounts` theo
   `machine==N` (Row→ID hiện tại trong config).
4. DAT hiện tại (`taikhoan_dat_v2_updated .xlsx`, col 0=Máy, col 2=ID,
   col 9=device ID) + bản `.bak_swap_*` trước thao tác swap → so M1/M6/M61.
5. Safe workbook hiện tại + bản `.bak-*`: M1 Row 5 là ai.
6. `runtime/taikhoan-sync-state.json` (`last_sync`) + mtime source config vs
   `generated_at` manifest → chứng minh stale.
7. Code verify: `multi_machine_feed_session.py` L841-842 + L872
   (`expected_username` / `target.account`).
8. Bỏ qua: run `.ai-runs/*` smoke test thủ công với ID che
   (`account:xxx`, `serial device:xxx`, thiếu artifact) — không phải alert thật.
   `feed_state.json` không quyết định Row (chỉ due/progress).

## Fix direction

- Không sửa code picker/runner (fail-closed đúng thiết kế).
- Regenerate `hermes_cron_source_config.json` từ DAT/safe hiện tại rồi cho
  picker re-pick / force-regenerate manifest ngày (hoặc sang ngày mới), sao cho
  Row 5 M1 trong config = `buithudung2011` trước giờ chạy ca tối.

## Tool pitfalls gặp trong session

- `openpyxl.load_workbook` KHÔNG mở được file đuôi `.bak-...`: copy sang tên
  có đuôi `.xlsx` trong cwd rồi mới đọc (vd `cp "...bak-20260902_130806"
  ./safe1.xlsx`).
- `grep -rn` toàn `python_runner/` quét cả `.ai-runs/` → timeout 900s.
  Scope hẹp: `python_runner/hermes_cron/` + `python_runner/flows/
  multi_machine_feed_session.py`.
- Header DAT: `['Máy','Folder Video','ID',...,'device ID',None]` — đọc M1 bằng
  index cột (0=Máy, 2=ID, 9=serial), không dò tên cột `machine`.
