# Bay 2-Way Sync Cua cron_sync_watchdog Ghi De Nguoc & Dirty Revert Ban Fix Git (26/10/2026)

## 1. Hien Tuong Thuc Te
- User va agent da fix loi chong spam 2FA watchdog o session trua (commit 9fdf62327 luc 13:30: chi kiem tra last_2fa_date == today_str, bo and is_success).
- Tuy nhien den ca toi (22:31 & 22:33), nhom Telegram 'Tiktok add 2fa' (-5468653590) tiep tuc bi ban 2 ban tin loi lien tiep y het nhau cach nhau 2 phut.
- Kiem tra git status trong repo Deploy: file cron_night_tiktok_2fa_watchdog.py bi o trang thai dirty modified, va git diff cho thay toan bo diff cua commit 9fdf62327 bi revert nguoc ve code cu co is_success.

## 2. Nguyen Nhan Goc Re (Root Cause)
1. Kien truc dong bo 2 chieu (2-way sync) trong cron_sync_watchdog.py:
   - Chieu 1: DEPLOY_SCRIPTS -> KIBE_SCRIPTS & ONEDRIVE_SCRIPTS.
   - Chieu 2: KIBE_SCRIPTS -> DEPLOY_SCRIPTS & ONEDRIVE_SCRIPTS (nham muc dich dong bo neu co sua nong o runtime Kibe).
2. Bay mtime (Timestamp collision) & Ket co --force:
   - Khi commit Git tai DEPLOY_SCRIPTS luc 13:30, file co timestamp 13:30.
   - Thu muc runtime Kibe hoac OneDrive vi ly do dong bo dam may/touch tien trinh duoc cap nhat timestamp len 17:39.
   - Ham sync_file(src, dst, force=False) co doan ma:
     if dst_mtime > src_mtime + MTIME_TOLERANCE_S: return 'skipped'
     Ke ca khi truyen force=True, dieu kien nay nam TRUOC khoi kiem tra if not force, khien chieu Deploy -> Kibe bi skip hoan toan.
   - Den Chieu 2 (Kibe -> Deploy), vi src_mtime (Kibe: 17:39) > dst_mtime (Deploy: 13:30), watchdog nhan dinh Kibe la ban moi hon va tu dong copy de file cu tu Kibe ve Git Deploy!
3. Hau qua:
   - Ban commit Git bi dirty revert ngam ma khong ai hay biet.
   - Runtime Kibe tiep tuc chay code cu co logic is_success: khi co bat ky may nao fail, already_ran_today() tra ve False, kich hoat rerun o tick tiep theo va gay bao spam.

## 3. Quy Tac & Giai Phap Khac Phuc Bat Buoc
1. Khoi phuc ban Git chuan (Single Source of Truth):
   - Khi phat hien watchdog bi spam lai du da fix, kiem tra ngay git diff tren file watchdog.
   - Chay git checkout de discard ban de ban.
2. Va co --force trong cron_sync_watchdog.py:
   - Khi co co force=True, Deploy BAT BUOC co quyen luc toi cao ghi de len Kibe va OneDrive bat chap dst_mtime:
     if dst_mtime > src_mtime + MTIME_TOLERANCE_S and not force: return 'skipped'
3. Quy trinh Closeout sau khi sua Cron Watchdog:
   - BAT BUOC chay cron_sync_watchdog.py --force ngay sau khi sua va kiem tra git status phai sach.
   - Sau khi sync, kiem tra hash SHA256 giua Deploy, Kibe runtime va OneDrive phai khop 100%.
