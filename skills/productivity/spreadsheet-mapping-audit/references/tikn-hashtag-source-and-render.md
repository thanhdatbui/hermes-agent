# Hashtag/keyword, video-gốc, và render TikN — mapping thực tế (2026-08-11)

## Bài học chính: hashtag theo NICHE CỦA FOLDER NGUỒN, không theo máy

User sửa thẳng: "Bậy. Sao lại lấy theo máy. Lấy theo keyword tải folder nguồn chứ?"
→ Mỗi folder nguồn (`D:\video goc\<N>`) được tải theo một niche riêng. `Keyword Video`
và `Hashtag Pool` của dòng TikN phải khớp niche của **folder nguồn** mà dòng đó render,
KHÔNG được copy theo máy (Tik1 của máy 1 = "Yêu thú cưng" nhưng Tik2 cùng máy 1 =
"Khoa học" vì folder 81 = `khoahoc`).

## Nguồn sự thật cho niche (theo thứ tự ưu tiên)

1. **DB downloader**: `D:\CodexRuntime\tiktok-video-downloader\state-real-1-tiktok-final.db`,
   bảng `folders` (`folder_num` -> `niche` slug). Đây là mapping gốc folder→niche thật
   lúc tải video (298 folder, 74 niche; dùng folder 1-240 cho Tik1/2/3).
2. **`D:\Taadaa\Tiktok-video\data\niches_pool.txt`**: slug → label tiếng Việt
   (format `group<TAB>slug<TAB>label<TAB>allow_no_speech`).
3. **Tik1 sheet "Hashtag theo Folder"**: pool hashtag chuẩn theo niche đã có
   (44 niche đầu). Niche nào đã có trong Tik1 → copy nguyên label + hashtag.
4. Niche chưa có (26 niche mới: `congnghe`, `game`, `nhac`, `kienthuc`, ...) →
   build pool: `#<slug> + extras (nếu có) + #<slug>vietnam + #<slug>moingay
   + #tiktokvietnam #xuhuong #fyp #videohay` (9-13 tag/dòng).

Ví dụ máy 74: Tik1 folder 74 = `thucung` ("Thú cưng"), Tik2 folder 154 = `cafe`
("Cà phê Việt"), Tik3 folder 234 = `game` ("Game") — ba dòng cùng máy khác niche nhau.

## Quy luật `video gốc` (cột source folder)

```
Tik1: video gốc = máy m           (1..80)
Tik2: video gốc = 80 + m          (81..160)
Tik3: video gốc = 160 + m         (161..240)
```

Pitfall: tik3 lúc mới tạo copy `video gốc` của Tik2 (81..160) — phải sửa thành 160+m.
Kiểm tra D:\video goc có đủ folder + ≥42 mp4 trước khi render.

## REG: 8 hàng/máy (restore slot 7-8)

- Backup 07/07/2026: mỗi máy **8 dòng** (đúng thiết kế gốc `(m-1)*8+1..8`).
- Đợt dọn 14/07/2026 (`backup-delete-rows-khong-trong-gmail-clean-v2`) cắt còn 6 dòng/máy.
- User yêu cầu tạo lại đủ 8: thêm 2 dòng cuối mỗi máy với `Folder Video = (m-1)*8+7, +8`,
  `device ID` copy từ block máy, các cột còn lại trống.
- Kỹ thuật: `ws.insert_rows(idx, amount=2)` chạy **từ máy 80 ngược lên 1**
  (idx = m*6+2, sau dòng cuối block) để không làm lệch chỉ số block chưa xử lý;
  verify 80×8 dòng + folder `(m-1)*8+k` sau khi replace.

## Render random TikN (launcher pattern)

- File: `run_tikN_random_render.ps1` (bản gốc `run_tik2_random_render.ps1`,
  copy đổi `$workbook`, `$Slot`). Thêm switch `-AutoRun` để bỏ `Read-Host` khi chạy ngầm.
- Gọi: `scripts\random_batch_render.py --randomize --slot <k-1> --machine-id <m-1>
  --seed-offset 0 --parallel <P> --preset presets\preset_owner.json`.
  Slot 0-based: Tik1=0, Tik2=1, Tik3=2.
- `-Parallel 1` khi CPU máy ~92%; `-Parallel 2` khi cần nhanh.
- Output: `D:\TIKTOK-videonuoinick\<Folder Video>`; source: `D:\video goc\<video gốc>`.
- Run metadata: `D:\CodexRuntime\tiktok-video\runs\tikN-kibe-m*-src*-out*/run_meta.json`
  + `render_manifest.csv` (status rendered/skipped, 45 tasks/máy).
- Tik1 = đã render + ĐÃ ĐĂNG; Tik2 = đã render chưa đăng; Tik3 = render mới → không
  nói Tik2 "kiểm chứng qua đăng" khi nó chỉ mới render.

## Watchdog báo tiến độ render (no_agent cron, silent + mốc)

Script `C:\Users\Kibe\AppData\Local\hermes\scripts\tik3_render_watchdog.py`:
- Đếm folder output `(m-1)*8+3` có ≥45 mp4 >0 bytes.
- State file `D:\CodexRuntime\tiktok-video\tik3-render-progress.json` giữ `last_reported`.
- Chỉ in thông báo khi `done >= last+10` (hoặc đủ 80) → cron `no_agent=true` deliver
  stdout verbatim; stdout rỗng = silent. Cron: `every 30m`, deliver origin.
- Mẫu báo: `✅ Tik3 render: 10/80 folder xong (máy 1-10) | đang render máy 11 (23/45)`.
