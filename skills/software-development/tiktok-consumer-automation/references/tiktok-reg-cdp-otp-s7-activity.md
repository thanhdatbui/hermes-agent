# CDP-only OTP reading + Samsung S7 background-activity-kill (2026-08-06, Tiktok_Reg)

## Root cause của cả class `OTP_SCREEN_NOT_PRESERVED` / `OTP screen unavailable after Recents recovery`

Trên farm **SM-G930F (Samsung S7, Android cũ, RAM hạn chế)**, TikTok KHÔNG preserve
màn OTP khi bị đưa xuống nền: **bất kỳ lần nào mở app khác (Chrome fullscreen để
login/inbox, Gmail app để verify account) trong suốt flow reg, TikTok activity OTP
bị OS thu hồi** → quay lại bằng Recents/reorder-to-front thì rơi về
`SignUpOrLoginActivity` (registration entry) thay vì màn OTP → fail.

Bằng chứng: 4 run liên tiếp, 5/5 máy fail cùng signature dù fix code khác nhau;
CDP fast-path chạy được nhưng vẫn fail vì TikTok đã chết từ lúc mở Chrome ở bước
trước (login). **Không fix được bằng code** — giải pháp duy nhất là không bao giờ
mở app khác giữa flow (pre-login) hoặc xử lý thủ công.

## Pattern đúng: đọc OTP KHÔNG rời TikTok (CDP fast-path)

Hotmail/Outlook: thay vì mở Chrome fullscreen để đọc OTP, dùng CDP đọc tab nền:

1. `adb forward tcp:9223 localabstract:chrome_devtools_remote`
2. `GET http://127.0.0.1:9223/json` → tìm tab có `outlook.live.com/mail` +
   `webSocketDebuggerUrl`
3. WebSocket `Runtime.evaluate` → quét DOM `div,span,a` có `tiktok` → collect
   code 6 số.
4. **Gọi CDP fast-path TRƯỚC khi `am start` Chrome** — nếu tab Outlook inbox đã
   login sẵn (từ lần trước), đọc code và return ngay, TikTok không bao giờ rời
   foreground → OTP screen sống. Chỉ mở Chrome khi CDP không có tab inbox.
5. Đã live-proven: STT 57 log `[otp-browser] OTP qua CDP background tab` — lấy
   được code, không mở Chrome.

## Outlook merged-conversation: 2 mail OTP dồn 1 conversation

Khi 2+ mail OTP TikTok gộp vào 1 conversation trong Outlook web, **DOM xếp mail
CŨ trước, mail MỚI cuối**. Bug cũ: `candidates[0]` = code mail cũ (sai — đúng lời
user "otp trên là mail cũ kéo xuống dưới mới ra mail đúng").

Fix: collect codes theo thứ tự DOM rồi **quét `reversed(candidates)`** (cuối =
mới nhất), filter `re.fullmatch(r"\d{6}", code)`.

## Gmail fast-path (đọc từ Gmail APP — không bao giờ mở Gmail web)

Gmail PHẢI đọc từ app `com.google.android.gm` (user chỉ rõ: "gmail phải đọc từ
app chứ sao lại mở web, hotmail mới mở web"). Để giảm thời gian rời TikTok:

- Sau khi `_ensure_gmail_mailbox("after account switcher")`, gọi
  `extract_recent_tiktok_otp_from_gmail_list` NGAY (fast-path preview) trước
  Promotions/refresh — Gmail hiển thị code 6 số trong preview snippet → return
  sớm (~5-10s thay vì 80s).
- Chỉ fallback Promotions/refresh/search khi preview không có code.

## Mail-die guard — dạng cuối (chỉ DEAD xóa)

Trong `_enter_tiktok_email_otp_with_one_fresh_retry` và nhánh `[7c]`:

- `ALIVE`, `UNKNOWN`, `BLOCKED` → **giữ mail, không cleanup**.
- Chỉ `DEAD` → ghi Audit Pending + xóa khỏi source.
- Lý do `BLOCKED`: `check_mailbox_alive` trả `BLOCKED` cho MỌI `LoginBlocked`
  (gồm Microsoft protection/recovery prompt — KHÔNG phải mail die). BLOCKED cần
  xử lý người, không tự xóa.

## Chrome save-password dialog che Microsoft recovery form

Khi gặp Protect account (`account.live.com/proofs/Add`), popup Chrome
"Lưu mật khẩu?" (`luu mat khau` / `save password`) che form → `recover_account`
điền email vào ô save-password thay vì ô email khôi phục → bấm "Tiếp theo" không
vào OTP screen → `RECOVERY_OTP_SCREEN_NOT_IDENTIFIED`. Fix: dismiss popup
(tap "Không bao giờ"/"Never") TRƯỚC khi gọi `recover_account`.

## Venv/test pitfalls khi chạy pytest consumer

- `--system-site-packages` venv kế thừa PIL system hỏng (`_imaging` import fail)
  → đặt PYTHONPATH venv site-packages LÊN ĐẦU
  (`D:\...\tiktok-reg-recovery\Lib\site-packages;...`) hoặc cài PIL vào venv.
- Chạy test files RIÊNG LẺ (`pytest tests/x.py`) — collect chung nhiều file
  lỗi collection transient do thứ tự import `flows` package (không phải lỗi code).
- `timeout` trong git-bash trên Windows gọi `TIMEOUT /?` (lệnh Windows) — dùng
  foreground không timeout hoặc cấu trúc lại lệnh.
