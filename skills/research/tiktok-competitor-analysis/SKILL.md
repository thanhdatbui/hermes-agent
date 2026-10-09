---
name: tiktok-competitor-analysis
description: "Cào và phân tích dữ liệu kênh TikTok đối thủ/mẫu: metadata 35 video, Snowflake ngày tạo acc, engagement metrics, nội dung video (frame+OCR+audio), blueprint nhân bản. Dùng khi user đưa link kênh TikTok muốn 'nghiên cứu', 'học hỏi', 'so sánh' hoặc build dàn kênh tương tự."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [tiktok, scraping, competitor, analysis, yt-dlp, snowflake, engagement]
    related_skills: [ui-evidence-first, web-marketplace-research, youtube-content]
---

# TikTok Competitor Channel Analysis

## Khi nào dùng skill này

- User đưa link TikTok profile (`https://www.tiktok.com/@username`) và nói: "cào dữ liệu", "nghiên cứu kênh này", "học hỏi", "so sánh với farm"
- User muốn build dàn kênh tương tự → cần reverse-engineer công thức content

## Workflow đầy đủ (thứ tự bắt buộc)

### Step 1 — Scrape metadata toàn bộ video
```bash
yt-dlp --flat-playlist --dump-json "https://www.tiktok.com/@<username>"
```
Parse NDJSON → DataFrame với pandas. Fields: `id, view_count, like_count, comment_count, save_count, repost_count, duration, upload_date, timestamp, track, title, uploader_id`.

**KHÔNG bị WAF/captcha chặn** — yt-dlp bypass qua API ngầm, khác với browser render.

### Step 2 — Lấy thông tin profile (followers, following, likes)
```python
browser_navigate("https://www.tiktok.com/@username")
# AX snapshot trả về:
# heading "705 Following 7600 Followers 88.2K Likes"
# heading "No bio yet."
```
Lưu ý: Captcha popup ("Drag slider") chỉ xuất hiện trên browser render, KHÔNG ảnh hưởng đến yt-dlp.

### Step 3 — Xác định ngày tạo acc từ Snowflake User ID
TikTok User ID (`uploader_id` hoặc `user.id` trong HTML hydration) là một số nguyên 64-bit dạng Snowflake ID. 32 bit cao nhất (`uid >> 32`) là Unix timestamp (giây) tại thời điểm tài khoản được khởi tạo:
```python
import datetime
from typing import Union

def extract_creation_time(uid: Union[str, int], date_only: bool = True) -> str:
    """Trích xuất ngày tạo nick TikTok từ Snowflake User ID với guard kiểm tra biên."""
    if not uid:
        return ""
    try:
        val = int(str(uid).strip())
        if val <= 0:
            return ""
        ts = val >> 32
        # Giới hạn timestamp hợp lý (từ năm 2014 đến 2049)
        if not (1400000000 <= ts <= 2500000000):
            return ""
        dt = datetime.datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d") if date_only else dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""

# Ví dụ thực tế:
# UID: 7123456789012345678 >> 32 = 1658584029 -> "2022-07-23"
```
Áp dụng tương tự cho `video_id >> 32` để lấy giờ đăng chính xác đến giây.

### Step 3b — Tính Tổng View & View 30 ngày (Beta / Creator Rewards) và Region
Profile UI TikTok chỉ hiển thị Followers/Following/Likes, không hiện tổng view. Để đối soát điều kiện kiếm tiền Beta (ngưỡng 100K view/30 ngày) và quốc gia tài khoản (US, FR, DE, VN...):
1. **Tổng View & View 30 ngày**:
   ```python
   import time
   now_ts = int(time.time())
   cutoff_30d = now_ts - 30 * 86400

   total_views = sum(v.get("view_count", 0) for v in videos)
   views_30d = sum(
       v.get("view_count", 0) 
       for v in videos 
       if v.get("timestamp", 0) >= cutoff_30d
   )
   ```
2. **Khu vực / Region**:
   - Web Profile Hydration: JSON trong `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">` -> `default_scope['webapp.user-detail']['userInfo']['user'].get('region')`.
   - Mobile Aweme Endpoint: `/aweme/v1/user/profile/other/?sec_user_id=...` -> trường `user.region` (e.g. `US`, `FR`, `VN`).
   - Tỷ lệ query: Giãn cách 5–10s hoặc xoay proxy sạch để tránh dính HTTP 429 WAF Captcha.

### Step 4 — Xuất Excel tổng hợp & Tích hợp Web Dashboard
Dùng pandas + openpyxl. 2 sheet:
- Sheet 1: Thông tin kênh (profile info + UID + Ngày Tạo + aggregate stats)
- Sheet 2: Danh sách video (full 35 rows, tất cả metrics)
*Lưu ý khi xuất báo cáo kho / tracker*:
- Cột "Ngày Tạo" nên đặt ngay sau "UID" để dễ lọc acc ngâm, acc cổ vs acc new reg. Chú ý cập nhật lại các chỉ số cột (index offset +1) trong unit test tương ứng (`test_export_excel_report`) để tránh fail do assert vị trí cột cứng.
- **Quy tắc On-Demand Web Dashboard vs Báo cáo hàng ngày**: User không muốn bị spam tin nhắn hay bắt tải file báo cáo Excel mỗi ngày ("K cần xuất báo cáo mỗi ngày đâu. Để ở web để xem là đc r"). Vì vậy:
  1. Script tracker chỉ xuất file Excel khi có cờ thủ công `--export <path>`, không tự tiện ghi file `.xlsx` mặc định mỗi tick.
  2. Cronjob chạy ngầm quét số liệu đặt `deliver: "local"` để âm thầm ghi snapshot vào SQLite (`tiktok_tracker.db`), không bắn tin Telegram.
  3. Cột "Ngày Tạo" được render trực tiếp lên Web Dashboard (`tiktok_dashboard.py`), hỗ trợ sort `sortTable('created_at')` và search theo năm-tháng (`2025-12`, `2026-03`) để người vận hành xem trực tiếp bất cứ khi nào cần.


### Step 5 — Download và phân tích TOP 3 video viral
```bash
yt-dlp -F "https://www.tiktok.com/@user/video/<id>"    # list formats
yt-dlp -f "h264_540p_*" -o "vid.mp4" "<url>"           # download
ffmpeg -y -ss <N> -i vid.mp4 -vframes 1 frame_<N>s.jpg # extract frames
```
Frame extraction nên làm tại: 2s, 8s, 15s, 25s, cuối.

**Đọc nội dung frame:**
1. WinRT OCR trước (`windows-native-ocr` skill + `--upscale 3` nếu text nhỏ)
2. Nếu OCR ra Latin gibberish (Å, ä) → `browser_navigate("file:///path/frame.jpg")` → `browser_vision()`
3. Extract audio → Google Speech API: `speech_recognition.recognize_google(audio, language="vi-VN")`

### Step 6 — Tính engagement metrics
```python
er = likes / views * 100            # ER% (benchmark VN <50K: 2-4%)
save_rate = saves / views * 100     # (>0.1% tốt, >0.3% exceptional)
repost_rate = reposts / views * 100 # (>0.05% = viral potential)
```

### Step 7 — Delegate phân tích sâu cho Sol
Sau khi có đủ dữ liệu thực tế, delegate_task với context chứa:
- Toàn bộ 35 video (ngày/giờ/dur/views/likes/comments/saves/reposts/title)
- Nội dung video top (từ OCR/vision/audio)
- Mục tiêu người dùng (build farm, học công thức, so sánh...)

Yêu cầu Sol phân tích: warm-up pattern, content formula, viral triggers, pitfalls, blueprint nhân bản.

### Step 8 — Cào danh sách Following/Follower (khi user yêu cầu soi tệp follow)
TikTok Web chặn khách vãng lai xem danh sách Following/Follower (bật modal "Đăng nhập").
Khi cần cào danh sách này:
1. Dùng Chrome CDP đã đăng nhập (`http://127.0.0.1:9222` qua skill `logged-in-chrome-cdp-marketplace`).
2. Mở tab điều hướng đến `https://www.tiktok.com/@<username>`.
3. **KỸ THUẬT CÀO CHUẨN XÁC NHẤT — In-session Fetch API (Bypass hoàn toàn lỗi kẹt cuộn DOM)**:
   DOM scrolling (gán `scrollTop` hoặc `mouseWheel`) thường xuyên bị kẹt ở mốc 28-30 nick do virtualized list hoặc event trigger bị TikTok chặn. Thay vào đó, trích xuất `secUid` từ script hydration hoặc DOM rồi fetch trực tiếp endpoint ngầm trong context tab đã login:
   ```javascript
   // 1. Trích xuất secUid từ hydration script
   const hydration = JSON.parse(document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__')?.innerText || '{}');
   const secUid = hydration?.['__DEFAULT_SCOPE__']?.['webapp.user-detail']?.['userInfo']?.['user']?.['secUid'] 
                  || document.body.innerHTML.match(/"secUid":"([^"]+)"/)?.[1];

   // 2. Phân trang qua cursor /api/user/list/ (scene=21 cho Following, scene=67 cho Follower)
   let cursor = 0, hasMore = true, allUsers = [];
   while (hasMore) {
       const url = `/api/user/list/?count=30&minCursor=${cursor}&maxCursor=0&secUid=${encodeURIComponent(secUid)}&scene=21`;
       const res = await (await fetch(url)).json();
       if (res.statusCode !== 0) break;
       const list = res.userList || [];
       for (const item of list) {
           const u = item.user;
           if (u) allUsers.push({
               id: u.id,
               uniqueId: u.uniqueId,
               nickname: u.nickname,
               signature: u.signature,
               relation: u.relation, // 1: following 1 chiều, 2: mutual / follow chéo bạn bè
               avatar: u.avatarLarger
           });
       }
       hasMore = res.hasMore && list.length > 0;
       cursor = res.minCursor;
       await new Promise(r => setTimeout(r, 300));
   }
   ```
   *Ưu điểm*: Cào 700+ nick trong < 30s, không phụ thuộc render UI, lấy được chính xác trường `relation` (quan hệ 2 chiều) và Snowflake ID của từng nick.

4. **Kỹ thuật nhận diện cụm nick Phone Farm trong danh sách Following/Follower**:
   - **Bẫy tư duy Follow chéo (Mutual Follow Fallacy)**: Nhiều người tưởng farm phải follow chéo nhau (`relation == 2`). Thực tế farm chuyên nghiệp **CẤM** follow chéo 2 chiều để tránh bị AI TikTok quét trúng graph cluster. Tỷ lệ mutual follow thường bằng `0/700`.
   - **Nhịp Reg tự động (Snowflake Timestamp Cadence)**: Giải mã ngày giờ tạo từng nick qua `int(u['id']) >> 32`. Nếu thấy:
     * Cứ đều đặn 7–9 phút có 1 nick được tạo liên tiếp trong cùng ngày (nhịp reg tool mail + TikTok trên phone farm).
     * Các cụm nick xuất hiện cùng 1 giây hoặc cách nhau 1-2 giây (dàn farm nhiều máy reg song song).
   - **Fingerprint Profile & Clone Metrics**:
     * Format username: Họ tiếng Việt + chuỗi 6 ký tự random + số đuôi (ví dụ `nguyelkcppf`, `tonnuqrpw8l`).
     * Chỉ số nhân bản: Đều có lượng following giống hệt nhau (~710–730), follower sàn sàn nhau (~540), số video bằng nhau (~40 clip), và đều bật quyền riêng tư "Ẩn danh sách Following".

---

## Engagement Benchmarks TikTok VN (<50K followers)

| Metric | Average | Good | Exceptional |
|:---|:---:|:---:|:---:|
| ER (Likes/Views) | 2-4% | 4-5% | >5% |
| Save rate | <0.1% | 0.1-0.3% | >0.3% |
| Repost rate | <0.05% | 0.05-0.1% | >0.1% |

---

## Dữ liệu bóc được vs KHÔNG bóc được

| Bóc được (không cần login) | Không bóc được |
|:---|:---|
| ✅ Views, Likes, Comments, Saves, Reposts | ❌ Watch time %, Avg watch duration |
| ✅ Ngày giờ đăng chính xác (timestamp) | ❌ Traffic source (FYP vs Search vs Follower) |
| ✅ Duration video | ❌ Audience demographics |
| ✅ Ngày tạo acc (Snowflake ID) | ❌ Profile views timeline |
| ✅ Track / âm thanh | ❌ Follower growth timeline |
| ✅ Thumbnail + frame video | ❌ Revenue/monetize data |
| ✅ Followers/Following hiện tại (browser AX) | ❌ Comment text content |

---

## So sánh với farm của user

Sau khi có metrics kênh nghiên cứu, đọc cron + script farm của user trước khi hỏi:
```bash
hermes cron list
cat "D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron_schedule.json"
grep -n "FEED_SESSION_MIN\|DEFAULT_FOLLOW\|BLOCK_ANCHOR" \
  "D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/multi_machine_feed_session.py"
grep -n "BLOCK_ANCHORS\|JITTER_MINUTES\|PAIR_GAP" \
  "D:/Taadaa/tiktok-luot nuoi acc/python_runner/hermes_cron/blocks.py"
```

Constants Taadaa farm (đã verify 2026-09-21):
- Feed: 16-22 videos/session, max 28 swipes
- Sessions/day cap: 2 per acc
- Like rate: 40% (Deep Inspect), Follow rate: 20%
- Gate follow: nick ≥10 video posted
- Block anchors: 06:00, 12:00, 18:00, 00:00 (±25p jitter)
- Concurrency: 15 follow workers, 20 upload workers

---

## Pitfalls

| Pitfall | Fix |
|:---|:---|
| Captcha popup trên browser → tưởng scrape bị chặn | yt-dlp dùng API riêng, bypass hoàn toàn. Browser popup không ảnh hưởng. |
| Pipe `yt-dlp ... \| head` trong git-bash trên Windows bị `OSError: [Errno 22] Invalid argument` | Lỗi broken pipe do MSYS đóng stdout sớm. Chạy qua Python `subprocess.run(..., capture_output=True)` rồi parse JSON từng dòng. |
| Cào danh sách Following/Followers bị chặn / yêu cầu đăng nhập | TikTok Web khóa API `/api/user/list/?...` và popup danh sách nếu chưa login (bật modal `Đăng nhập`). Trước khi cào qua CDP (:9222), BẮT BUỘC kiểm tra cookie `sessionid` hoặc DOM profile. Cảnh giác bẫy attach nhầm Hermes isolated profile (`hermes/browser_profile` không có session TikTok) thay vì Profile cá nhân đã login (`Profile 4`). |
| Soi nick farm / seeding trong Following & Bẫy trường `relation` | Để kiểm tra nick trong Following có thuộc farm hoặc follow chéo: BẪY NGUY HIỂM: Trường `user.relation` trong `/api/user/list/` là quan hệ của Viewer đang login với user đó, KHÔNG PHẢI giữa kênh mục tiêu và user! Khi các nick vệ tinh ẩn Following ("Chỉ mình tôi"), không thể vào từng nick xem ngược lại. CÁCH DUY NHẤT để chứng minh quan hệ 2 chiều: Lấy Followers của kênh mục tiêu giao với Following của nó (`set(following) & set(followers)`). Nếu xuất hiện hàng chục/trăm nick trùng, đó là bằng chứng thép 100% về mạng lưới follow chéo PBN nội bộ. |
| Ngộ nhận phone farm có script "thần kỳ" nick nào cũng viral & Trần Follower nội bộ | Dữ liệu đối soát dàn farm 7 tháng thực tế: 100% nick vệ tinh đều kẹt ở **200-view limbo** (140–250 view) và **kẹt cứng ở trần 540–555 follower** (đây là quy mô cụm farm nội bộ follow chéo lẫn nhau; không có video viral ra FYP thì follower đứng im vĩnh viễn, không thể tự chạm 1.000 follow). Trong cả đàn chỉ 1–2 nick cắn đề xuất triệu view (trò chơi xác suất). Nhịp đăng 3–5 ngày/clip (70h–120h/clip) thực chất do đối thủ làm tay/bấm đợt thủ công bằng GemPhone (không có cron, đăng vào giờ rảnh 10h/16h/21h); vô tình nhịp thưa này né được radar bot nhưng hiệu suất rất thấp. Farm Taadaa có cron tự động chuẩn nhịp ~3.3 ngày/clip (kèm ngày dưỡng sinh) an toàn tương đương nhưng tính đều đặn và khả năng scale vượt trội hoàn toàn. |
| Bẫy quy kết avatar & cấm phủ nhận nhả follow thật | TUYỆT ĐỐI CẤM bịa sự khác biệt về avatar (ví dụ: phán selfie vs cắt từ video) khi chưa inspect asset gốc. Khi user đã đối soát tracker/dashboard xác nhận bị nhả follow thật, CẤM bao biện do "sync delay". Khi cùng gói mạng/proxy, nguyên nhân follow giữ được nằm ở Inbound Trust (acc đã có video viral/nhiều like được TikTok nới lỏng) vs Outbound-only (acc chưa có view đi follow bị silent-drop). |
| Infinite scroll trên modal Following/Follower bị đứng ở 30 nick | Cuộn DOM hoặc dispatch mouseWheel thường xuyên bị kẹt ở mốc 28-30 user do virtualized list. Fix triệt để 100%: Dùng In-session Fetch API `/api/user/list/?count=30&minCursor=...&secUid=...&scene=21` trong context tab đã login để kéo sạch toàn bộ hàng trăm nick trong vài chục giây. |
| Modal Following bị chặn hoặc click không ăn | Kiểm tra xem popup Thông báo (`DivHeaderInboxWrapper`) có đang tự bung đè lên UI không. Phải xóa dialog inbox khỏi DOM trước khi click nút `following-count`. |
| Tab Đang follow (Following) hiện 0 user dù bên ngoài có số lượng | Kênh đã bật quyền riêng tư "Chỉ mình tôi" cho danh sách Following (như `@hong.thy.qunhhh`). Đây là privacy feature của TikTok, không phải lỗi. |
| WinRT OCR đọc tiếng Việt ra Latin gibberish | Dùng browser_vision() thay vì WinRT khi text có diacritics nặng |
| Following count → suy diễn "đi follow X người trong Y ngày" | **TUYỆT ĐỐI CẤM** — không có timestamp follow history. Chỉ report current count. |
| Khoảng cách ngày tạo → video đầu → kết luận "ngâm acc" | Là giả thuyết chưa kiểm chứng. Nick dùng cá nhân bình thường, chỉ chưa up video. |
| f-string với nested quotes trong `-c string` | Dùng biến trung gian thay vì `v.get(\"id\")` trong f-string |
| speech_recognition.UnknownValueError | Audio quá nhiều nhạc, ít lời. Crop đoạn 5-10s có lời rõ nhất |
| Hỏi user "kênh này làm nội dung gì?" khi đã cào data | **CẤM** — tự extract frame + OCR + vision trước khi hỏi ngược user |
| Bắt user tự xem/xác minh video/kênh cào thủ công | **TUYỆT ĐỐI CẤM** — user yêu cầu cào tự động ("vkl tao bảo mày đi cào link h mày bắt t đi nhìn"). Bắt buộc dùng `AIFemaleFilter` (NLP blacklist `toca, boca, game, traidep...` + ViT ONNX gender classification `onnx-community/gender-classification-ONNX` với normalization `mean=0.5, std=0.5` chạy 0.05s/frame) tự động xóa video rác/game/nam giới và nạp bù video chuẩn gái 100%. |
| Phân bổ bể gộp gom cục bộ 2-3 kênh vào 1 folder | **CẤM** — Với các kênh thiếu (< 40 clip), mọi folder bể gộp (Curated Hub) bắt buộc phải rút video từ TẤT CẢ các kênh thiếu trong bể (chia đều + random biến thiên số lượng giữa các bạn nữ), sau đó xáo trộn đều để kênh có tính đa dạng tối đa. Kênh đủ >= 40 clip thì giữ độc quyền 1 người/folder. |
| Hỏi user "farm bác config nuôi thế nào, upload mấy video/ngày?" | **CẤM** — tự đọc config, cron (`hermes cron list`), scripts (`multi_machine_feed_session.py`, `blocks.py`) và SQLite tracker (`tiktok_tracker.db`) trên máy. |
| Đọc SQLite `tiktok_tracker.db` lỗi `no such table: messages/snapshots` | Bắt buộc chạy `PRAGMA table_info(snapshots)` trước khi SELECT. Bảng `snapshots` chứa `username, following, followers, likes, timestamp, id`. |
| Cào view/video của nhiều nick trên farm để kiểm tra view trend | Đừng crawl toàn bộ farm. Chỉ cần truy vấn danh sách nick có >= 10 video từ SQLite: `SELECT s.username, m.may FROM snapshots s JOIN account_mapping m ... GROUP BY s.username HAVING MAX(s.total_videos) >= 10`. Sau đó chỉ scrape top 4-5 nick tiêu biểu nhất qua `yt-dlp --flat-playlist --dump-json` để có phân phối view thực tế. |
| Revert upload ngày dưỡng sinh (Organic Rest Day) | Khi data farm cho thấy view TB thấp (100-300 view) và lịch đăng bị nén quá dày (1-2 ngày/video do ngày dưỡng sinh vẫn cố upload), phải REVERT cờ cho phép upload về `status: skipped, reason: organic-rest-day-upload-disabled`. Đưa chu kỳ đăng tự nhiên về ~3 ngày/video để thuật toán TikTok có đủ 48-72h nhả hết lượt phân phối đề xuất. |
| Tăng like quá đà để "cứu" 200-view limbo | Sai lầm nghiêm trọng. Like là tín hiệu yếu nhất trong thuật toán TikTok. Thả tim 20-25% biến farm thành bot cluster. Bắt buộc giữ like FYP ở mức 12-16% (default 15%), tập trung tối ưu hook 3s đầu và duration 12-45s. |
| Siết download quá hẹp (10-35s) | Làm cạn pool video nhanh chóng của 1.280 nick. Chuẩn Sol Plan: Reject <8s & >120s, ưu tiên dải 12-45s lên Priority 0, giữ 45-90s làm Priority 1 dự phòng. |
| Follow tự nhiên quá nhanh khi lướt feed bị nhả follow | Nếu tap follow ngay trong 1-2 giây đầu khi quẹt trúng video, TikTok đánh giá là bot và âm thầm hủy (nhả) follow. Bắt buộc áp dụng **Watch Time Gate**: ngâm video xem sâu tối thiểu **8.0s – 12.0s** trước khi bấm follow tự nhiên, và ghi nhận `watch_dwell_seconds` vào telemetry log. |
| Tải Douyin bằng `f2 dy` bị lỗi `Option '-P' requires 2 arguments` hoặc `HTTP 403 / Fresh cookies needed` | Flag `-P` của `f2 dy` bắt buộc truyền 2 args (`-P http://... http://...`). Douyin WAF chặn detail API nếu thiếu session cookies; bắt buộc truyền cookie còn hạn qua `f2 dy -k "<cookie>"` hoặc `yt-dlp --cookies douyin_cookies.txt`. Không dùng `--cookies-from-browser` trên Windows khi trình duyệt đang mở do lỗi lock file SQLite `Cookies`. |
| Tải `f2` bị treo 30 giây hoặc lỗi `Client error 405 Method Not Allowed https://api.day.app/` | `f2` mặc định bật thông báo Bark (`enable_bark: true` trong `venv/.../f2/conf/conf.yaml`). Do không có key nên mỗi request bị timeout 30s gây đơ toàn bộ crawler đa luồng. Bắt buộc sửa `enable_bark: false`. |
| Bắt user gửi link Douyin / bắt user tự tìm creator tiếng Trung | **TUYỆT ĐỐI CẤM** — user không biết tiếng Trung ("Mẹ t đã k biết tiếng trung yêu cầu m đi cào cho t m lại bảo t gởi link"). Agent phải tự động 100%: cào sitemap Douyin (`/htmlmap/hotauthor_0_X`) tìm creator gái xinh/dance, sau đó dùng `f2 dy -M post` kéo về. |
| Video Douyin dính tiếng nói tiếng Trung hoặc anime/hoạt hình/review | Áp dụng Bộ Lọc Kép: (1) NLP blacklist loại từ khóa anime/game/review; (2) AI Vision ViT ONNX ngưỡng `score >= 0.75` chỉ nhận gái người thật; (3) AI Whisper quét 30s âm thanh, xóa ngay nếu phát hiện `zh_speech`, chỉ giữ video thuần nhạc nền (`no_speech`). |
| **[CRITICAL] Đánh giá kênh rồi so sánh với farm user dựa trên giả định về môi trường mà không có bằng chứng** | Ví dụ: "ông anh không lướt feed tự động nên cần giãn video hơn" — KHÔNG biết ông anh có nuôi acc tự động không. **CẤM suy diễn về cách người khác vận hành kênh** nếu không cào được data đó. Chỉ report những gì đo được: views/likes/dates. Mọi giải thích cơ chế phải gắn label HYPOTHESIS, không phải FACT. |
| So sánh farm user với kênh mẫu → đề xuất thay đổi code/config | Phải đọc cron + code farm trước khi đưa khuyến nghị. Đọc: `hermes cron list`, `blocks.py`, `multi_machine_feed_session.py`, báo cáo tracker gần nhất. Không dùng lý thuyết chung để phán. |
| Tìm báo cáo sức khỏe farm hàng ngày | Cron `daily-tiktok-farm-tracker` (ID `9f7a9a3969b2`) lưu output tại `C:\Users\Kibe\AppData\Local\hermes\cron\output\9f7a9a3969b2\`. Format: `YYYY-MM-DD_HH-MM-SS.md`. Metrics: tổng nick, LIVE count, chưa avatar, DIE, tổng followers, top nick cắn đề xuất. |
| Đọc SQLite `tiktok_tracker.db` lỗi `no such table: messages/snapshots` | Đường dẫn DB canonical là `D:/Taadaa/data/tiktok_tracker.db` (bảng `snapshots` chứa `username, uid, follower, following, heart, video, status, created_at`; bảng `farm_account_info` chứa `username, may, tik`). Trước khi SELECT nên kiểm tra schema qua `PRAGMA table_info`. |
| Nhầm lẫn mục đích Farm nuôi nick (Trust/Dual Gate) vs Kênh Beta (cày view) | Farm Taadaa là nuôi tài nguyên (age >= 21d, video >= 6, 2FA, giữ LIVE), view chỉ là warm-up mồi thuật toán. **CẤM** tích hợp cào view định kỳ cho cả dàn 1.280 nick (làm cháy pool proxy, nghẽn DB và rối dashboard). Chỉ chạy On-Demand audit 5-10 nick qua `yt-dlp` khi user yêu cầu kiểm tra chất lượng render hoặc nghi ngờ 0-view shadowban. |
| Tool MMO/Farm trôi nổi chia sẻ file nén có pass (`123123`) hoặc bọc Enigma Protector/crypter | CẢNH BÁO BẢO MẬT CỰC CAO: Đặt password file nén là chiêu né Google Drive quét AV; file EXE bọc Enigma Protector (`.enigma1`, `.enigma2`) thường chứa mã độc cắp cookie trình duyệt, Telegram session, GPM token. TUYỆT ĐỐI CẤM chạy file EXE lạ trên máy thật/máy farm. Mọi tính năng như Check Tổng View, View 30 ngày Beta, Region, Snowflake ID đều tự giải quyết sạch bằng Python nội bộ (`yt-dlp`, Aweme API, bit-shift `uid >> 32`) an toàn 100%. |

---

## References
- `references/farm-vs-competitor-upload-cadence-analysis.md` — Đối soát nhịp đăng farm vs kênh mẫu viral, giải mã cơ chế tier 200-view limbo (ranking signals, 3s retention vs fake likes), quy tắc ngắt upload ngày dưỡng sinh (0 follow, 0 up), và Sol High Plan (download 12-45s sweet spot, like rate 12-15%).
- `references/competitor-reup-visual-formula-and-benchmarks.md` — Phân tích chi tiết công thức 3 giai đoạn mồi view/viral, tệp follow gái 88.1%, âm thanh gốc và nhịp dưỡng sinh từ case study thực tế
- `references/tiktok-scraping-techniques-20260921.md` (trong skill `ui-evidence-first`) — code đầy đủ, Snowflake decode, audio pipeline
- `references/tiktok-farm-cluster-forensics-and-in-session-following-scrape.md` — Kỹ thuật cào Following/Follower qua In-Session Fetch API (bypass kẹt cuộn DOM), và forensics nhận diện cụm nick farm (Mutual Follow Fallacy, Snowflake timestamp cadence 7-9p, clone metrics).
- `references/tiktok-following-graph-and-farm-cluster-recon.md` — Trích xuất Following/Followers siêu tốc qua In-Session API (scene=21/67), bẫy trường relation của Viewer, kỹ thuật đối soát tập giao (Intersection Gate) chứng minh mạng lưới follow chéo PBN nội bộ khi nick vệ tinh ẩn danh sách.
- `references/tiktok-niche-reorientation-and-follow-gating.md` — Quy hoạch chuyển đổi dàn slot Tik5/Tik7 sang niche visual/gái xinh, phân tách cổng follow nội bộ vs follow tự nhiên và cơ chế Watch Time Gate chống nhả follow
- `references/douyin-video-scraping-and-workflow-audit.md` — Quy trình cào video 1080p gốc không watermark từ Douyin (TikTok Trung Quốc) qua công cụ chuyên dụng `f2` CLI & `yt-dlp`, pipeline trích xuất frame bằng chứng (ffprobe/ffmpeg), và checklist audit workflow GemLogin/Automa (đứt luồng, kill-switch, hardcoded path).
- `references/tiktok-account-buy-sell-valuation.md` — Framework định giá và forensics khi đánh giá kênh rao bán: like/follow ratio taxonomy, công thức content "cảm xúc vô danh" (faceless nostalgia/sad), risk matrix mua acc đã có Affiliate, câu hỏi due-diligence trước khi mua.
- `references/ai-gated-video-crawling-and-distribution.md` — Kiến trúc kiểm duyệt tự động 100% bằng AI (ViT ONNX vision + NLP blacklist, CẤM bắt user tự soi mắt), chiến lược phân phối video 2 tầng (Độc quyền 1 người vs Bể gộp chia đều tất cả kênh thiếu), và cờ --clean-old dọn sạch kho render cũ.
