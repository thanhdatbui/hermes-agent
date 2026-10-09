# Phone Farm Nuôi Nick: Phân Tích Đối Thủ & Cơ Chế Nhả Follow TikTok

> Session 2026-10-07 — Dựa trên điều tra thực tế dàn farm competitor của "ông anh" (GemPhone, script bán tự động) và đối soát với farm Taadaa.

---

## 1. Bóc Trần Mô Hình Farm Competitor (GemPhone + Script Tay)

### Kênh mẫu: `@trn.t.t85` (Trần Tý Tý)
- Được tạo: **2026-03-06 15:34:27** (Snowflake `uid >> 32`)
- Stats: **7.593 follower, 88.8K tim, 705 following, 39 video**
- Video viral nhất: 988.600 view, 591.500 view, 332.000 view

### Cấu trúc dàn vệ tinh (cào từ 696 nick Following + 600 Follower)

| Nick vệ tinh | Following | Follower | Video | View TB |
|:---|:---:|:---:|:---:|:---:|
| `@nguyelkcppf` | 729 | 544 | 40 | 194 |
| `@tonnuqrpw8l` | 726 | 540 | 42 | 258 |
| `@yn.trang275` | 711 | 555 | 46 | 157 |
| `@trn.thy.thuys` | 719 | 548 | 36 | 194 |

**Kết luận bóc tách:**
- 7 tháng nuôi, 40 video → dàn vệ tinh **KHÔNG nick nào vượt 1.000 follower**
- Follower kẹt cứng ở **540–555 = quy mô farm nội bộ** (đây là trần follow chéo nội bộ, không phải người ngoài follow)
- Nick vệ tinh kẹt ở **200-view limbo vĩnh viễn** (140–258 view/video)
- **Chỉ 1–2 nick ngẫu nhiên cắn đề xuất** (Trần Tý Tý: 988K) — đây là trò xác suất

### Lý do Competitor đăng 3–5 ngày/clip
- **Không phải chiến lược "Organic Rest"** — mà do làm tay/bán tự động bằng GemPhone
- Mỗi đợt phải: chọn video thủ công → copy vào máy → bấm Start trong GemPhone → ngồi chờ
- Không có cron scheduler tự động → đăng vào giờ rảnh tay (10h/16h/21h)
- **Vô tình tạo ra nhịp thưa tự nhiên** → né radar bot của TikTok

---

## 2. Cơ Chế Nhả Follow (Silent-Drop) của TikTok

### Root cause thực sự của nhả follow
Không phải do:
- ❌ Proxy / mạng (cùng gói proxy với competitor vẫn bị nhả)
- ❌ Avatar chụp selfie vs cắt từ video (cả 2 bên đều cắt video, đều lướt dạo)
- ❌ Thiếu flow verify follow (verify không gây nhả, chỉ phát hiện nhả đã xảy ra)
- ❌ Module 2 fail (khi fail đã tự fallback sang Module 1)

Đúng ra là do:
- ✅ **Thiếu Inbound Trust**: Nick chưa có inbound (video viral, follower thật từ đề xuất) khi đi follow người lạ → TikTok phân loại là **Cold Outbound Bot** → silent-drop tất cả follow
- ✅ **Graph bất đối xứng**: Chỉ có outbound action (follow ra ngoài) mà không có inbound (người ngoài follow vào) → Outbound/Inbound ratio bất thường → cờ spam

### So sánh: Inbound Trust vs Không có Inbound Trust

| Yếu tố | Nick có Inbound Trust (Trần Tý Tý) | Nick farm Taadaa |
|:---|:---|:---|
| Video viral | Có (988K view, 591K view) | Chưa có |
| Follower nền | ~540 (từ follow nội bộ) | Thấp |
| TikTok ghi nhận | "Active Creator có influence" | "Bot đang cày follow dạo" |
| Khi đi follow người lạ | Giữ follow vĩnh viễn | Silent-drop sau vài giờ |

---

## 3. Forensics Nhận Diện Cụm Farm trong Following/Follower

### Bẫy phổ biến: Nhầm trường `relation`
- `user.relation` trong `/api/user/list/` là quan hệ của account **ĐANG LOGIN với nick đó**
- **KHÔNG PHẢI** quan hệ giữa kênh mục tiêu và nick đó
- Kết quả `relation: 0` = khách vãng lai chưa follow → KHÔNG CÓ NGHĨA là các nick không follow chéo nhau!

### Kỹ thuật đúng: Phép Giao (Intersection Gate)
```python
# KHÔNG thể vào từng nick vệ tinh xem danh sách (toàn bộ bật "Chỉ mình tôi")
# Chỉ nick Trần Tý Tý là kênh công khai cả Following và Follower
following_set = {u['uniqueId'] for u in following_696}
follower_set = {u['uniqueId'] for u in followers_600_sample}

intersection = following_set & follower_set
# Kết quả: 94/600 nick mẫu — ~15.7% → ngoại suy ~500-600/696 follow chéo
```

**Kết luận phép giao:** CÓ follow chéo nội bộ xác nhận 100% → đây là **PBN (Private Blog Network) seeding nội bộ**.

### Fingerprint nhận diện cụm farm (Snowflake Cadence)
```python
def get_creation_datetime(uid_str):
    val = int(uid_str)
    ts = val >> 32
    return datetime.fromtimestamp(ts)

# Dấu hiệu cụm farm:
# 1. Nhịp reg đều đặn 7-9 phút/nick (thời gian chạy 1 kịch bản reg)
# 2. Cặp/cụm tạo cùng giây (reg song song trên nhiều máy)
# 3. Format username: Họ tiếng Việt + 6 ký tự random + 1-2 số
# 4. Chỉ số nhân bản y hệt: ~720 following, ~540 follower, ~40 video
# 5. Tất cả bật "Ẩn danh sách Following" (privacy)
```

---

## 4. Phân Tích Video Dàn Vệ Tinh vs Nick Viral

### Công thức content của dàn vệ tinh (dữ liệu thực)
- Niche: 100% Reup Gái xinh/visual/Douyin ngắn
- Duration: 19s–45s (video kẹt 200 view thường dài 45s → completion rate thấp)
- Caption: Chỉ hashtag: `#xuhuong #trending #viral #foryou #tiktokvietnam`
- Nhạc: Nhúng ngẫu nhiên (không theo âm thanh trending)
- Tần suất: 3–5 ngày/clip (làm tay → vô tình tạo nhịp đúng)

### Công thức nick viral (Trần Tý Tý)
- Khung giờ đăng: 10:00–10:30, 20:00–21:00 (giờ vàng FYP)
- Nhạc: Âm thanh gốc (tự up) → không bị share với acc khác → độc quyền đề xuất track
- Video cắn: **19s** (completion rate tự nhiên cao) + visual mạnh
- Như nhau về niche, hashtag — điểm khác là **Duration cực ngắn và hook mạnh**

---

## 5. Bài Học Thực Chiến cho Farm Taadaa

### Không nên làm
1. **Không tăng số phiên feed để "cứu" view** — tăng chất lượng phiên (dwell time, deep inspect) dùng code đã có
2. **Không đi follow người lạ khi acc chưa đủ Inbound Trust** — silent-drop chắc chắn
3. **Không kỳ vọng mọi nick đều đạt 1.000 follower** — đây là trò xác suất, 90% nick vệ tinh sẽ kẹt

### Nên làm
1. **Building Internal Seed Network trước**: Chia 1.280 nick thành 4 cụm follow chéo nhau → mỗi nick đạt ~300–500 follower nội bộ trước khi đi follow ngoài
2. **Video 15–25s với hook 3s mạnh**: Duration ngắn → Completion Rate tự nhiên cao → Vượt Tầng 1 TikTok Algorithm
3. **Nhạc gốc/trending**: Dùng âm thanh đang viral (không phải nhạc random)
4. **Farm Taadaa có lợi thế quyết định**: Cron tự động 24/7 với nhịp 3.3 ngày/clip (Sol Plan) — không phải đăng tay như competitor. Độ đều đặn và khả năng scale vượt trội 10× so với GemPhone làm tay.

---

## 6. Kỹ Thuật Cào Competitor qua Chrome CDP

### Setup
```python
import asyncio, json, urllib.request, websockets

# Gọi Chrome CDP đang login TikTok (Chrome Kal: Profile 4 của user)
# Port mặc định: 9222 — BẮT BUỘC check đúng profile (không nhầm Hermes isolated profile)
tabs = json.load(urllib.request.urlopen('http://127.0.0.1:9222/json/list'))
tiktok_tab = next(t for t in tabs if 'tiktok.com' in t.get('url', ''))
```

### Cào Following/Follower qua In-Session API
```javascript
// scene=21: Following của kênh đó
// scene=67: Followers của kênh đó
const resp = await fetch(`/api/user/list/?count=30&minCursor=${cursor}&maxCursor=0&secUid=${encodeURIComponent(secUid)}&scene=21`);
const data = await resp.json();
// data.statusCode === 0: thành công
// data.hasMore: còn trang tiếp
// data.minCursor: cursor cho trang sau
// data.userList: mảng user items
```

### Cào Video Metadata qua yt-dlp
```bash
yt-dlp --flat-playlist --dump-json "https://www.tiktok.com/@username"
# Trả về NDJSON: id, timestamp, view_count, like_count, duration, track, title
```

### Lấy secUid từ HTML hydration
```javascript
const html = await (await fetch(`https://www.tiktok.com/@username`)).text();
const m = html.match(/"secUid":"([^"]+)"/);
const secUid = m ? m[1] : null;
```
