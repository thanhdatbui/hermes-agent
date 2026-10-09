# TikTok Rest Day Upload Cadence & Scraping Discipline (2026-09-21)

## 1. Kỷ luật Bóc Tách Kênh Đối Thủ / Học Hỏi (Anti-Hallucination on Scraped Data)

### Bài học từ User Correction (2026-09-21):
- *"Xàm quá mày sao biết 74 ngày đi follow 705 ng..."*
- *"Ủa tính ra mày đi cào dữ liệu, xong h quay lại hỏi ngược tao"*
- *"Ông a vẫn nuôi lướt xem mà, sao m biết k mà phá / Mà phán"*

### Quy tắc bất biến:
1. **CẤM suy diễn hành vi từ metadata tĩnh không có timestamp:**
   - Số `Following` hiện tại (ví dụ 705 following) KHÔNG có timestamp trong API công khai. Tuyệt đối CẤM suy diễn "nick đi follow dạo 705 người trong lúc ngâm".
   - Khoảng cách ngày tạo (từ Snowflake ID) → ngày đăng video đầu tiên chỉ là mốc thời gian, KHÔNG chứng minh người ta có "kỷ luật ngâm acc 74 ngày" hay chỉ đơn giản là nick cá nhân chưa dùng.
   - CẤM TUYỆT ĐỐI phán bừa người khác "chỉ nuôi tay không có hành vi lướt feed" khi không có dữ liệu hiện trường.
2. **Cào dữ liệu là phải tự đào sâu nội dung, CẤM hỏi ngược user:**
   - Khi user yêu cầu cào kênh để đánh giá/học hỏi: Agent BẮT BUỘC phải download video top, extract frames qua ffmpeg, chạy WinRT OCR hoặc browser_vision, bóc tách audio qua speech-to-text để xác định chính xác ngách nội dung (personality quiz, xổ số, nhạc cảnh...).
   - Tuyệt đối CẤM cào xong metadata rồi quay sang hỏi user "kênh này làm chủ đề gì vậy bác?".

---

## 2. Quy luật Cadence Upload vs Ngày Dưỡng Sinh (Rest Day Lifecycle Invariant)

### Dữ liệu thực tế đối soát từ Farm (21/09/2026):
- Đọc DB `D:/Taadaa/data/tiktok_tracker.db` (bảng `snapshots` JOIN `account_mapping`) đối soát các nick có số lượng video nhiều nhất (25-29 video):
  - **Máy 18 (`@hakha18062003`):** 26 video, tổng view 3.534, view TB 136, view gần nhất tụt dốc: 423 → 372 → 124 → 131 → 72.
  - **Máy 31 (`@lu.huyn926`):** 26 video, tổng view 3.871, view TB 149, view kẹt: 169 → 153 → 160 → 370 → 120.
  - **Máy 38 (`@thy.dung1828`):** 29 video, tổng view 7.866, view TB 271, view tụt dốc: 392 → 365 → 357 → 330 → 68.
  - **Máy 21 (`@labaozmh1x8`):** 25 video, tổng view 4.202, view TB 168, kẹt mức 115 → 136 → 133 → 116 → 261.
- **Tần suất upload khi cho phép đăng cả ngày dưỡng sinh:** 1-2 ngày/video liên tục (12/09, 15/09, 16/09, 18/09, 21/09).
- **Hậu quả:** 
  - Kênh bị kẹt cứng ở **200-view limbo** (135 - 271 view). Càng đăng dày thì view các video sau càng tụt thê thảm về 68 - 72 view (chạm đáy).
  - Tỷ lệ tương tác (ER = Likes/Views) của các nick này rất cao (7% - 13%), chứng minh nội dung không tệ, nhưng thuật toán TikTok đánh giá đăng quá dày là hành vi **spam / low-quality pool**, không cấp thêm luồng thử nghiệm mới.

### So sánh với kênh triệu view (@trn.t.t85):
- Kênh cắn viral 988K, 591K, 320K view có nhịp đăng trung bình **2-4 ngày/video** (trung bình ~3 ngày/video).
- Thuật toán TikTok cần khoảng **48-72 giờ** để phân phối video qua các vòng thử nghiệm (test pools). Đăng dồn dập khiến video mới đè bẹp luồng phân phối của video cũ.

### Quy tắc Bất Biến Ngày Dưỡng Sinh:
```python
# Quy tắc: Dưỡng sinh = 0 Follow + 0 Upload (chỉ lướt feed ngắm video thuần túy).
# Giữ nhịp đăng tự nhiên ~3 ngày/1 video per account.
```

### Vị trí code điều khiển (`flows/multi_machine_feed_session.py`):
```python
    upload_row = int(getattr(account, "account_row_index", 1) or 1)
    child_cfg = getattr(child_ctx, "config", None) or {}
    is_organic = child_cfg.get("_is_organic_rest")
    if is_organic is None:
        is_organic = _is_account_organic_rest_day(getattr(account, "machine", 0), upload_row)
        if isinstance(child_ctx.config, dict):
            child_ctx.config["_is_organic_rest"] = is_organic

    # Quy tắc Lifecycle (revert 2026-09-21): Dưỡng sinh = 0 Follow + 0 Upload.
    # Data thực tế cho thấy đăng video ngày dưỡng sinh khiến nhịp quá dày (1-2 ngày/video)
    # → TikTok gắn cờ spam → view bị bóp. Ngày dưỡng sinh chỉ lướt feed, không tương tác ngoại vi.
    if is_organic:
        payload = {
            "machine": account.machine,
            "row": upload_row,
            "status": "skipped",
            "reason": "organic-rest-day-upload-disabled",
        }
        _write_upload_result(child_ctx, payload)
        return payload
```

---

## 3. TikTok Snowflake ID Timestamp Extraction

ByteDance Snowflake ID 64-bit:
- **32-bit cao nhất (`ID >> 32`):** Unix timestamp (seconds).
- **User ID:** Thời điểm tạo tài khoản chính xác đến từng giây.
- **Video ID:** Thời điểm video được publish lên hệ thống chính xác đến từng giây.

```python
import datetime

user_id = 7614058181921326098
ts = user_id >> 32
created_time_vn = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc) + datetime.timedelta(hours=7)
# => 2026-03-06 15:34:27 (GMT+7)
```
