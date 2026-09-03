# Batch upload launcher workflow (run_tiktok_upload_batch.ps1)

Full-farm "đăng video tất cả máy" dùng cùng canonical launcher cho Tik1/Tik2/TikN; chỉ workbook/data thay đổi qua tham số. Lessons from the 2026-08-08 79-máy batch, 46-máy retry, và correction Tik2 ngày 2026-08-12.

## Launch preflight (bắt buộc trước mỗi batch)

1. **`unset PYTHONPATH`** trước khi gọi launcher qua bash→PowerShell. MSYS path
   (vd `/d/Taadaa/...`) lọt vào env làm launcher nhặt nhầm dist-info từ
   `hermes-agent\venv\Lib\site-packages` (automation_core 0.4.43) thay vì
   `venv-core024` (0.4.40) → chết ngay với lỗi:
   `automation-core version mismatch: expected=0.4.40; actual=0.4.43; ...
   reason=metadata version did not match expected contract` (throw ở dòng ~91
   của ps1). Đây là DẤU HIỆU PYTHONPATH dơ, KHÔNG phải venv hỏng — đừng
   downgrade/upgrade core vội. One-liner chuẩn chạy được ngay (linux env
   command, 1 dòng bash):
   `env -u PYTHONPATH powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./run_tiktok_upload_batch.ps1 -Tik 1 -MaxParallel 30 -Confirmation RUN`
   Check nhanh trước: `env -u PYTHONPATH <venv-core024>/Scripts/python.exe -c "import importlib.metadata as m; print(m.version('automation-core'))"`
   (`unset` bash không dùng được trong pipeline 1 dòng qua tool; `env -u` là
   dạng tương đương an toàn).
2. Kiểm tra `automation-core` version pin khớp: launcher expect `0.4.40`
   (mặc định; override qua `TIKTOK_VIDEO_AUTOMATION_CORE_VERSION`).
3. Chạy inventory trước khi launch (read-only):
   `PYTHONPATH='D:\Taadaa\Tiktok-video\scripts' venv-core024\Scripts\python.exe -m tiktok_workflow.machine_inventory --workbook "D:\OneDrive\Tiktok\Tik1.xlsx"` —
   xem `eligible` / `skipped` (SKIPPED_LOCKED = có lock file).
4. Verify manifest trước launch:
   `AssignmentManifest.load(path); m.assert_owner(worker_id)` + đếm resources +
   check không có máy bị loại (vd `machine:34`).

## Lock cleanup (máy bị SKIPPED_LOCKED)

- Lock root: `C:\Users\Kibe\.codex\device-locks\` — `machine_*.lock.json` +
  `serial_*.lock.json`.
- Lock nào PID đã chết (`tasklist /FI "PID eq N"` / `wmic`) là stale → chặn
  inventory. Dọn theo quy trình: **backup toàn bộ vào `backup_takeover_<ts>\` +
  evidence JSON** (`schema: tiktok-video-stale-lock-cleanup-v2`), rồi xóa.
- Script chuẩn: `D:\Taadaa\Tiktok-video\scripts\lock_cleanup_stale.py`
  (fail-closed: pid sống của consumer khác → KEEP; `KEEP_MACHINE` cho máy loại
  khỏi batch; override feed pid khi operator authorize).
- Máy đang được consumer khác xử lý (vd máy 34 = `Tiktok_Reg` recovery) →
  **KHÔNG xóa lock**, loại khỏi manifest.
- Lưu ý: lock máy 34 (`machine_34.lock.json`, project `Tiktok_Reg/social_reg_v1.py`,
  status `blocked`) có thể ghi `owner_active: false` nhưng vẫn KHÔNG được coi là
  stale — Tiktok_Reg đang recovery (attempt 2), lock giữ `handoff`. Chỉ dọn
  stale khi PID đã chết (`tasklist /FI "PID eq N"`) VÀ project không phải
  consumer đang chạy. Rule: máy 34 luôn loại khỏi manifest batch upload.

## Feed-session race (nguyên nhân SKIPPED_LOCKED hàng loạt)

- `tiktok-luot nuoi acc` scheduler chạy live (`python_runner\run_tiktok.py
  --mode multi-machine-feed-session --machines 1..74`) sẽ acquire lock máy bất
  kỳ lúc nào → batch upload bị `SKIPPED_LOCKED` (exit 3) hoặc
  `DEVICE_LOCK_FAILED` giữa chừng. KHÔNG stale — process thật.
- Trước batch lớn: check `wmic process where "name='python.exe'" get
  ProcessId,CommandLine` + `psutil`/PowerShell `Get-Process` cho PID khả nghi.
  `tasklist //FI` qua bash MSYS bị hỏng tham số (`//FI` → dùng `//FI` đúng
  MSYS hoặc PowerShell `Get-Process`).
- Khi operator xác nhận feed "chưa đến lịch" và authorize: kill feed PID
  (PowerShell `Stop-Process -Id N -Force`; `taskkill //F //PID N` trong bash
  MSYS bị lỗi arg — dùng PowerShell), chạy lại lock cleanup với override pid,
  rồi launch.

## Launch & retry pattern

- **Canonical launcher rule (user correction 2026-08-12):** Tik1/Tik2/TikN phải dùng CHUNG `run_tiktok_upload_batch.ps1`; chỉ workbook/data TikN thay đổi. Không tạo launcher live riêng trong `runs/` hoặc ghép `xargs/bash -lc` để chạy từng worker. Nếu canonical launcher đang hardcode path cũ hoặc chưa hỗ trợ workbook farm hiện tại, sửa/build chính canonical launcher, test preflight TikN, audit/verify rồi mới chạy live.
- **Không nhầm approval shell với quyền vận hành:** yêu cầu trực tiếp kiểu “chạy upload Tik2” đã là business authorization cho live upload đúng scope; đừng hỏi xác nhận lần hai chỉ vì một command phức tạp bị Hermes smart-approval timeout. Ngay từ đầu gọi canonical PowerShell launcher bằng command shape ngắn/rõ như Tik1. Không dùng `xargs`/`bash -lc`/pipe `YES` rồi tìm cách bypass approval; nếu tool chặn thì dừng command đó, giải thích ngắn, và chỉ tiếp tục sau steering mới của user.
- **Kiểm tra account thật trước media:** preflight chỉ kiểm tra workbook/device/video/lock. Live flow phải lấy `ID TikTok` từ workbook TikN, exact-verify Profile bằng `verify_selected_account`, nếu sai thì `select_exact_account`, rồi exact-verify lại tại `ACCOUNT_READY`; mismatch/missing phải fail-closed trước khi chạm media/Post. Khi user hỏi “script có check đúng acc không”, trả lời rõ hai tầng preflight vs live và nêu gate này.
- Launch: `powershell -NoProfile -ExecutionPolicy Bypass -File
  run_tiktok_upload_batch.ps1 -Tik 1 -MaxParallel 10 -AssignmentManifest
  <manifest> -WorkerId <id> -Confirmation RUN` — background +
  `notify_on_complete=true` (batch 79 máy ~2-3h).
- Manifest mới mỗi retry (assignment_id/owner_id khác). Máy retry =
  `1..80 trừ máy OK từ batch trước trừ máy loại trừ`; loại tiếp máy thiếu data
  bắt buộc (vd thiếu `ID TikTok` → lỗi `Missing required fields: ID TikTok`,
  không retry được tới khi điền workbook).
- Batch dir: `D:\CodexRuntime\tiktok-video\batch-runs\batch_tik1_<machines>_<ts>\`
  — `summary.csv` + `machine-<N>.out.log`; report:
  `D:\CodexRuntime\tiktok-video\runs\run_<id>\report.json`.
- Exit codes: `0`=verified success (đối chiếu `post_verified=true`), `2`=
  worker exit 0 nhưng thiếu report/verifier → MANUAL_REVIEW, `3`=SKIP
  (SKIPPED_LOCKED/assignment). MANUAL_REVIEW giữ lock `handoff` theo contract;
  không tự retry lần 3 cùng signature.
- Sau batch: phân loại máy ERR theo report `status`; máy `MANUAL_REVIEW`/
  `FAILED` cần recovery handler riêng (không launch mù). Máy thiếu ID TikTok
  (75,77-80) báo user cần điền workbook.
