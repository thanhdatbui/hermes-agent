# Retry batch recovery + RecoveryMode preflight correction (2026-08-06)

## `-RecoveryMode` KHÔNG qua được inventory lock filter — SỬA hướng dẫn cũ

Trước đây skill ghi "`--recovery-mode` để takeover lock stale" — **SAI khi dùng qua launcher**:

- `machine_inventory.py::_filter_locks` chỉ `path.exists()` check lock file — không biết recovery-mode/takeover. Launcher LUÔN chạy inventory preflight trước khi launch → máy giữ lock handoff bị skip ngay từ preflight: `machine_launch_order` rỗng, "Máy mục tiêu: none", batch exit 3, 0 verified, toàn bộ 80 máy "Target bị bỏ qua".
- Takeover lock stale chỉ xảy ra ở WORKER lúc live (`--recovery-mode`) — KHÔNG cứu preflight.
- **Muốn retry máy đang giữ lock handoff: xoá lock stale TRƯỚC khi chạy launcher** (cả `machine_N.lock.json` + `serial_<serial>.lock.json`; backup trước). Preflight xong sẽ thấy eligible.
- `-RecoveryMode` vẫn bật cho worker (soft-reboot/OPEN_TIKTOK handler) nhưng không giải phóng preflight.

## Điều kiện xoá lock stale an toàn

```python
# lock file: C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json
# an toàn xoá khi: status == "handoff" AND owner_active == false AND PID chết
r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True)
dead = str(pid) not in r.stdout   # 1 slash — `//FI` fail trên MSYS
```
- PHẢI xoá CẢ `machine_N.lock.json` VÀ `serial_<serial>.lock.json` — chỉ xoá 1 cái inventory vẫn báo `device lock present`.
- Serial từ cột `device ID` workbook. Backup trước (`lock-backup_<date>/`).
- Sau khi worker live chạy, lock xuất hiện LẠI (re-acquire) + fingerprint re-reserve — đó là hành vi đúng, không phải lỗi.

## Playbook retry batch nhiều máy (đã chạy 3 vòng batch 2026-08-06)

1. **Preflight toàn workbook** → đọc `batch-runs/batch_tik1_*/summary.csv` (UTF-8-sig): tách `THÀNH CÔNG` / `SKIPPED_LOCKED` (SkipReason `device lock present`) / `SKIPPED_ASSIGNMENT` (ngoài manifest) / `LỖI`.
2. **Manifest MỚI đúng scope mỗi lần retry** (không dùng lại manifest cũ — máy success sẽ resolve video kế tiếp và đăng thêm). Verify schema + scope bằng ad-hoc script trước live.
3. **Phân loại reason từng máy** từ `runs/<serial>_<ts>/report.json`: đọc `status`, `last_state`, `reason`, `post_tap_attempted`, `post_verified`. exit=2 = MANUAL_REVIEW; exit=1 = FAILED (đọc log riêng — khác hẳn).
4. **Dọn fingerprint stale**: `idempotency/media-fingerprints/*.json` có `status=reserved` VÀ **không có** post-attempt `machine_X_video_N.json` → backup + xoá. Có post-attempt (completed/verification_pending/ACCEPTED) → GIỮ (receipt barrier chống repost).
5. **Dọn lock stale** (mục trên).
6. **Máy uiautomator treo** (dump rỗng/`Killed`/`null root node` dù đã force-stop) → `adb reboot` + chờ `getprop sys.boot_completed`=1 + chờ/verify `tun0` (watcher gán lại 30-300s; máy không lên → `set_proxy` thủ công từ `PROXYgandienthoai.xlsx` cột proxy, qua `vi_changer_runner.set_proxy` — đã gán máy 74).
7. **Preflight lại** (xác nhận eligible) → live `-RecoveryMode`.
8. **Hậu kiểm success**: workbook `Video Đã Đăng` == số receipt completed == max video number receipt — không dựa process exit.

## Attempt budget (Recovery Contract)

- **Cùng signature ≥2 lần = DỪNG, không attempt 3** (máy 10 POST_RECHECK ×3, máy 27 ACCOUNT_SWITCHER ×2, máy 65 OPEN_TIKTOK ×2).
- Signature KHÁC nhau được retry nhưng mỗi lần cần material change: reboot (sửa uiautomator treo), xoá fingerprint stale, handler mới.
- Sau retry vẫn fail cùng signature → giữ MANUAL_REVIEW + báo user, không spam retry.

## CAPTION signature mới: "Paste action not found" (máy 74, 2026-08-06)

- Clipboard broadcast OK (escape `#` đã fix COMPAT-CAPTION-003) nhưng sau paste action không tìm thấy → 3/3 attempts fail → FAILED exit=1.
- **Chưa có handler** — theo rule bắt buộc phải implement handler + regression test + COMPAT entry trước khi retry (bắt XML lúc fail để biết paste menu variant).

## Web API hậu kiểm — account private/rỗng trả videoCount rỗng

`curl ... https://www.tiktok.com/@<user>?lang=en | grep -oE '"videoCount":[0-9]+'` trả RỖNG khi account private/không public — KHÔNG kết luận được "chưa đăng". Pattern `PUBLISHED_VERIFIED_WEB_API`/`SUPPRESSED_NOT_PUBLIC` chỉ áp dụng khi web TRẢ SỐ. Private account → verify in-app (mở profile máy đếm tile).

## Máy OFFLINE ADB + workbook thiếu dữ liệu

- Máy lỗi nhưng serial KHÔNG có trong `adb devices` (đổi serial/ngắt USB) → không retry được, báo user.
- Preflight fail `Missing required fields: ID TikTok` (exit 1) = workbook thiếu dữ liệu cột `ID`, không phải lock — cần bổ sung workbook trước khi chạy.
