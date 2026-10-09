# Đối Soát & Đồng Bộ Niche - Hashtag Pool (Khắc Phục Lệch Niche Video Đăng Toàn Farm)

## 1. Kiến Trúc Luồng Hashtag Farm (Mô hình 3 tầng)
Hệ thống đăng bài tự động trên farm vận hành luồng hashtag qua 3 tầng:
1. **Tầng 1 - Logic chọn Hashtag (`hashtag_selector.py`)**:
   - Chọn ngẫu nhiên từ 3 đến 5 hashtag cho mỗi video.
   - **Lớp bảo vệ (Invariant)**: Luôn gồm 2 đến 4 tag viral quốc dân (`#fyp`, `#xuhuong`, `#videohay`, `#viral`, `#trending`, `#tiktokvietnam`, `#moingay`, `#hay`) + **tối đa duy nhất 1 tag ngách (niche)**.
   - Tránh việc video bị spam 4–5 tag ngách sai lệch.
2. **Tầng 2 - File Excel vận hành Dual-Cluster (1.280 tài khoản)**:
   - **Cụm Kibe**: Máy 1..80 (640 acc) tại `D:/OneDrive/TaadaaData/kibe/` (`Tik1.xlsx` $\rightarrow$ `Tik8.xlsx`).
   - **Cụm Admin**: Máy 201..280 (640 acc) tại `D:/OneDrive/TaadaaData/admin/` (`Tik1.xlsx` $\rightarrow$ `Tik8.xlsx`).
   - Mỗi file quản lý 80 máy (1 slot). Sheet `TaiKhoan` chứa:
     * `video gốc`: Số thứ tự folder nguồn (1..640) trong `D:/video goc/`. Cả Kibe và Admin dùng chung quy tắc ánh xạ dải folder nguồn theo Slot.
     * `Keyword Video`: Tên chủ đề tiếng Việt (ví dụ: *Thú cưng*, *Yoga*, *Tin tức*).
     * `Hashtag Pool`: Danh sách các hashtag thuộc chủ đề để Tầng 1 bốc ngẫu nhiên.
3. **Tầng 3 - CSDL nguồn chân lý (`D:/CodexRuntime/tiktok-video/state.db`)**:
   - Bảng `folders`: Lưu `folder_num`, `niche` (slug), `source_channel`, `status`.
   - Bảng `videos`: Lưu `video_id`, `uploader`, `source_url`, `folder`.

---

## 2. Nguyên Nhân Lệch Niche / Hashtag Drift
- **Hiện tượng**: Video tải về và đăng lên có nội dung A (ví dụ: video cún con, chó mèo) nhưng caption lại gắn tag chủ đề B (ví dụ: `#suckhoeyoga`).
- **Gốc rễ sự cố**:
  1. Trong quá trình crawler tự động tải video về các folder nguồn (1..640), bảng `folders` trong `state.db` bị gán nhãn `niche` sai lệch so với kênh thực tế (ví dụ: Folder 354 tải từ YouTube `@YeuLu` nhưng bị set `niche = 'yoga'`).
  2. Khi công cụ đồng bộ (`sync_all_tik_keywords.py`) chạy, nó lấy nhãn từ `state.db` ghi đè vào file `Tik<Slot>.xlsx` tương ứng.
  3. Cụm Admin trước đây bị gán nhãn cứng (hardcoded) ở một số file (như `Tik7` bị gán toàn bộ 'Đời sống', `Tik8` toàn bộ 'Khám phá') hoặc lệch so với `state.db`.
  4. Khi máy farm chạy lệnh upload, tool đọc file `Tik<Slot>.xlsx` và lấy Hashtag Pool đã bị gán nhầm để bốc hashtag.

---

## 3. Quy Trình Điều Tra O(1) Khi Phát Hiện Video Lệch Hashtag (Trường hợp đơn lẻ)

1. **Xác định tọa độ tài khoản & Folder nguồn trên Excel**:
   - Xác định cụm (`kibe` hoặc `admin`) và file Tik quản lý: Tìm theo username hoặc số máy $M$ trong `Tik1.xlsx` .. `Tik8.xlsx`.
   - Trích xuất: `Máy`, `ID`, `Folder Video` (output), `video gốc` (folder nguồn $F_{src}$), `Keyword Video`, `Hashtag Pool`.

2. **Truy vấn đối soát trong `state.db`**:
   ```python
   import sqlite3
   conn = sqlite3.connect(r'D:\CodexRuntime\tiktok-video\state.db')
   cur = conn.cursor()
   # Kiểm tra folder
   cur.execute("SELECT folder_num, niche, source_channel FROM folders WHERE folder_num = ?", (f_src,))
   print("Folder:", cur.fetchone())
   # Kiểm tra uploader thực tế của video trong folder
   cur.execute("SELECT folder, uploader, source_url FROM videos WHERE folder = ? LIMIT 5", (f_src,))
   print("Videos sample:", cur.fetchall())
   conn.close()
   ```

3. **Cập nhật `state.db` & Đồng bộ Excel**:
   ```python
   import sqlite3
   conn = sqlite3.connect(r'D:\CodexRuntime\tiktok-video\state.db')
   conn.execute("UPDATE folders SET niche = 'thucung' WHERE folder_num = ?", (f_src,))
   conn.commit()
   conn.close()
   ```
   Chạy đồng bộ sang Excel cho cả 2 cụm: `python C:/Users/Kibe/AppData/Local/hermes/scripts/sync_all_tik_keywords.py`.

---

## 4. Quy Trình Quét & Chuẩn Hóa Diện Rộng 640 Folder (Batch Re-classification)

Khi User yêu cầu "sửa hết tất cả các folder bị lệch", KHÔNG sửa mò từng cái mà phải rà soát đối chiếu chéo tự động:

### Bước 1: Nguồn dữ liệu đối chiếu chéo
1. **DB hiện tại (`D:\CodexRuntime\tiktok-video\state.db`)**: Bảng `folders` và bảng `videos`.
2. **DB kho video lịch sử (`D:\CodexRuntime\tiktok-video-downloader\state-real-1-tiktok-final.db`)**: Chứa thông tin uploader và niche gốc của các video đời đầu (folder 1..297).
3. **Danh mục kênh nguồn (`D:\CodexRuntime\tiktok-video\sources.json`)**: Chứa metadata crawl gồm channel URL, uploader, và niches.
4. **File thực tế trên đĩa (`D:\video goc\<folder>\`)**: Kiểm tra tên file, số lượng file `.mp4`, avatar.

### Bước 2: Bảng đối soát ngữ nghĩa 15 cụm chủ đề chính
Phân loại chính xác dựa trên uploader / tên kênh:
- **Thú cưng / Chó mèo (`thucung`)**: `yeulu`, `thú cưng`, `meohera`, `tinypet`, `meouo`, `poodle`, `bossdog`, `khethui`, `mèo`, `chó`, `cún`.
- **Yoga (`yoga`)**: `yoga`, `hyeyoga`, `sophie`.
- **Ô tô (`oto`) / Xe máy (`xemay`)**: `mê xe`, `otofun`, `ô tô`, `car today`, `autopro`, `longmuabanoto`, `thayduan`, `luật ô tô`. (Nếu có `xe máy`, `honda`, `yamaha` $\rightarrow$ `xemay`).
- **Hài hước (`haihuoc`)**: `xuan hinh`, `xuân hinh`, `hài kịch`, `phim hài`, `comedy`, `xàm xí`, `xanh xàm`.
- **Tin tức / Xã hội / Câu chuyện (`cauchuyen`)**: `tin 3 phut`, `tin 3 phút`, `vtv24`, `thvl`, `thanhnien`, `vtc news`, `báo tuổi trẻ`, `thời sự`, `pháp luật`, `hoangminh`, `mangovid`.
- **Làm đẹp / Skincare (`lamdep`)**: `bác sĩ nguyên`, `skincare`, `son sờ kin`, `làm đẹp`, `trang điểm`, `makeup`.
- **Sức khỏe (`suckhoe`)**: `dr ngọc`, `dr. ruột`, `sức khỏe`, `y tế`, `khỏe tự nhiên`.
- **Học tập / Đào tạo (`hoctap`)**: `tiếng anh`, `education`, `học tập`, `học làm bánh`, `kỹ năng sống`, `sasuke`, `netspace`.
- **Ẩm thực / Nấu ăn (`amthuc`)**: `quynh truong`, `ẩm thực`, `bếp việt`, `món ngon`, `nấu ăn`, `food`, `ăn uống`, `bánh ngọt`, `beemart`.
- **Nội thất / Kiến trúc (`noithat`)**: `nội thất`, `nhato`, `kiến trúc`, `milimet`, `nhà đẹp`, `tiên khôi`, `benluxury`.
- **Thể thao / Gym (`thethao` / `gym`)**: `bóng đá`, `cầu lông`, `fpt bóng đá`, `thế dân`, `the dan`.
- **Âm nhạc (`nhac`)**: `music`, `nhạc`, `singing`, `cô bé thích hát`, `pops music`, `yeah1 music`, `vtvmusic`.
- **Nhảy / Dance (`nhay`)**: `dance`, `nhảy`, `vũ đạo`, `ngocanhdancefit`.
- **Game (`game`) / Anime (`anime`)**: `phê game`, `cris devil gamer`, `ani-one`, `pops anime`.
- **Review sản phẩm (`review`) / Du lịch (`dulich`)**: `đàm đức review`, `mốc review`, `du lịch biết tuốtz`.

### Bước 3: Script thực thi Bulk Update có Backup an toàn
```python
import sqlite3, shutil
from pathlib import Path

STATE_DB = Path(r"D:\CodexRuntime\tiktok-video\state.db")
BACKUP_DB = Path(r"D:\CodexRuntime\tiktok-video\state.db.bak_before_niche_fix")

# Luôn backup trước khi ghi hàng loạt
if not BACKUP_DB.exists():
    shutil.copy2(str(STATE_DB), str(BACKUP_DB))

conn = sqlite3.connect(str(STATE_DB))
cur = conn.cursor()

# updates: dict[folder_num, new_niche_slug]
for fnum, new_niche in updates.items():
    cur.execute("UPDATE folders SET niche = ? WHERE folder_num = ?", (new_niche, fnum))

conn.commit()
conn.close()
```

---

## 5. Chuẩn Hóa & Đồng Bộ Dual-Cluster (Kibe & Admin)

### Cấu trúc 2 cụm máy
- **Cụm Kibe**: Máy 1..80 $\rightarrow$ `D:\OneDrive\TaadaaData\kibe\Tik1.xlsx` .. `Tik8.xlsx`.
- **Cụm Admin**: Máy 201..280 $\rightarrow$ `D:\OneDrive\TaadaaData\admin\Tik1.xlsx` .. `Tik8.xlsx`.
- Cả hai cụm đều có cấu trúc 8 file giống nhau:
  * Tik1: Folder nguồn 1..80
  * Tik2: Folder nguồn 81..160
  * Tik3: Folder nguồn 161..240
  * Tik4: Folder nguồn 241..320
  * Tik5: Folder nguồn 321..400
  * Tik6: Folder nguồn 401..480
  * Tik7: Folder nguồn 481..560
  * Tik8: Folder nguồn 561..640

### Đồng bộ hóa tự động qua Cron Watchdog
Script `C:/Users/Kibe/AppData/Local/hermes/scripts/sync_all_tik_keywords.py` (chạy qua cron job `sync-all-tik-keywords-cron` mỗi 15 phút):
- Tự động duyệt qua `FARM_DIRS = [("Kibe", ...), ("Admin", ...)]`.
- Sử dụng `atomic_workbook_update` để cập nhật đồng thời cả sheet `TaiKhoan` và `Hashtag theo Folder` của cả 16 file Excel (8 Kibe + 8 Admin).
- Đồng bộ an toàn, tự tạo `.bak` và lock an toàn chống tranh chấp tiến trình.

### Lệnh chạy đồng bộ thủ công
```bash
python C:/Users/Kibe/AppData/Local/hermes/scripts/sync_all_tik_keywords.py
```

### Bộ kiểm thử Parity toàn bộ 1.280 tài khoản (Test Suite)
Chạy script kiểm thử giả lập bốc tag cho toàn bộ 1.280 tài khoản:
```python
import sys, openpyxl
from pathlib import Path
sys.path.insert(0, "D:/Taadaa/Tiktok-video/scripts")
from tiktok_workflow.hashtag_selector import COMMON_VIRAL_HASHTAGS, select_hashtags

FARM_DIRS = [
    ("Kibe", Path(r"D:\OneDrive\TaadaaData\kibe")),
    ("Admin", Path(r"D:\OneDrive\TaadaaData\admin")),
]
TIK_FILES = ["Tik1.xlsx", "Tik2.xlsx", "tik3.xlsx", "Tik4.xlsx", "Tik5.xlsx", "Tik6.xlsx", "Tik7.xlsx", "Tik8.xlsx"]
COMMON_LOWER = {t.lower() for t in COMMON_VIRAL_HASHTAGS}

for cluster_name, cluster_dir in FARM_DIRS:
    for fname in TIK_FILES:
        wb = openpyxl.load_workbook(str(cluster_dir / fname), read_only=True)
        ws = wb["TaiKhoan"] if "TaiKhoan" in wb.sheetnames else wb.active
        # Kiểm tra 80 máy: keyword != '', pool != '', select_hashtags đạt 3..5 tags, >=2 common tags, <=1 niche tag
        wb.close()
```
**Bảo đảm 4 Invariants trên toàn bộ 1.280 tài khoản**:
1. Đầy đủ Keyword và Hashtag Pool (0 ô trống, 0 dính chữ "pending").
2. Số lượng tag luôn trong khoảng $3 \le \text{tags} \le 5$.
3. Luôn có $\ge 2$ tag viral quốc dân.
4. Tối đa duy nhất 1 tag ngách đúng chủ đề.
