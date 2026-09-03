# 3 phiên/ca + follow hook + canary — bài học 2026-08-16

Kèm theo session implement "3 sessions/block + jitter + follow hook + max_workers 30" (commit 460096f). Skill `tiktok-feed-session` SKILL.md đã quá size (103K) — bài học chi tiết để ở đây, SKILL.md chỉ thêm pointer.

## Worker subagent hết budget (100 API calls) — session-as-worker là đường cứu

Khi dispatch worker implement task LỚN (nhiều file, đụng manifest/constraints), subagent hay hết `api_calls=100` (giới hạn delegation budget, KHÁC `max_iterations` tool calls) giữa chừng — 2 lần liên tiếp:
- worker 1: hết sau khi đọc plan + code (0 file sửa) — nhưng phát hiện blocker manifest.py hardcode 2 sessions
- worker 2: hết sau khi xong RED tests (chưa implement GREEN)

**ĐỪNG spawn worker 3 mơ hồ** (mỗi worker mới tốn 100 calls load lại context). Chuyển **session-as-worker** (HERMES_SUBAGENT_RULES fallback): session tự implement phần còn lại theo plan APPROVED. Worker chỉ hữu ích cho việc GIỚI HẠN RÕ (VD sửa 1-2 file tests theo pattern có sẵn) — worker 3 sửa 44 tests fleet/contract thành công (nó tự sửa thêm 2 production bugs phát hiện — chấp nhận vì đúng).

**Khi worker báo "chưa implement" hãy ĐỌC summary file đầy đủ** (`C:\Users\Kibe\AppData\Local\hermes\cache\delegation\subagent-summary-*.txt`) — blocker quan trọng thường nằm trong "middle omitted", không thấy ở preview.

## Thay đổi scheduling — allowlist phải gồm manifest.py + models.py

Plan chỉ liệt kê blocks.py/picker.py nhưng **manifest.py hardcode toàn bộ constraints** — sửa blocks/picker lên 3 sessions mà không sửa manifest → picker gọi `validate_manifest` → raise `SOURCE_CONFIG_INVALID` ngay:
- `CONSTRAINTS`: sessions_per_block, pair_gap_minutes, inter_block_gap_minutes, slot_grid_minutes, block_anchors
- Validators: pair_gap `not in (60,75,90)`, session_index `not in (1,2)`, `len(block_entries) != 2`, inter-block `< 180`, session_slots so với `build_block_sessions` (2-tuple), entry_ids `(s1,s2)`, identity check chỉ s1/s2
- `models.py`: `SLOT_GRID_MINUTES` (15→5) — grid thay đổi phải đổi cả đây

→ **Quét grep `sessions_per_block\|pair_gap_minutes\|block_anchors` toàn repo TRƯỚC khi chốt allowlist**, đừng chỉ tin plan.

## Reactive scheduling phiên 2/3 + cap 3 phiên/ngày

- Phiên 2/3 KHÔNG giờ cố định: runner GHI `last_feed_success_at` sau mỗi phiên success → phiên sau = last + random(35-60') per-machine
- **BẮT BUỘC cap 3 phiên/ngày**: `_feed_decision` đếm `success_timestamps` hôm nay; ≥ 3 → NOT_DUE (không có cap → reactive chạy 4-5 phiên/ngày)
- Jitter clamp: block 1 anchor 06:00 = window start — jitter âm (-15/-20) đẩy s1 trước 06:00 → `RESERVED_BLOCK_CONFLICT`/`is_schedulable_interval` reject. **Clamp block 1 jitter ≥ 0**; blocks 2/3 giữ ±20 (anchor sâu trong window)
- INTER_BLOCK_GAP (90,300) chỉ contractual cho feasibility test **non-jittered** (dùng nominal/unjittered slots) — jitter thực có thể vi phạm (gap 70' < 90') là by design; manifest validator phải so sánh **nominal slots** không phải jittered

## Follow hook (multi_machine_feed_session.py)

Sau `child_result = _result_from_child_context(...)` khi `final_status in {"success","degraded"}` → `_run_follow_hook`:
- **Gate sensitive**: stop_reason chứa login/OTP/2FA/captcha/security/verify → skip (ghi `sensitive-skip`)
- **Subprocess thuần** (KHÔNG import chéo follow_runner — 2 core/PYTHONPATH khác nhau): `python D:\Taadaa\tiktok-follow\follow_runner\run_follow.py --machine N --config ...\config.example.yaml --account-row-index R`
- Đọc `FOLLOW_RESULT <json>` từ stdout + exit code; ghi `follow_result.json` vào child artifact
- FOLLOW_FAILED → ghi `follow_failed: true` (không dừng phiên — feed đã xong)
- Timeout 900s; exception → log không crash

## Chạy canary multi-machine-feed-session — pitfalls

- **`unset PYTHONPATH` TRƯỚC khi chạy** — session có `PYTHONPATH=D:/Taadaa/Tiktok-video/scripts` set sẵn → run_tiktok.py import PIL từ hermes venv thiếu `_imaging` → ImportError. Chạy với:
  ```bash
  unset PYTHONPATH && export PYTHONTZPATH='D:/Taadaa/Hermes/.venv/Lib/site-packages/tzdata/zoneinfo' && /d/Taadaa/python-envs/automation/Scripts/python.exe -B python_runner/run_tiktok.py --mode multi-machine-feed-session --machines 4 --account-row-index 1 --account-workbook 'D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx' --max-workers 1 --allow-navigation-only --allow-feed-swipe --allow-benign-popup-dismiss --prepare-tiktok
  ```
- **Bắt buộc `--account-workbook` + `--account-row-index`** (thiếu → config-error "requires --account-row-index"/"--account-workbook")
- **`--account-row-index` = số thứ tự NICK trong máy** (1-based), KHÔNG phải row workbook: taikhoan_run_safe.xlsx cấu trúc (May, Device ID, ID) — mỗi máy nhiều nick (máy 4: row 20-25 = thuuy.thy, dinhlan24076...). Máy 4 nick 1 = `thuuy.thy` → row-index 1. (Tik1.xlsx khác: 1 máy = 1 row, cột Máy = số máy.)
- **Serial log có prefix `device:` là MASK** (`mask_value(serial, prefix="device")`) — không phải emulator. `device:6539271ed7` = serial thật bị che. Đừng kết luận "sai máy" từ log masked.
- Manual-needed thường do máy kẹt splash (máy yếu load lâu) → classifier "not confidently classified as Add phone popup" — kiểm tra ảnh screen.png trước khi blame code.
- `device:` prefix trong adb devices = ADB reverse/emulator serial thật (khác với mask_value prefix).
