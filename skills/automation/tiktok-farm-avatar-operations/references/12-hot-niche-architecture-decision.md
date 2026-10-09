# 12 Hot Niche Architecture Decision (Chốt 2026-10-06)

## Nguồn quyết định
Sol Advisor (:20129) đã review độc lập và xác nhận: **5 niche là KHÔNG ĐỦ** cho farm 1.280 account. Tối ưu là **12-15 niche** để tránh nguồn chạm đáy và giảm cluster fingerprint.

## Lý do loại bỏ 5 niche

| Vấn đề | Hệ quả |
|---|---|
| Mỗi niche gánh ~250 folder | Cần 250 kênh độc quyền ≥ 40 clips / 1 ngách — rất nhanh cạn nguồn sạch |
| Invariant 1 folder = 1 channel | Không chia sẻ được video giữa các folder → áp lực 45.000 clip unique / 5 niche |
| TikTok cluster detection | 250 acc cùng 1 network, cùng format, cùng niche → AI gắn cờ industrial farm |

## Bảng 12 Cụm Niche Hot chốt lần cuối

| STT | Slug | Label | Đặc điểm |
|---|---|---|---|
| 1 | `gaixinh_vn` | Gái xinh VN | Nữ sinh VN đời thường, cafe, outfit, vlog — KHÔNG tiếng Trung |
| 2 | `douyin_beauty` | Douyin Biến hình | Visual aesthetic, biến hình, thuần nhạc — KHÔNG giọng nói tiếng Trung |
| 3 | `thucung` | Thú cưng cute | Chó mèo hài hước, cute, cứu trợ |
| 4 | `amthuc` | Món ngon đường phố | Street food, nấu ăn cuốn hút |
| 5 | `cuoi` | Tiểu phẩm hài hước | Tình huống vui, troll, giải trí ngắn |
| 6 | `satisfying` | Mẹo vặt & Satisfying | Phục hồi đồ cũ, dọn dẹp mãn nhãn, ASMR |
| 7 | `kienthuc_viral` | Sự thật bất ngờ | Top điều kỳ lạ, lịch sử sốc, fact lạ (KHÔNG khô hàn lâm) |
| 8 | `dulich` | Cảnh đẹp du lịch | Check-in, cảnh đẹp VN, travel |
| 9 | `xe` | Siêu xe & Xe đẹp | Siêu xe, độ xe, car lifestyle |
| 10 | `gym_fit` | Fitness & Vóc dáng | Before-after, gym motivation, giảm cân |
| 11 | `banhngot` | Làm bánh ngọt | Quy trình làm bánh, visual đồ ngọt nét |
| 12 | `anime_clip` | Anime Edit | Hoạt hình edit visual cao, nhạc bắt tai |

## Ngách cũ bị loại (Khó Viral — CẤM gán cho acc mới)

Các slug trong `KHO_VIRAL`:
`laptrinh`, `kienthuc` (hàn lâm), `khoahoc`, `thuvien`, `sach`, `congviec`, `noithat`, `giaothong`, `thietbi`, `marketing`, `taichinh`, `nghenghiep`, `ngoaingu`, `hoctap`, `kynangsong`, `phattrienbanthan`, `thien`, `tamly`, `dongluc`, `truyencamhung`, `thoiquen`, `khampha` (chung chung), `chamsocsuckhoe`, `suckhoe`, `chamsocbe`, `nha`, `vantay`, `dochai`, `sukien`

## INVARIANT: gaixinh_vn ≠ douyin_beauty (BẮT BUỘC TÁCH)

| | `gaixinh_vn` | `douyin_beauty` |
|---|---|---|
| Content | Gái Việt Nam đời thường, nội địa | Visual cinematic, biến hình, aesthetic Douyin |
| Ngôn ngữ | Tiếng Việt / im lặng | Nhạc nền không lời, thuần nhạc |
| Nguồn | Kênh TikTok / YouTube VN | Kênh Douyin được re-up |
| Watermark | Không có | Được phép Douyin watermark nếu clip đẹp |
| Audience graph | Theo dõi nữ VN, comment tiếng Việt | View satisfaction, không cần hiểu ngôn ngữ |

**Trộn 2 niche này vào 1 folder = loãng audience graph**, TikTok khó phân loại để phân phối đúng tệp.

## Quy trình Migrate Niche (đã chạy thành công 2026-10-06)

Các bước tuần tự để chuyển folder từ niche cũ sang niche hot mới:

1. **Xác định target folders**: Đọc workbook Excel (`Tik7.xlsx`, `Tik8.xlsx` Kibe; `Tik1..8.xlsx` Admin), lọc `slug in KHO_VIRAL` + (Admin: `posted <= 1`).
2. **Dọn media cũ**: Xóa sạch `.mp4`, `.part`, `.ytdl`, `avatar.jpg`, `channel_info.json` ở cả 2 đầu kho (`video goc/` và `TIKTOK-videonuoinick/`). **KHÔNG giữ lại avatar cũ**.
3. **Gán niche mới**: Cập nhật cột `Keyword Video` (col 6) và `Hashtag Pool` (col 7) trong workbook. Xoay tua 12 cụm niche theo index `i % 12`.
4. **Reset state.db**: `UPDATE folders SET niche=?, status='pending', video_count=0, source_channel=NULL WHERE folder_num=?`. Kibe: `C:\CodexRuntime\tiktok-video\state.db`. Admin: `D:\CodexRuntime\tiktok-video-machine2\state.db`.
5. **Đánh dấu avatar queue**: Insert/upsert vào `avatar_replace_queue` với `status='PENDING'`. PK là `(username, tik, host_id)` — ON CONFLICT phải match đúng 3 cột này, không phải `ON CONFLICT(username)`.
6. **Tải video mới**: Downloader tự nhặt folder `status='pending'` và cào nguồn kênh phù hợp niche mới.
7. **Tạo avatar MỚI sau khi tải xong**: Trích frame từ video mới (seek 3.0–11.0s, crop 512×512), đồng bộ `avatar.jpg` vào cả 2 đầu kho, reset queue `PENDING`.

## Pitfalls phát hiện trong session này

### P1: `ON CONFLICT` phải khớp PK thực tế
Bảng `avatar_replace_queue` có PK phức hợp `(username, tik, host_id)`. Câu `ON CONFLICT(username)` gây `OperationalError: ON CONFLICT clause does not match any PRIMARY KEY or UNIQUE constraint`. Kiểm tra bằng `PRAGMA table_info()` trước khi viết upsert.

### P2: Admin state.db nằm ở path khác Kibe
- Kibe: `C:\CodexRuntime\tiktok-video\state.db`
- Admin: `D:\CodexRuntime\tiktok-video-machine2\state.db` (KHÔNG phải `D:\CodexRuntime\tiktok-video\state.db`)

### P3: openpyxl `data_only=True` khi READ nhưng cần `load_workbook(path)` (không `data_only`) khi WRITE
Đọc với `data_only=True` trả cached value. Ghi thì mở không có flag này, save lại. Hai thao tác phải dùng 2 lần open riêng.

### P4: "Khám phá" trong Admin Tik8 bị dùng sai (57 rows)
Ngách `Khám phá` (chung chung, không viral) bị gán hàng loạt vào slot mặc định khi khởi tạo template Admin Tik8. Phải scan thêm riêng bằng `if 'khám phá' in label.lower()` sau khi chạy migration chính.

### P5: Slug mới cần đăng ký vào niches_pool.txt
Các slug mới (`gaixinh_vn`, `douyin_beauty`, `kienthuc_viral`, `xe`, `gym_fit`, `anime_clip`) phải được thêm vào `D:\\Taadaa\\Tiktok-video\\data\\niches_pool.txt` và sync lên Admin farm (`scp ... admin-farm:...`), nếu không `sync_all_tik_keywords.py` sẽ không nhận diện được.

### P6: Admin downloader tự thoát sau 1 vòng quét — phải re-launch thủ công
Script `run_admin_clean_vn_downloader.py` chạy **một vòng tuần tự** 591 folder rồi thoát (`exit 0`). Nó KHÔNG tự lặp vòng lặp vô hạn. Sau khi dọn niche cũ và đổi sang niche hot mới, state.db Admin có nhiều folder mới `status='pending'` nhưng downloader đã dừng từ trước → Task Manager chỉ còn Gateway process. Phải re-launch bằng:
```
ssh admin-farm "wmic process call create \"cmd /c python D:/Taadaa/Tiktok-video/scripts/run_admin_clean_vn_downloader.py >> D:/Taadaa/Tiktok-video/admin_downloader_live.log 2>&1\""
```
Xác nhận bằng cách poll log 10–15s sau khi launch để kiểm tra dòng `[1/N] Đang xử lý Folder`.

### P7: `wmic process call create` là cách duy nhất reliable để spawn detached process qua SSH trên Admin
- `Start-Process -WindowStyle Hidden`: Process bị kill ngay khi SSH session kết thúc (không thực sự detached).
- `ssh admin-farm "python script.py"` foreground: Treo SSH session, bị timeout.
- **Chuẩn xác:** `wmic process call create "cmd /c python script.py >> log.log 2>&1"` tạo process gắn vào Session 0 của Windows, không chết khi SSH thoát. Kiểm tra bằng `wmic process where "name='python.exe'" get ProcessId,CommandLine`.

### P8: Render chain Admin bỏ qua folder khi thư mục source trống (0 MP4)
`admin_render_chain.py` kiểm tra `len(os.listdir(source_path)) > 0` trước khi render. Nếu dọn sạch video cũ (để thay niche) nhưng downloader chưa kịp nạp video mới, render chain log ra dòng `SKIP machine X: source Y has only 0 MP4` rồi kết thúc sớm với `"Khong co target can xu ly"`. Sequence đúng: **Đợi downloader đủ ≥ 40 clip vào folder → mới re-launch render chain**. Không cần re-launch render chain ngay sau khi dọn.

### P9: Kibe state.db có 2 bản song song — phải sync 2 chiều sau khi cập nhật niche
Kibe có 2 state.db:
- `C:\\CodexRuntime\\tiktok-video\\state.db` — bản chính (primary, NVMe nhanh)
- `D:\\CodexRuntime\\tiktok-video\\state.db` — bản mirror (HDD fallback)

Khi migrate niche script chỉ cập nhật `C:`, cần sync sang `D:` bằng lệnh Python đọc từ C: rồi `UPDATE` sang D:. Nếu script auto-rescan của farm đọc nhầm file D: cũ, nó sẽ không nhận diện được các folder pending mới.

```python
# Sync pending rows from C: to D:
src = sqlite3.connect("C:/CodexRuntime/tiktok-video/state.db")
tgt = sqlite3.connect("D:/CodexRuntime/tiktok-video/state.db")
rows = src.execute("SELECT folder_num, niche, status, video_count FROM folders WHERE status='pending'").fetchall()
for f, n, s, v in rows:
    tgt.execute("UPDATE folders SET niche=?, status=?, video_count=0, source_channel=NULL WHERE folder_num=?", (n, s, f))
tgt.commit()
```
