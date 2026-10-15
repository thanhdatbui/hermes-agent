# Chuan Hoa Toan Dien Kenh (Avatar - Hashtag - Pin) & Co Che Khoa Kep

## 1. Quy Trinh Tu Dong Doi Soat 3 Tieu Chi Khi Nhan Lenh Chuan Hoa
Khi nhan lenh "chuan hoa kenh <anh/ten>", Agent BAT BUOC kiem tra dong thoi ca 3 muc:

1. **Avatar (Ava):**
   - Soi profile TikTok thuc te vs noi dung video thuc te cua kenh vs file trong kho (`D:\video goc\<F_src>\avatar.jpg` va `D:\TIKTOK-videonuoinick\<F_out>\avatar.jpg`).
   - Kiem tra xem anh tren profile co dung chinh chu khong (phat hien bay: avatar mac dinh, anh tinh do vat, anh dong vat/meo tren kenh nguoi).
   - Kiem tra co lock trong `manual_avatar_protected_folders.json` va file marker `.manual_avatar_locked`.
   - Canh bao bay: Neu cot `Avatar` trong `Tik<Slot>.xlsx` ghi san `OK` nhung thuc te tren may chua doi, tool watchdog se bo qua -> Phai reset ve PENDING hoac chay force runner.

2. **Hashtag & Niche:**
   - Soi luoi thumbnail video cua kenh de xac dinh chu de that (vi du: Thieu nhi / Gia dinh / Me & Be).
   - So sanh voi `Keyword Video` va `Hashtag Pool` trong `Tik<Slot>.xlsx`.
   - Phat hien hien tuong lech Niche (Niche Drift) va chuan hoa dong bo sang dung chu de.

3. **Pin (Ghim Top Video):**
   - Doc luot xem cua tat ca video tren profile.
   - Tim cac video co luot xem cao vuot troi (>= 1.000 views) nhung chua co huy hieu "Da ghim".
   - Tu dong ghim toi da 2-3 clip top view len dau trang ca nhan qua `pin_top_videos.py`.

---

## 2. Co Che Khoa Kep Chong Can Thiep Tu Dong (Dual Lock Mechanism)

Khi mot kenh duoc can thiep thu cong hoac chuan hoa theo yeu cau, BAT BUOC thiet lap co khoa de cac script quet tu dong hang loat khong ghi de:

### A. Khoa Avatar (3 Tang):
1. **SSOT Registry JSON:** Dang ky ca F_out va F_src vao `protected_folders` va `accounts` trong CA HAI file:
   - `D:\Taadaa\data\manual_avatar_protected_folders.json`
   - `D:\Taadaa\Tiktok-video\data\manual_avatar_protected_folders.json`
   - Bat buoc doi soat kep de `validate_registry_integrity() == True`.
2. **Marker Vat Ly:** Tao file `.manual_avatar_locked` tai ca 4 thu muc:
   - `D:\TIKTOK-videonuoinick\<F_out>\.manual_avatar_locked`
   - `D:\video goc\<F_src>\.manual_avatar_locked`
   - `D:\video goc\<F_out>\.manual_avatar_locked`
   - `D:\TIKTOK-videonuoinick\<F_src>\.manual_avatar_locked`
3. **Hieu luc:** Tool `regenerate_unique_avatars.py` va `_make_avatar.py` goi `is_folder_avatar_protected()` se tra ve `True` va bo qua (`SKIPPED_MANUAL_PROTECTED`), khong tao lai anh.

### B. Khoa Hashtag / Niche:
1. **File SSOT:** `D:\Taadaa\data\manual_hashtag_protected_folders.json` chua danh sach `protected_folders` va metadata tai khoan da chot niche thu cong.
2. **Cron Guard:** `sync_all_tik_keywords.py` kiem tra `is_folder_hashtag_protected(f_src)`:
   - Neu thu muc nguon nam trong danh sach khoa -> Bo qua khong cap nhat `Keyword Video` va `Hashtag Pool`.
   - Giup bao ve gia tri da chinh tay khong bi cronjob quet 15 phut ghi de nhan cu tu co so du lieu trung tam.
3. **Cap nhat Workbook:** Dong bo ca 2 sheet trong `Tik<Slot>.xlsx`:
   - Sheet `TaiKhoan`: Cot `Keyword Video` va `Hashtag Pool`.
   - Sheet `Hashtag theo Folder`: Dong co `Folder Nguon = F_src`.

---

## 3. Pitfall: Khoi Dong TikTok Tren Samsung S7 / Android 7 Cho Tool Pin
- **Loi:** Lenh `am start -n com.ss.android.ugc.trill/.MainActivity` bi TikTok v47.0.3 tu choi intent explicit khi may dang o Launcher, dan den app khong len man hinh va `open_profile_root` bao loi `PROFILE_ROOT_NOT_CONFIRMED`.
- **Khac phuc chuan Farm Invariant:** Dung monkey launcher:
  ```python
  execute_adb_cmd(serial, ["shell", "monkey", "-p", "com.ss.android.ugc.trill", "-c", "android.intent.category.LAUNCHER", "1"])
  time.sleep(8.0)
  ad.tap_profile() # Tap vao toa do Profile (970, 1850) de roi Splash/Feed vao Profile
  ```
