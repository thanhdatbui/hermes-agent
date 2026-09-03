# Sự cố m74: FALSE POSITIVE SUCCESS — workflow báo đã đăng nhưng video chưa lên profile (2026-08-12)

## Triệu chứng

- Run `run_ce061606c21e153d03_20260812_101710` báo `status=SUCCESS`, `post_verified=True`, ghi workbook máy 74 `Video Đã Đăng` 6→7.
- User kiểm tra profile @muyduyen4589: **không có video mới** — vẫn 5 tile cũ (bếp, súp, trời, cửa hàng, cherry).
- User bác: "T thấy 74 vẫn chưa có video ms. Bằng chứng nào m ns đã đăng video r? Gửi hình ảnh xem".

## Chuỗi root cause (3 lớp lỗi chồng nhau)

1. **Run đêm trước** (`..._20260811_234206`, 23:55): tap "Đăng" bị **ADB timeout** → `post_submission_state=UNKNOWN`, `post_submission_accepted=False`, **KHÔNG có** `post_tapped_at`/`post_submission_accepted_at` trong receipt. Verify lạc sang surface `TIKTOK_LIVE_MOBILE_GAMING` → `MANUAL_REVIEW`. Video 7 thực tế CHƯA lên.
2. **Run sáng** (`..._20260812_101710`, 10:17): `RESOLVE_NEXT_VIDEO` thấy receipt cũ (đánh dấu `completed` dù submission UNKNOWN) → **nhảy thẳng VERIFY_POST, KHÔNG chạy POST/MEDIA_PUSH**.
3. **VERIFY_POST false positive**: log `[PROFILE_GRID] Không tìm thấy scroll container; dừng ở viewport 1` → đếm "3 tile (baseline=3)" dù profile thật có 5-6 tile; lượt sau "4 tile" → suy ra "increment confirmed" → ghi workbook 7. **Baseline sai + increment giả** = false positive.

## Đối chiếu receipt: video 6 (thành công thật) vs video 7 (false)

| Trường | video 6 (ACCEPTED) | video 7 (giả) |
|---|---|---|
| `post_submission_state` | ACCEPTED | UNKNOWN |
| `post_submission_accepted` | True | False |
| `post_tapped_at` | có | KHÔNG có |
| `post_submission_accepted_at` | có | KHÔNG có |

## Fix (đã áp vào `state_machine.py` + tests, suite 344→350 pass)

- **COMPAT-POST-VERIFY-004** (`_post_submission_state_allows_success`): `post_submission_state=UNKNOWN` + có bằng chứng Post attempt (`post_tap_attempted`/`post_intent_at` trong receipt) → chặn success/workbook, `MANUAL_REVIEW` với `[POST_SUBMISSION_UNKNOWN]`. Chỉ ACCEPTED (hoặc proven) mới advance. NOT_ACCEPTED giữ riêng nhánh proven-not-posted retry.
- **COMPAT-POST-VERIFY-005** (`_profile_scan_is_reliable`): scan reliable chỉ khi `viewports >= 2`. Increment chỉ được kết luận khi cả baseline_scan lẫn current_scan đều reliable (`POST_RECHECK` cũng áp dụng). Scan 1 viewport / grid bị cắt → không dùng làm bằng chứng.
- Generic text marker "đã đăng/posted" chỉ là `PROOF_INSUFFICIENT`, không phải publication proof; phải có own-post surface hoặc exact-account profile increment.

## Cách dọn state để retry (đã dùng thành công)

1. **Revert workbook** về counter đúng (backup `.bak-revert-74-to-6-<ts>.xlsx` trước khi ghi).
2. **Archive receipt sai**: `mv machine_74_video_7.json machine_74_video_7.json.bak-false-complete-<ts>` — receipt `status=completed` nhưng submission UNKNOWN sẽ chặn retry (workflow coi là "đã post").
3. **Archive fingerprint sai** trong `idempotency/media-fingerprints/<key>.json`:
   - `status=verified_success` do run false-positive → `.bak-false-verified-<ts>` (nếu không dọn → `[DUPLICATE_MEDIA_BLOCKED]`).
   - `status=reserved` do run bị kill giữa chừng → `.bak-reserved-killed-<ts>` (nếu không dọn → `[MEDIA_FINGERPRINT_PENDING]` unresolved).
4. **Xóa cả 2 lock** `machine_74.lock.json` + `serial_<serial>.lock.json` sau khi xác minh PID chết (wmic/tasklist).
5. Chạy lại live — verifier mới yêu cầu ACCEPTED + scan reliable.

## Verification discipline (bắt buộc từ sự cố này)

- `report.json status=SUCCESS` + `post_verified=True` **không phải bằng chứng** — nó từng sai.
- Bằng chứng hợp lệ trước khi báo DONE:
  1. Receipt: `post_submission_state=ACCEPTED` + đủ `post_tapped_at` + `post_submission_accepted_at`.
  2. Log scan: `viewports >= 2` ở cả baseline và sau.
  3. Ảnh độc lập: chụp profile thật TRƯỚC (baseline) và SAU (post) — so danh sách tile bằng vision, phải thấy tile mới xuất hiện (ví dụ m74: 5→6 tile, tile selfie mới, 9 views).
  4. Workbook đúng path runtime (`D:\OneDrive\TaadaaData\kibe\Tik1.xlsx`) tăng counter.
- Mở profile bằng ADB: tab Hồ sơ = tap (972,1883). **Tap (540,1840) là nút + giữa → mở composer/upload, KHÔNG phải profile** — nhầm lẫn đã xảy ra khi chụp proof.
- `post_submission_state=ACCEPTED` là khác biệt quyết định giữa "đăng thật" và "tap timeout không rõ kết quả" — kiểm tra nó trước mọi kết luận.
