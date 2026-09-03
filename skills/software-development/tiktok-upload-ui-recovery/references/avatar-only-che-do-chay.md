# AVATAR-ONLY — chế độ chạy chỉ đổi avatar (2026-08-10)

## Rule (phủ Tiktok-video PROJECT_RULES.md, đã commit 438411d)

**Khi user yêu cầu CHỈ đổi avatar → PHẢI dùng cờ avatar-smoke:**

```text
--avatar-smoke --force-avatar-upload --force-avatar-machines N
```

Flow: `RESOLVE → ENSURE_AVATAR → RELEASE` — KHÔNG push video, KHÔNG post, KHÔNG ghi workbook. Worker exit 0, report `status=AVATAR_SMOKE_SUCCESS`, signature `FORCED_REPLACED_VERIFIED`.

## Pitfall NGHIÊM TRỌNG — cấm `--force-avatar-upload` đơn lẻ cho mục đích avatar-only

- `--force-avatar-upload` đơn lẻ = **FULL flow** (MEDIA_PUSH → VIDEO_PICK → POST) rồi mới tới ENSURE_AVATAR ở cuối → **đăng video thừa** mỗi lần chạy.
- Bằng chứng 2026-08-10: m38 tile video 12→13 bị đăng vô ý; m36+m38 run 18h3x đăng video mới lần nữa vì dispatch sai cờ. User bực: "ns là chỉ đăng ava lại thôi mà?".
- User chốt: video đã đăng thừa thì **để im, không xóa, không retry**; chỉ sửa cách chạy lần sau.

## Verify sau khi chạy avatar-only

1. Report mới: `status=AVATAR_SMOKE_SUCCESS` + signature `FORCED_REPLACED_VERIFIED`.
2. **`post_submission_state` PHẢI vắng mặt (None)** — nếu có value nghĩa là đã đụng post = sai cờ.
3. `post_verified=true` trong report CŨ (run trước) = không retry post, chỉ avatar smoke.
4. Verify sau save: similarity ≥ 0.800 (pick trước ≥ 0.600), poll 1.

## Verify ngưỡng avatar picker

- `AVATAR_PICKER_TILE_MATCH_THRESHOLD` = 0.600 (pick tile).
- Verify sau save threshold 0.800.
- Visual fallback corr cần đủ cao; nếu "Recent grid" = VIDEO grid (có tile video) thì tile video KHÔNG bao giờ khớp avatar — phải mở album ảnh (Download/Hình ảnh/Images/Ảnh/Camera) hoặc ưu tiên image tile (fix ccd28f3).

## Trigger

- User: "đổi ava máy X", "chỉ đăng avatar thôi", "up ava lại cho X,Y".