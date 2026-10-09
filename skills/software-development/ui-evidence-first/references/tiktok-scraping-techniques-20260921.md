# TikTok Account Scraping — Kỹ thuật bóc tách dữ liệu kênh (2026-09-21)

## 1. Scrape toàn bộ metadata kênh + video

```bash
yt-dlp --flat-playlist --dump-json "https://www.tiktok.com/@<username>"
```

Trả về 1 dòng JSON per video (NDJSON). Parse:
```python
import json, subprocess
cmd = ["yt-dlp", "--flat-playlist", "--dump-json", "https://www.tiktok.com/@trn.t.t85"]
out = subprocess.check_output(cmd, text=True, encoding="utf-8", errors="replace")
videos = []
for line in out.strip().split("\n"):
    if not line.strip(): continue
    try:
        data = json.loads(line)
        if "id" in data: videos.append(data)
    except: pass
```

Các field quan trọng: `id`, `view_count`, `like_count`, `comment_count`, `save_count`, `repost_count`, `duration`, `upload_date`, `timestamp`, `track`, `title`, `uploader_id`, `channel_id`.

**Note:** `playlist_count` = tổng video kênh (bao gồm cả video private nếu scrape không được thì chỉ lấy được public).

---

## 2. Xác định ngày tạo tài khoản từ Snowflake User ID

TikTok (ByteDance) dùng 64-bit Snowflake ID cho mọi User/Video/Comment. **32 bit cao = Unix timestamp (seconds)**.

```python
import datetime
user_id = 7614058181921326098
ts = user_id >> 32
utc_dt = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
vn_dt = utc_dt + datetime.timedelta(hours=7)
print("Ngày tạo acc (GMT+7):", vn_dt.strftime("%Y-%m-%d %H:%M:%S"))
# => 2026-03-06 15:34:27
```

**Lấy `uploader_id` từ yt-dlp dump JSON** (`data["uploader_id"]`). Áp dụng tương tự cho Video ID để lấy giờ đăng chính xác đến giây.

---

## 3. Download video và extract frame để phân tích nội dung

```bash
# List formats
yt-dlp -F "https://www.tiktok.com/@<user>/video/<id>"

# Download format cụ thể
yt-dlp -f "h264_540p_*" -o "vid.mp4" "https://www.tiktok.com/@<user>/video/<id>"

# Extract frame tại giây N
ffmpeg -y -ss <N> -i vid.mp4 -vframes 1 frame.jpg
```

**Workflow đọc nội dung video:**
1. Extract 3-5 frames (2s, 8s, 15s, 25s, cuối) → WinRT OCR mỗi frame.
2. Nếu OCR ra text méo (Latin charset đọc tiếng Việt): dùng `browser_vision` mở file local → mô tả bằng vision model.
3. Extract audio → `speech_recognition.recognize_google(audio, language="vi-VN")` để nhận dạng lời nói/nhạc nền.

---

## 4. Extract và nhận dạng audio

```python
import subprocess, speech_recognition as sr

# Convert sang WAV 16kHz mono
subprocess.run(["ffmpeg", "-y", "-i", "vid.mp4", "-vn", "-c:a", "pcm_s16le", "-ar", "16000", "-ac", "1", "audio.wav"], capture_output=True)

r = sr.Recognizer()
with sr.AudioFile("audio.wav") as source:
    audio = r.record(source)
    try:
        text = r.recognize_google(audio, language="vi-VN")
        print("Audio text:", text)
    except: pass
```

**Speech_recognition.recognize_google** gọi Google Speech API miễn phí (rate limit nhẹ). Hoạt động tốt cho tiếng Việt thông thường.

---

## 5. Pitfalls quan trọng

| Pitfall | Fix |
|---|---|
| WinRT OCR dùng en-US đọc tiếng Việt → ra text méo (`Å`, `ä`, `ï`) | Dùng `browser_vision` mở file local JPG để model vision đọc trực tiếp |
| `speech_recognition.UnknownValueError` với `recognize_google` | File âm thanh quá nhiều nhạc nền, ít lời. Thử crop đoạn 5-10s có lời nói rõ nhất |
| Scrape metadata thành công nhưng download video bị WAF | yt-dlp bypass OK nếu không cần watermark. Format `h264_540p_*` là stable |
| f-string với nested quotes trong Python `-c string` | Dùng biến trung gian thay vì `v.get(\"id\")` trực tiếp trong f-string |
| Khoảng cách ngày tạo acc → video đầu = "ngâm" | CẤM suy diễn. Chỉ là khoảng cách thời gian, không biết hành vi trong đó |
| Following count hiện tại ≠ hành vi nuôi acc | API không có timestamp follow history. Cấm diễn giải "74 ngày đi follow 705 người" |
| Phán bừa người khác nuôi tay không lướt feed | CẤM phán đoán vô căn cứ khi không có dữ liệu hiện trường |
| Cào dữ liệu xong quay lại hỏi ngược user chủ đề | BẮT BUỘC extract frame + OCR + vision + speech-to-text tự bóc tách chủ đề trước khi trả lời |
| Đăng video cả ngày dưỡng sinh (1-2 ngày/video) | Làm nhịp đăng quá dày → kẹt 200-view limbo (view tụt về 68-72 dù ER cao 7-13%). Bắt buộc: Dưỡng sinh = 0 Follow + 0 Upload, giữ nhịp ~3 ngày/video |

---

## 6. Dữ liệu KHÔNG bóc được từ yt-dlp (cần browser authenticated hoặc API private)

- Follower count / Following count (lấy từ browser snapshot `browser_navigate` + đọc AX snapshot — `heading "705 Following 7600 Followers"`)
- Bio (từ AX snapshot: `heading "No bio yet."`)
- Video comment text (chỉ có count)
- Thông tin âm thanh trending (chỉ có track name)
- Account Health / FYP eligibility status
- Watch time %, traffic source (FYP vs Search vs Follower), audience demographics — chỉ có TikTok Studio chính chủ

### Profile data via browser_navigate (không cần login):
```python
# browser_navigate("https://www.tiktok.com/@username")
# AX snapshot trả về heading:
# "705 Following 7600 Followers"  → parse regex
# "88.2K Likes"
# "No bio yet."
# Lưu ý: TikTok WAF popup captcha ("Drag slider") chỉ chặn browser render,
# KHÔNG chặn yt-dlp scrape API ngầm. Hai luồng độc lập.
```

---

## 7. Phân tích kênh cạnh tranh — workflow đầy đủ

```
1. yt-dlp --flat-playlist --dump-json → 35 video metadata
2. browser_navigate profile → follower/following/likes (AX snapshot)
3. user_id >> 32 → ngày tạo acc
4. yt-dlp -f h264 -o vid.mp4 <top_video_url> → download top 3 video
5. ffmpeg extract frames → WinRT OCR hoặc browser_vision → xác định nội dung
6. ffmpeg extract audio → wav → speech_recognition.recognize_google vi-VN → nhận dạng lời/nhạc
7. Tổng hợp + delegate_task → Sol phân tích patterns, engagement metrics, blueprint
```

**Engagement metrics quan trọng:**
- ER = Likes/Views (benchmark TikTok VN <50K followers: 2-4%)
- Save rate = Saves/Views (>0.1% = tốt, >0.3% = exceptional)
- Repost rate = Reposts/Views (>0.05% = viral potential)

---

## 8. Đọc cron + script farm trước khi hỏi user

Khi user hỏi "số liệu farm của tao thế nào" → BẮT BUỘC đọc thực tế trước:
```bash
hermes cron list                    # xem toàn bộ scheduled jobs
cat scripts/hermes_cron_schedule.json  # xem cấu hình picker/runner/watcher
grep -n "FEED_SESSION_MIN\|FEED_SESSION_MAX\|DEFAULT_FOLLOW" flows/multi_machine_feed_session.py
```

Constants quan trọng đã tìm ra cho farm Taadaa:
- `FEED_SESSION_MIN_TOTAL_VIDEOS = 16`, `MAX = 22`, `MAX_SWIPES = 28`
- `DEFAULT_FOLLOW_HOOK_TIMEOUT_SECONDS = 1200.0` (20 phút)
- `DEFAULT_FOLLOW_MAX_CONCURRENCY = 15`
- `DEFAULT_UPLOAD_MAX_CONCURRENCY = 20`
- Cadence: max 2 feed sessions/ngày/acc (`successes_today >= 2` → skip)
- Gate follow: nick phải có `>= 10 video` mới được follow
- Block anchors: `"06:00", "12:00", "18:00", "00:00"` với jitter ±25p
- Like rate tại Deep Inspect: 40%, Follow rate: 20%
