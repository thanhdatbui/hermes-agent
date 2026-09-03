# Row-5 canary + popup policy + commit trail (17/08 tối, live-wire chạy thật)

## Kết quả row 5 canary (lệnh `run-feed-session.ps1 -Row 5 -Machines <list> -Run`)

| Máy | Nick row 5 | Feed | Follow | Fix đã áp dụng |
|---|---|---|---|---|
| 5 | thachkieu05 | ✅ success | ✅ OK 2 nick | skip-identity-verify |
| 19 | haihuong980 | ✅ success | ✅ OK 2 nick | ATX stub restart + `_sleep_and_recapture` 2.5s |
| 21 | — | ✅ success (lần đầu) | ✅ | sạch từ đầu |
| 34 | — | ✅ success (lần đầu) | ✅ | sạch từ đầu |
| 33 | chungan981 | ⚠️ kẹt swipe 12: popup "Follow bạn" | (chưa follow — popup chặn) | thêm rule `follow_friend_dismiss` → "Không quan tâm" |
| 35 | phungmwgtc4 | ✅ success | ✅ OK 4 nick | ATX stub restart |

## Popup "Follow bạn" — policy user chốt (17/08 tối, máy 33)

- Màn hình: video feed + banner "Follow bạn" + 2 nút **"Follow lại"** (đỏ) / **"Không quan tâm"** (xám). TikTok hiện khi có người follow nick — gợi ý follow lại.
- User: *"Bấm không quan tâm nhé, k đc bấm follow lại"* → rule `follow_friend_dismiss` trong `GEMPHONEFARM_BLIND_POPUP_RULES`:
  - detect: `//node[@text="Follow bạn"]`
  - tap: `//node[@text="Không quan tâm"]`, loop=True
- Lý do cấm "Follow lại": follow phải qua follow hook (budget/order riêng); bấm ngoài script = follow không kiểm soát.
- Rule chung: popup mời hành động tác vụ → chỉ dismiss, không bao giờ thực hiện hành động popup đề nghị.

## Commit trail session này

- `tiktok-follow`:
  - `e4aed22` + `d7760e9` — skip_identity_verify vào config + run_follow CLI flag (lưu ý: engine patch bị interrupt mất 1 lần, phải re-patch + verify `git show HEAD:file | grep`).
  - `671a9b6` — engine `run_session`: khi `cfg.skip_identity_verify` → bỏ `switch_account_and_verify`, set `active_account_handle = row.tik_id` thẳng.
- `tiktok-luot nuoi acc`:
  - `79093ec` — follow hook truyền `--skip-identity-verify` + fix `launch_evidence` UnboundLocalError.
  - `5cf7edb` — ui_capture ATX-primary + benign_popup wait 2.5s + feed_swipe rule "Không quan tâm".

## Cron (17/08 tối) — trạng thái cuối

- Picker `304211820b28` (0 6 * * *) — OK.
- Runner + watcher bị xóa khi interrupt update repeat → **tạo lại**: runner `cdd43b124363` (`*/15 * * * *`), watcher `7890172324ca` (7,22,37,52) — cả 2 `no_agent=true` + **`deliver: local`** (tránh spam Telegram mỗi tick).
- 3 wrapper hash khớp repo; permit + env.json đầy đủ.
- Trả lời user "cron hoạt động chưa": runner/watcher không còn trong list = không tự lướt được — luôn `cronjob list` lại trước khi khẳng định.
