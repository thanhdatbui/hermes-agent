# Database-Driven Avatar Audit & Autonomous Raw Video Face Extraction Pipeline

## 1. Boi Canh & Nhu Cau Van Hanh
Tren Farm quy mo lon (160 may, 1.280 accounts), rat nhieu tai khoan dang bi tinh trang **Avatar Loi / Rac**:
- Avatar la do vat vo tri, co khi, may moc (vi du: ong giam xoc xe may, mat da granite, mat ban).
- Avatar la poster, logo cao tu YouTube, hoac tranh chu 3D che kin mat.
- Avatar lech niche hoac anh chup vo hat, thieu sang, khong nhan dien duoc nguoi that.
- Kiem tra thu cong bang cach mo tung dien thoai vua ton pin, nghen bus USB, vua lam nong may va co nguy co vang phien TikTok.

## 2. Kien Truc 3 Pha Tu Dong Hoa (Zero-Touch Phone Pipeline)

```
[Tracker Database & Authority Video Store]
          |
          v (Pha 1: Quet DB & Thu Muc Video Goc)
[Phat Hien Avatar Rac / No Face / Text Banner]
          |
          v (Pha 2: Dao Clip Goc 1.mp4, 2.mp4)
[Trich Xuat Frame -> HaarCascade / Vision LLM -> Score -> Crop 512x512]
          |
          v (Pha 3: Khoa Bao Ve & Dua Vao Hang Doi)
[.manual_avatar_locked + Protected Avatar Folders Registry]
          |
          v
[avatar_replace_queue (status='PENDING') -> post_evening_avatar_watchdog.py]
```

## 3. Chi Tiet Thuc Thi Ky Thuat

### Pha 1: Quet Database & Tham Dinh File Avatar Hien Tai
- Truy van `avatar_replace_queue` va `snapshots` trong database tracker de lay danh sach cap `(may, tik, username, folder_video, video_goc)`.
- Doc file `avatar.jpg` tai thu muc video goc `D:/video goc/<folder_raw>/avatar.jpg`.
- Chay bo phan loai (OpenCV `haarcascade_frontalface_default.xml` hoac Multimodal Vision LLM qua OmniRoute proxy port 20129):
  * **HOP LE (VALID):** Nhan dien khuon mat nguoi ro rang, chiem >= 15% dien tich anh, do sac net Laplacian >= 100, khong co text banner lon.
  * **LOI RAC (INVALID):** Khong tim thay khuon mat (do vat, phong canh, logo), file loi/thieu, hoac bi chu che kin.

### Pha 2: Trich Xuat & Tu Dong Sinh Avatar Moi Tu Clip Goc
Voi cac folder bi gan co `INVALID`:
1. Mo cac clip dau tien (`1.mp4`, `2.mp4`) trong `D:/video goc/<folder_raw>/`.
2. Lay mau khung hinh tu 1.0s den 10.0s (moi 0.5s hoac 1.0s).
3. Phat hien khuon mat (`faces = cascade.detectMultiScale(gray, 1.2, 4, minSize=(90, 90))`).
4. Cham diem do net va kich thuoc khuon mat:
   Score = (w * h) * sqrt(max(Laplacian_variance, 1.0))
5. Chon khung hinh co diem so cao nhat (`best_candidate`).
6. Crop vuong tam mat ty le chuan voi khoang trong tren dinh dau (headroom):
   - `crop_dim = int(max(w, h) * 2.2)`
   - `cy = y + int(h * 0.45)`
   - `y1 = y - int(crop_dim * 0.35)`
   - Resize ve `(512, 512)` bang noi suy `cv2.INTER_LANCZOS4`.
7. Xuat file anh moi:
   - `D:/video goc/<folder>/avatar.jpg` (anh vuong chuan).
   - Tao circle preview (ban kinh R=256, vien xanh, lam toi 75% vung ngoai) de kiem dinh thi giac.

### Pha 3: Khoa Cung & Ban Giao Cho Watchdog Ca Toi
1. **Cam co vat ly chong ghi de:** Tao file rong `.manual_avatar_locked` tai ca kho video goc va video render:
   - `D:/video goc/<folder>/.manual_avatar_locked`
   - `D:/TIKTOK-videonuoinick/<folder_render>/.manual_avatar_locked`
2. **Cap nhat Registry bao ve:** Ghi danh `folder` vao file registry protected avatar folders.
3. **Dua vao hang doi tu dong:**
   - Cap nhat bang `avatar_replace_queue` trong tracker database:
     `UPDATE avatar_replace_queue SET status='PENDING' WHERE may=? AND tik=?`
   - Cap nhat cot `Avatar` tren cac file Excel (`Tik1..8.xlsx`) thanh `PENDING`.
4. **Van hanh khong cham:** Con watchdog `post_evening_avatar_watchdog.py` (chay moi toi 21:00 -> 23:45) se tu dong kich hoat `run_tiktok_upload_avatar.ps1` de nap avatar chuan len may that.
