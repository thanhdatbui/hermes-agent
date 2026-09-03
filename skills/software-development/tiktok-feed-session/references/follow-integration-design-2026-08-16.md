# Follow-integration design 2026-08-16 (3 phiên/ca + jitter + hook follow)

Design đã APPROVED sau 11 vòng audit Claude opus-5 (plan:
`.hermes/plans/2026-08-16_follow-hook-3-session-jitter.md`). NO-LIVE tại thời điểm
viết — chưa code, chưa chạy farm.

## Bối cảnh & quyết định user chốt (research Gemini hành vi TikTok thật)

- 480 acc, mỗi IP 6 acc, mỗi acc cần 1000 follower mở giỏ hàng (~60-70 ngày).
- Mỗi máy 3 acc, mỗi acc 1 ca/ngày, mỗi ca **3 phiên** (tăng từ 2) = 9 phiên/ngày/máy.
- 3 ca: **06:00 / 12:30 / 19:00** (đổi từ 7/14/21 — peak thật + tránh trễ qua đêm).
- **Jitter ±15-20'** deterministic per machine/day/block (tránh dấu vân tay cronjob).
- Nghỉ giữa phiên **35-60'** (đổi từ 60-90').
- Organic follow 5→**6%** (không phải 12 — code hiện tại là 5).
- Follow chéo: 3-7/phiên (config follow repo, budget 18-21/ngày acc cũ).
- **Account switcher chỉ phiên đầu ca (session_index 1)** — phiên 2,3 cùng acc chỉ
  verify nhẹ (fail-safe nếu nick lệch), không switch.
- Hook follow cuối phiên: subprocess gọi `D:\Taadaa\tiktok-follow\follow_runner\run_follow.py
  --machine N --config ...\config.example.yaml --account-row-index R`; KHÔNG import chéo;
  gate sensitive (login/OTP/2FA/captcha → skip); FOLLOW_FAILED đánh dấu không dừng.
- **Reactive per-machine**: phiên 2/3 = xong phiên trước + nghỉ 35-60' (máy nào xong
  trước nghỉ theo máy đó — tự nhiên hơn giờ cố định). Máy chậm chỉ mất phiên cuối hôm đó.

## Scheduling thật (đọc từ code — job_spec.py)

- PICKER `0 6 * * *` (1 lần/ngày 6:00) → chọn acc due + viết manifest (session 1/2/3 giờ ấn định).
- RUNNER `*/15 * * * *` (mỗi 15') → đọc manifest, chạy máy due tick đó.
- WATCHER `7,22,37,52` (lệch pha 15') → giám sát.
- `_feed_decision` chỉ có NEVER_SUCCESS / HARD_OVERDUE (≥3 ngày) / NORMAL_DUE (2 ngày) /
  NOT_DUE (0-1 ngày) — KHÔNG có khái niệm phiên ở cấp picker; session_index từ manifest.
- `unresolved_reservation` → IN_FLIGHT → máy bận skip phiên mới (không kẹt vĩnh viễn).

## Test max_worker thật (ATX — KHÔNG dùng uiautomator dump!)

**User correction 16/08: "test max worker sao lại dùng uiautomator, t chuyển qua dùng
atx service hết r mà"** — farm đọc UI qua ATX agent port 7912, không phải uiautomator.

ATX API đúng: `POST http://127.0.0.1:<port>/uiautomator` (lifecycle endpoint —
xem `capture_recovery.py:1114 _atx_http_request`). KHÔNG phải `/wd/hub/status`,
`/jsonrpc/0`, `/health` (404). Root `/` là web UI không phải API.

Kết quả đo thật (80 máy online, ADB `C:\Program Files (x86)\xiaowei\tools\adb.exe`):

| Parallel | ATX /uiautomator | ghi chú |
|---|---|---|
| 5 | 1.1s, 0 lỗi | |
| 10 | 0.1s, 3 lỗi | forward port 7912 dùng chung local port → đụng |
| 15 | 0.1s, 0 lỗi | |
| 20 | 0.1s, 0 lỗi | |

→ ATX chịu tốt tới 20 song song. **Chốt max_workers = 12** (an toàn dưới 15 + đủ nhanh).
Lưu ý: code thật dùng port riêng mỗi máy (9008, capture_recovery.py) nên không đụng
như test dùng chung 7912. Ping nhẹ (shell echo) không phải benchmark đúng — phải dùng
công việc thật (ATX dump/lifecycle).

## Feasibility math (đã verify audit)

- Block 1 jitter+20' + gap 60': s3_end = 11:20 → gap Block2 (12:30) = 70' < INTER_BLOCK
  min 90' — **by design**: INTER_BLOCK_GAP (90,300) chỉ contractual cho feasibility
  non-jittered; anchor cố định quyết định scheduling.
- Non-jittered: s3_end 11:00 → gap 90' = đúng min ✓. Block 3 s3_end worst 00:20 hôm sau
  < WINDOW_END_HOUR=2 ✓.

## Pitfalls implement (từ 11 vòng audit — tránh lặp lại)

- Gap + jitter worst-case phải tính buffer giữa ca (ban đầu gap 70' + jitter 35' → gap=0).
- Jitter dùng chung RNG với pair_gap → drift manifest cũ → **rng riêng, seed
  `machine_day_seed ^ 0x9E3779B9 * block_index`** (mỗi block jitter khác nhau).
- `build_block_sessions(day, *, block_index, pair_gap_minutes, jitter_minutes: int = 0)`
  — picker pick jitter từ rng ngoài rồi truyền GIÁ TRỊ, không truyền rng (tránh double-jitter).
- `AccountBlock.jitter_minutes: int = 0` default (backward-compat test shape).
- `session_index` truyền qua `child_config["_session_index"]` — KHÔNG thêm field
  MachineAccount (tạo từ workbook, không có session_index).
- Picker line numbers: unpack loop 246 + session_slots 257 (sẽ dịch khi sửa).
- Tests phải liệt kê ĐẦY ĐỦ test sẽ vỡ (audit vòng 7-9 bắt: pair_gap_on_grid,
  feasibility_all_blocks, account_block_dataclass_shape, anchor_and_pair_gap,
  block3_finishes_within_window — mỗi vòng bắt thêm 1-3 test sót).

## User preference báo cáo plan

"Sửa xong báo cáo lại plan theo workflow đơn giản cho t đọc hiểu" — báo cáo plan cho
user: tiếng Việt đơn giản, bảng so sánh Cũ→Mới, không thuật ngữ kỹ thuật, trả lời
thẳng câu hỏi (số liệu thật không suy đoán), hỏi đúng 1 quyết định còn chặn.
