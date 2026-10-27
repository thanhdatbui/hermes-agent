# Bay Revert Ngam Cua Co Che Cron Sync 2 Chieu & Clobber Timestamp (27/10/2026)

## 1. Hien Tuong Thuc Te
- Nguoi dung hoac agent da sua loi watchdog trong session truoc va commit Git thanh cong (vi du commit 9fdf62327: sua already_ran_today chi check last_2fa_date == today_str, bo dieu kien and is_success).
- Tuy nhien den ca chay tiep theo, watchdog van bi lap tin nhan va spam Telegram y het nhu chua he duoc fix.
- Khi kiem tra git status tren repo Hermes, file script vua sua lai o trang thai M (Modified) va git diff cho thay toan bo code sua da bi bien mat, dao nguoc lai dung doan code loi truoc do.

## 2. Nguyen Nhan Goc Re (Root Cause)
1. Kien truc 3 vi tri luu tru script tren Farm:
   - Git Deploy (Source of Truth): deploy/hermes-home/scripts/
   - Local Runtime Scripts: thu muc scripts runtime cuc bo
   - OneDrive Shared: thu muc hermes-cron/scripts tren OneDrive
2. Co che so khop mtime cua cron_sync_watchdog.py:
   - Script chay ngam moi 15 phut, duyet ca 2 chieu:
     * DEPLOY -> RUNTIME / OneDrive
     * RUNTIME -> DEPLOY / OneDrive (voi gia dinh "runtime sua nong moi hon thi day nguoc ve").
3. Cam bay OneDrive Clobber Timestamp:
   - Khi commit Git dien ra (vi du 13:30), file trong DEPLOY co timestamp 13:30.
   - Neu session ket thuc (turn limit / crash) truoc khi kip chay lenh dong bo, file o Runtime va OneDrive van la ban cu.
   - Trong qua trinh hoat dong, dich vu OneDrive hoac he dieu hanh cham vao file trong Runtime/OneDrive, day mtime len thoi diem muon hon (vi du 17:39).
   - O lan tick tiep theo, cron_sync_watchdog.py so sanh mtime:
     * Chieu DEPLOY -> RUNTIME: Thay RUNTIME (17:39) > DEPLOY (13:30) => BO QUA (skipped), ke ca khi co co --force neu sync_file khong kiem tra force truoc mtime.
     * Chieu RUNTIME -> DEPLOY: Thay RUNTIME (17:39) > DEPLOY (13:30) => TU DONG COPY BAN CU TU RUNTIME DE NGUOC VAO REPO GIT DEPLOY!
   - Ket qua: Code trong Git bi dirty revert ve ban cu, ca chay toi tiep tuc chay code cu bi loi va spam Telegram.

## 3. Quy Tac & Giai Phap Bat Buoc

1. Va cung sync_file() trong cron_sync_watchdog.py:
   - Khi co co --force, sync_file BAT BUOC thuc hien copy nguyen tu (_atomic_copy) ngay lap tuc ma khong xet mtime.
   - Chieu DEPLOY -> RUNTIME & OneDrive phai luon uu tien neu co xung dot, tuyet doi khong de file runtime tu dong ghi de lam ban Git Repository dang track.
2. Ky luat dong bo bat buoc sau khi sua Watchdog/Cron:
   - Sau bat ky thao tac sua script nao trong deploy/hermes-home/scripts/, Coordinator/Worker BAT BUOCO chay ngay:
     python cron_sync_watchdog.py --force
   - Hau kiem: Chay git status --short de dam bao file deploy sach va _same_content dat 100% tren ca 3 thu muc.
3. Khi gap phan anh "Tao fix o session truoc roi ma sao van bi":
   - Buoc 1: git status --short kiem tra xem file co dang bi modified ngam khong.
   - Buoc 2: git log -p -n 1 -- <file> xem commit truoc da co noi dung gi.
   - Buoc 3: Neu working tree dang dirty dao nguoc commit cu, dung git checkout <file> phuc hoi ngay, sau do chay cron_sync_watchdog.py --force.
