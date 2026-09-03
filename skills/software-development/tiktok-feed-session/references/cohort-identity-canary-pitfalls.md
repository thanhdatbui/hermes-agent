# Cohort Identity Canary Pitfalls — feed-session

Áp dụng cho `multi_machine_feed_session.py::_apply_cohort_identity` + runner `scripts/run-feed-session.ps1`.

## 1. Thứ tự fail-closed trong `_apply_cohort_identity`
- Chỉ cần 1 trong 4 key xuất hiện (`_cohort_artifact`, `_assignment_manifest`, `_worker_id`, `_cohort_bound_live`) là `cohort_bound=True`.
- Nếu `cohort_bound` mà thiếu `artifact` hoặc `assignment_path` → lỗi ngay:
  `cohort artifact and assignment manifest are both required for a live cohort child`
- Lỗi này xảy ra TRƯỚC so sánh `expected_username` / `target.account` / `tik`.
- Hệ quả: alert gốc `cohort target identity mismatch: expected_username` có thể bị che bởi lỗi `both required` khi canary không truyền đủ 2 input frozen.

## 2. Canary máy đơn vẫn bị gate cohort
- `run-feed-session.ps1 -Machines 1` (không `-LocalRun`) tự gắn `--assignment-manifest` + `--worker-id` từ env `TIKTOK_FEED_ASSIGNMENT_MANIFEST` / `TIKTOK_FEED_WORKER_ID`.
- Khi đó `_apply_cohort_identity` bắt buộc phải có thêm `--cohort-artifact` (env `TIKTOK_FEED_COHORT_ARTIFACT`).
- Không có artifact → `final_status=failed`, `blocker_type=cohort-target-mismatch`, `swipes_completed=0`, chưa chạm device/VPN/proxy.
- Muốn nuôi tiếp: hoặc cấp cohort artifact frozen khớp workbook Row, hoặc chạy `-LocalRun` để bypass gate assignment/cohort.

## 3. Hiện trường thường gặp
- `inspect_machine.py 1` hiện chỉ là stub (in `adb devices`), không cho screen/log/step. Bắt buộc đối chiếu ADB trực tiếp + `.ai-runs/<run_id>/summary.txt` + `log.jsonl` + `machines/machine_<N>/`.
- Không có symlink `.ai-runs/latest`. Lấy run mới nhất bằng `ls -t .ai-runs/`.
- `search_files` (rg) fail IO error với path có dấu cách (`tiktok-luot nuoi acc`). Fallback: `python -c 'open(...)'` qua terminal để đọc/grep.
- Lock `machine_N.lock.json` `status=blocked, owner_active=false` vẫn chặn spawn; canary mới sẽ takeover lock cũ.

## 4. Checklist debug mismatch
1. Xác nhận env: `TIKTOK_FEED_COHORT_ARTIFACT` có tồn tại không, digest có khớp assignment manifest không.
2. Đọc `.ai-runs/<newest>/summary.txt` → xem `stop_reason` là `both required` (thiếu input) hay `expected_username` / `target.account` / `tik` thật.
3. Nếu là `expected_username`: so workbook `taikhoan_run_safe.xlsx` Row N vs cohort `entries_by_machine[N].account` (strip `@`, so sánh case-sensitive sau strip).
4. Không sửa `automation-core`; chỉ sửa `python_runner/*` theo allowlist repo.

## 5. Case 20260903 M74 — alert UI bị che bởi gate cohort toàn batch
- Alert báo `ui_dump_error: ATX_SESSION_UNAVAILABLE` (serial `ce061606c21e153d03`) nhưng canary `run-feed-session.ps1 -Machines 74 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run` fail ngay tại `_apply_cohort_identity` với `both required`, `swipes_completed=0`, chưa chạm device/UI. Lỗi UI gốc không tái hiện được.
- Nguyên nhân: lệnh canary trong alert không truyền `--cohort-artifact` và env `TIKTOK_FEED_COHORT_ARTIFACT` trống, trong khi ps1 vẫn tự gắn `--assignment-manifest + --worker-id` từ env → `cohort_bound=True` → fail-closed. Lệnh canary alert đưa ra mặc định là thiếu input cho mọi máy non-LocalRun.
- Batch `20260903-195710` cùng lúc fail diện rộng: 34 `cohort-target-mismatch` + 40 `skipped-device-locked`, 0 swipes — đây là lỗi gate, không phải 34 máy cùng lỗi UI.
- File flow alert chỉ (`feed_swipe_smoke.py`) là sai chỗ cho blocker này; gate nằm ở `python_runner/flows/multi_machine_feed_session.py::_apply_cohort_identity`. Đọc `summary.txt` → `stop_reason=both required` là đủ kết luận, không cần mở `feed_swipe_smoke.py` (21k dòng).
- Serial trong log runner bị redact (`device:67041b72f9`) khác serial thật trong alert; đối chiếu máy phải qua `machines/machine_74/` + `adb devices`, không so chuỗi serial trong summary.
