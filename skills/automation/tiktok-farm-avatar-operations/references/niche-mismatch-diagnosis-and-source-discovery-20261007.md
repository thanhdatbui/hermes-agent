# Niche Mismatch Diagnosis & Channel Source Discovery (07/10/2026)

## Root Cause: "Lúc thì gái lúc thì công nghệ"

Case study: `@ngobaoquynh29` (Máy 15 / Tik 7, Folder Video 119, Video Gốc 495).

- Excel (`Tik7.xlsx`, dòng 15): niche = **`Công nghệ`** (ngách khó viral).
- Folder `TIKTOK-videonuoinick/119`: trộn lẫn video vẽ tranh nghệ thuật + video talkshow công nghệ từ các đợt cào/swap cũ.
- Folder `video goc/495`: chứa 41 video talkshow/podcast công nghệ dài (49-115s/video, không phải Shorts chuẩn).
- Avatar: bị cắt nhầm khuôn mặt khách mời ông Tây mặc vest, dính phụ đề vietsub → hoàn toàn lệch với tên nick con gái Ngô Bảo Quỳnh.

**Chẩn đoán nhanh niche mismatch (O(1) steps):**
1. `python C:/Users/Kibe/check_channel_niche.py` → đọc từ Excel: `taikhoan[niche_col]` phải khớp với niche actual của video.
2. Xem folder `video goc/<Video Gốc>` để kiểm tra duration video (videos > 45s là talkshow/podcast, không phải Shorts viral).
3. Nếu niche label trong Excel là "Công nghệ", "Học tập", "Sức khỏe", "Câu chuyện", "Nội thất"... → đây là KHO_VIRAL (ngách cứng khó viral) → phải migrate.

---

## Quy trình Migrate Niche (Đúng Tuần Tự — Không Bỏ Bước)

```
1. DỌN SẠCH media cũ cả 3 thư mục:
   - D:/video goc/<Video Gốc>/         → xóa .mp4, .part, .jpg, .json, avatar.jpg
   - D:/video goc/<Folder Video>/      → như trên
   - D:/TIKTOK-videonuoinick/<Folder Video>/ → như trên

2. CẬP NHẬT EXCEL (Tik7.xlsx / Tik8.xlsx) dòng tài khoản:
   - Col 6 (Keyword Video): tên niche hot mới (vd: "Gái xinh VN")
   - Col 7 (Hashtag Pool): hashtag chuẩn của niche hot
   - Col 10 (Render Status): "PENDING"
   - Col 11 (Render MP4): 0
   - Col 13 (Avatar): "PENDING"

3. RESET QUEUE — DELETE (không phải PENDING) entry trong avatar_replace_queue:
   DELETE FROM avatar_replace_queue WHERE username='<username>';
   
   LÝ DO: phải DELETE chứ không phải PENDING vì nếu để PENDING,
   watchdog có thể up avatar cũ (từ file cũ còn sót) lên máy trước khi
   có video mới. Entry mới sẽ được tạo lại SAU KHI download xong.

4. CHỌN KÊNH NGUỒN MỚI (1 folder = 1 kênh, min 40-45 video):
   - Đọc gaixinh_channel_claims.json để tra trạng thái claim.
   - Đọc tiktok_sources_discovered.json (579 kênh) để tìm unclaimed.
   - Filter theo niche slug / keyword trong uploader name.
   - Ưu tiên kênh VN gaixinh_vn (không dùng douyin_beauty tiếng Trung).

5. TẢI VIDEO MỚI bằng download_single_channel_to_folder.py:
   python D:/Taadaa/Tiktok-video/scripts/download_single_channel_to_folder.py \
     --channel-url "https://www.tiktok.com/@<username>" \
     --folder <Video Gốc> \
     --min-videos 45
   
   Chạy background với terminal(background=True, notify_on_complete=True, timeout=600).

6. SAU KHI DOWNLOAD HOÀN TẤT:
   - Trích xuất avatar từ video mới (Pillow crop, O(1), tránh _make_avatar.py timeout).
   - Đồng bộ avatar vào 4 đầu kho (Folder Video + Video Gốc × 2 roots).
   - INSERT vào avatar_replace_queue với status='PENDING'.
   - Render thành phẩm vào TIKTOK-videonuoinick/<Folder Video>.
   - Claim kênh nguồn trong gaixinh_channel_claims.json.
```

---

## Source Discovery: Tìm kênh gaixinh_vn chưa claim

### Kho nguồn có sẵn:
- `D:/Taadaa/Tiktok-video/data/tiktok_sources_discovered.json` — 579 kênh TikTok đã crawl, có trường `niches`, `url`, `uploader`, `qualified_video_count`.
- `D:/Taadaa/Tiktok-video/data/gaixinh_channel_claims.json` — dict `{url: {folder, uploader}}` các kênh đã claim.
- `D:/Taadaa/Tiktok-video/data/source_manifest_gaixinh.jsonl` — manifest gaixinh nhỏ (~19 entries).

### Script kiểm tra nhanh:
```python
import json

with open('D:/Taadaa/Tiktok-video/data/tiktok_sources_discovered.json', 'r', encoding='utf-8') as f:
    disc = json.load(f)
with open('D:/Taadaa/Tiktok-video/data/gaixinh_channel_claims.json', 'r', encoding='utf-8') as f:
    claims = json.load(f)

claimed_urls = set(claims.keys())
candidates = [s for s in disc if s['url'] not in claimed_urls
              and any(k in ' '.join(s.get('niches', [])).lower() + s.get('uploader','').lower()
                     for k in ['gai', 'girl', 'beauty', 'xinh', 'outfit', 'dance', 'thoitrang'])]
print(f"Unclaimed hot-girl candidates: {len(candidates)}")
for c in candidates[:10]:
    print(" ", c['url'], c['uploader'], c['niches'], c.get('qualified_video_count'))
```

### Kiểm tra số video của 1 kênh TikTok trước khi chọn:
```python
import yt_dlp
url = "https://www.tiktok.com/@dresswithdan"
with yt_dlp.YoutubeDL({"extract_flat": True, "playlist_end": 50, "quiet": True}) as ydl:
    info = ydl.extract_info(url, download=False)
    print(len(info.get('entries', [])), "videos found")
```

### download_single_channel_to_folder.py usage:
```bash
python D:/Taadaa/Tiktok-video/scripts/download_single_channel_to_folder.py \
  --channel-url "https://www.tiktok.com/@<handle>" \
  --folder <N>           # folder goc số (vd: 495)
  --min-videos 45        # tiêu chí tối thiểu
  --output-root "D:/video goc"
  --render-root "D:/TIKTOK-videonuoinick"
  # optional: --clean-old  (đã dọn trước thì không cần)
```

Script tự động tải, lọc theo duration, báo summary. Min 45 video / kênh là tiêu chuẩn vận hành.

---

## KHO_VIRAL — Danh sách slug ngách khó viral (phải migrate)

```python
KHO_VIRAL = {
    'laptrinh', 'kienthuc', 'khoahoc', 'thuvien', 'sach', 'congviec',
    'noithat', 'giaothong', 'thietbi', 'marketing', 'taichinh',
    'nghenghiep', 'ngoaingu', 'hoctap', 'kynangsong', 'phattrienbanthan',
    'thien', 'tamly', 'dongluc', 'truyencamhung', 'thoiquen', 'khampha',
    'chamsocsuckhoe', 'suckhoe', 'chamsocbe', 'nha', 'vantay', 'dochai',
    'sukien', 'congnghe',  # ← "Công nghệ" là slug 'congnghe'
}
```

Mapping label → slug: đọc `D:/Taadaa/Tiktok-video/data/niches_pool.txt` (TSV 4-col: group/slug/label/allow_no_speech).

---

## Lesson: Verify Niche TRƯỚC khi generate avatar

Khi Operator gửi ảnh profile nick, TRƯỚC KHI làm bất cứ gì với avatar, phải:
1. Đọc Excel xem niche label (cột `Keyword Video`).
2. Kiểm tra video trong folder gốc (duration, content type).
3. Nếu niche là KHO_VIRAL → **DỪNG avatar**, báo cáo niche lệch, đề xuất migrate sang Niche Hot.
4. Chỉ proceed avatar sau khi niche đã chuẩn và video đúng niche đã có trong folder.

**"Đổi đi" của operator không chỉ nghĩa là đổi avatar — khi niche sai, đổi avatar lại chỉ làm rối thêm.**
