# Retry batch sau lần chạy all-máy (2026-08-07, Tik1)

Quy trình retry chỉ các máy lỗi từ batch all-máy, không đụng máy thành công / máy lock thật.

## 1. Phân loại lỗi từ summary.csv + report.json

Batch launcher ghi `summary.csv` (ExitCode 0=success, 3=locked, khác=error). Với máy error, đọc `runs/run_<serial>_<ts>/report.json` — `reason` chứa error code dạng `[CODE]`:

| Error code | Ý nghĩa | Xử lý |
|---|---|---|
| `UI_DUMP_FAILED ... uiautomator_idle_state_error` | UiAutomator wedged | Reboot (tầng 2) — retry sau reboot thường qua (máy 5 ✅) |
| `OPEN_TIKTOK_FAILED` | TikTok không vào feed sau force-stop | Retry — nhiều máy transient (máy 28 ✅) |
| `POST_RECHECK_UNAVAILABLE` | Không đọc được profile sau đăng → **chưa biết bài đã đăng chưa** | Hậu kiểm tay trước khi retry (tránh đăng 2 lần) |
| `MEDIA_FINGERPRINT_PENDING` | Ledger media SHA-256 status=reserved | Xử lý ledger, không retry mù |
| `ACCOUNT_SWITCHER_FAILED PROFILE_ROOT_NOT_CONFIRMED` | Không confirm profile root | Kiểm tra login/session máy |
| `POST_CONTROL_OCCLUDED_RECOVERY_FAILED` | Overlay che Post, recovery hết attempts | Xem mục 3 trong SKILL.md |
| `Missing required fields: ID TikTok` | Workbook cột ID trống | Điền ID, không retry được |
| `NO_ACCOUNT_LOGIN_REQUIRED` (exit 4) | Máy **logout** — đang ở Hồ sơ rỗng nút Đăng nhập | KHÔNG phải lỗi upload — cần login recovery/đăng nhập lại, KHÔNG retry upload |
| `DRAFT_CLEANUP_FAILED` | Không xoá được toàn bộ bản nháp (draft cũ từ lần đăng lỗi/reboot) | Retry — thường qua lần sau; nếu tái diễn xem `_delete_all_profile_drafts` |
| `VIDEO_PICK_SHOP_REPLAY_CARD` | UI recapture sau Back fail: `uiautomator_idle_state_error` ở bước chọn video | Reboot (tầng 2) giống idle_state_error |
| `DEVICE_STARTUP_FAILED ui_dump_error: non_xml_ui_dump` | UI dump trả rác không phải XML ngay startup | Reboot (tầng 2) trước retry |

## 1b. Exit code ngoài lề (verify 08-08)

- **exit 2 = fail MỚI trong run đó** (OPEN_TIKTOK_FAILED/UI_DUMP_FAILED/DRAFT_CLEANUP_FAILED), KHÔNG phải luôn "checkpoint MANUAL_REVIEW từ trước" như SKILL.md §5 cũ ghi — đọc `reason` trong report.json để phân biệt; quyết định theo `post_submission_state` (None = retry an toàn).
- **exit 1 = worker fail TRƯỚC khi có report dir** (vd `Missing required fields: ID TikTok` ở preflight) — đọc `machine-N.err.log` (UTF-16) lấy lý do.
- **exit 4 = NO_ACCOUNT_LOGIN_REQUIRED** (máy logout) — không phải lỗi upload, không retry.

## 2. Dọn lock stale trước retry

Các máy lỗi để lại lock `handoff` (worker giữ cho recovery nhưng process chết → STALE). Script archive (move, không delete) vào `D:\CodexRuntime\tiktok-video\stale-lock-archive\<ts>_retry_m<m>/`:
- Quét cả `machine_*.lock.json` lẫn `serial_*.lock.json` (2 file/máy).
- Verify pid chết bằng `wmic process where "ProcessId=N" get ProcessId` (tasklist silent-fail).
- **Giữ nguyên** máy có lock thật (pid sống) — VD máy 25, 34.

## 3. Assignment manifest — chạy đúng subset máy

Tạo `D:\CodexRuntime\tiktok-video\assignment-tik1-retryN-<ts>.json`:
```json
{
  "schema_version": 1,
  "assignment_id": "tik1-retry13-20260807_1530",
  "owner_id": "hermes-upload-retry13-20260807_1530",
  "resources": ["machine:1", "machine:4", ...],
  "reviewed_at": "2026-08-07T15:30:00+07:00"
}
```
Format khớp `automation_core/assignments.py` (schema_version=1, resources là set "machine:N").

Chạy:
```bash
cd /d/Taadaa/Tiktok-video && PYTHONPATH= \
  TIKTOK_VIDEO_ASSIGNMENT_MANIFEST="D:\CodexRuntime\tiktok-video\assignment-tik1-retry13-20260807_1530.json" \
  TIKTOK_VIDEO_WORKER_ID="hermes-upload-retry13-20260807_1530" \
  powershell -ExecutionPolicy Bypass -File run_tiktok_upload_batch.ps1 \
  -Tik 1 -MaxParallel 15 -Confirmation RUN > batch-retry13.log 2>&1
```
- Launcher check `AssignmentManifest.assert_owner(worker_id)` — owner_id phải khớp.
- Máy ngoài assignment → `SKIPPED_ASSIGNMENT` (exit 3).

## 4. Kết quả retry 13 (2026-08-07)

- 31 máy error → retry → **12 máy mới success** (4,5,15,21,26,28,29,38,39,53,63,69) = tổng 49/80 trong ngày.
- Máy 5 (idle_state_error) qua sau reboot — xác nhận reboot fix.
- Máy 28 (transient OPEN_TIKTOK_FAILED) qua — retry đơn giản đủ.
- Còn 19 máy: 8 OPEN_TIKTOK_FAILED, 3 UI_DUMP_FAILED (8,45,46 — chưa reboot tay), 3 POST_RECHECK_UNAVAILABLE (22,30,64 — cần hậu kiểm), 2 MEDIA_FINGERPRINT_PENDING (44,48), 2 ACCOUNT_SWITCHER_FAILED (13,70).

## 5. Bài học chạy batch

- **Set pin 80 cho ALL máy trước batch** — nhiều máy farm thực tế 1-5% (dialog pin yếu phá upload).
- Batch launcher process **treo khi pipe qua `tail`** — redirect ra file, không pipe.
- `python3` (Hermes) đọc summary.csv với `encoding='utf-8-sig'` (BOM).
- Chờ batch: poll `wmic ... | grep tiktok_workflow` đếm worker; summary.csv xuất hiện = gần xong.

## 6. Kết quả retry 14/15/16 (2026-08-07) — leo thang tới hết

- **Retry 14** (19 máy, reboot tay trước 8/45/46): **+5** success (14,45,46,64,65) — 45/46 qua sau reboot tay, xác nhận reboot là fix idle_state.
- **Retry 15** (14 máy): **+7** success (1,44,48,50,51,54,70) — máy 1 (pin) ✅, 44/48/54 (MEDIA_FINGERPRINT stale-release patch) ✅, 70 (soft-reboot) ✅.
- **Retry 16** (máy 72): 4 lần SKIPPED_LOCKED liên tục → chuyển sang worker trực tiếp (xem SKILL.md mục 8).
- **Tổng ngày**: 37 + 12 + 5 + 7 = **61 verified** + 3 ACCEPTED (10,22,30) = **64/80 thực tế có bài mới**. Còn lại: 7 (8,13,27,72 đang xử lý + 10/22/30 ACCEPTED), 6 MISSING_ID (73,75,77,78,79,80), 2 lock thật (25,34).
- **Máy 10/22/30 ACCEPTED**: đọc report `post_submission_state=ACCEPTED` → KHÔNG retry (đăng 2 lần). Tổng kết phải tính ACCEPTED vào success dù status=MANUAL_REVIEW.

## 7. Retry "máy hôm nay chưa đăng được" — multi-batch merge (verify 08-08)

Khi user yêu cầu "chạy đăng video cho các máy hôm nay chưa đăng được, trừ máy N" — KHÔNG retry all-farm mù, KHÔNG chỉ đọc batch cuối. Đúng quy trình:

1. **Merge NHIỀU summary.csv trong ngày** (`D:\CodexRuntime\tiktok-video\batch-runs\batch_*<ngày>*/summary.csv`, đọc `utf-8-sig`): mỗi máy gom set status qua các batch.
   - `ok = máy có ≥1 lần THÀNH CÔNG` (dù batch sau đó LỖI — máy đó ĐÃ đăng, đừng retry).
   - `fail = máy chỉ có LỖI/SKIPPED_LOCKED, không có THÀNH CÔNG` → tập retry.
   - Loại máy user yêu cầu trừ (giữ lock, không đưa vào manifest).
2. **Đọc report.json từng máy fail** — chỉ retry máy `post_submission_state=None` (fail TRƯỚC khi gửi). Máy ACCEPTED → xử lý §7 SKILL.md, không retry. (08-08: toàn bộ 26 máy fail đều None → retry an toàn.)
3. **Phân loại lỗi theo bảng §1**: máy `uiautomator_idle_state_error`/`non_xml_ui_dump` → reboot tay TRƯỚC batch (verify `sys.boot_completed=1` + `tun0` inet trước khi launch); máy `OPEN_TIKTOK_FAILED` retry thường qua; máy `DEVICE_LOCK_FAILED` do lock feed-scheduler pid chết → chỉ cần dọn lock.
4. **Dọn lock stale** (pid chết, `wmic` verify) — batch all-máy để lại hàng loạt `machine_*.lock.json` + `serial_*.lock.json` status `handoff` project `tiktok-upload`; worker fail nhưng process chết → lock STALE. Backup trước khi move.
5. **Tạo assignment manifest** subset fail → launch (`unset PYTHONPATH`, background + notify_on_complete, `-MaxParallel 10-15`).
6. **Sau batch: đọc summary mới, lặp phân loại** — máy fail lần 2 cùng signature `OPEN_TIKTOK_FAILED` đã đủ 2 attempts (contract AGENTS.md "at most two meaningful target attempts"): **KHÔNG tạo attempt 3** → báo user cần xử lý tay (reboot + chờ app load / login). Máy fail signature MỚI (VD lần 1 `DEVICE_LOCK_FAILED` → lần 2 `OPEN_TIKTOK_FAILED`) vẫn còn attempt → reboot + retry tiếp.
7. **Máy MISSING_ID** (workbook cột ID trống, fail exit 1 `Missing required fields: ID TikTok`) — không retry được, báo user điền ID; loại khỏi manifest ngay từ đầu.
8. **Sau batch, quét MỌI máy FAILED để tìm ACCEPTED chưa finalize** (bắt buộc — auto-handler không phủ mọi path):
   - Field `post_submission_state` trong report.json: `ACCEPTED` = bài ĐÃ đăng → finalize ledger + bump workbook theo SKILL.md §7, KHÔNG retry.
   - **Pitfall 08-08 máy 74**: run kết thúc `status=FAILED` + `error=None` + `post_submission_state=ACCEPTED` + `post_recheck_attempted=False` → auto-handler KHÔNG chạy (chỉ kích khi verify đi nhánh TIMEOUT→UNAVAILABLE). Ledger entry video 6 vẫn `reserved`, workbook vẫn 5 → **phải finalize tay** (backup ledger + workbook trước).
   - **Pitfall đọc ledger**: field `machine` trong `<sha256>.json` đôi khi là **int** (`74`) đôi khi là **string** (`"74"`) → so sánh LUÔN bằng `str(e.get('machine')) == '74'`, không dùng `== 74` (sẽ miss entry). Tương tự `video_number` cũng có thể là str.
   - **Pitfall đọc log UTF-16** (`execution.log`/`machine-N.out.log`): KHÔNG slice bytes trước khi decode (`open(...,'utf-16').read()[-800:]` → `truncated data` vì cắt giữa surrogate pair). Đọc cả file rồi decode, hoặc decode rồi mới lấy tail. `execution.log` run bị kill có thể chỉ ~8 dòng — không phải log hỏng, là worker chết sớm.

Kết quả 08-08: batch 1 (79 máy) 28 OK + batch 2 (46 máy) 25 OK = 53/80; retry 20 máy còn fail → +9 (3,25,29,31,39,40,42,63,64); retry 2 (7 máy, reboot trước 12/21/23/26) → +6 (12,21,23,26,27,36) — máy 74 ACCEPTED đã finalize (workbook 5→6) = 62/79 có bài mới. Còn lại: 6 MISSING_ID (73,75,77,78,79,80), 3 hết 2 attempts OPEN_TIKTOK_FAILED (52,65,69), 1 logout cần login (76), máy 34 trừ theo yêu cầu.
