# Dual Gate (30d/10v) & Streak 4+ Deep Quarantine (15 Days)

## 1. Empirical Origin (Tran Ty Ty Farm Reverse-Engineering)

Khảo sát đối soát thực tế toàn bộ 696 nick Following và mẫu 600 Followers của kênh mẫu `@trn.t.t85` (Trần Tý Tý / GemPhone):
- **Phát hiện mạng lưới Seeding Chéo Nội Bộ (Mutual Seeding):** 94/600 followers trùng khớp 100% với following list. Dàn 550 nick vệ tinh tự follow chéo lẫn nhau để tạo đệm Inbound Trust (~540 follower trần nội bộ).
- **Trần 200 view của dàn vệ tinh:** Toàn bộ dàn vệ tinh kẹt ở mức 140–258 view/video, đăng thưa 3–5 ngày/clip từ tháng 3/2026 đến tháng 10/2026. Chỉ có duy nhất 1 clip của Trần Tý Tý cắn đề xuất (988K view).
- **Nguyên nhân gốc rễ nhả follow:** Nick farm Taadaa bị TikTok silent-drop vì **Cold Outbound** (tài khoản non đi follow người lạ khi Inbound Trust = 0). TikTok lọc sạch các lượt follow từ tài khoản thiếu tín hiệu người dùng thật.

---

## 2. Dual Gate Policy (2026-10-06)

Trích xuất logic trong `follow_runner/core/follow_state.py` (`session_budget`):

```python
# Điều kiện bắt buộc để đi follow:
if account_age_days is not None:
    if account_age_days < 30 or video_count is None or video_count < 10:
        budget = 0  # BỊ CHẶN HOÀN TOÀN (Cold Outbound Guard)
    elif self.is_post_cooldown_warmup:
        budget = _random.randint(3, 5)
    else:
        budget = _range(1)  # Full budget 10-20
elif video_count is not None and int(video_count) >= 10:
    budget = _range(1)
else:
    budget = 0
```

### Xóa bỏ hoàn toàn "Giai đoạn Mồi" (Warmup 21–30 ngày):
- **Trước 2026-10-06:** Nick 21–30 ngày hoặc < 10 video được cấp 3–5 follow/phiên để "mồi".
- **Từ 2026-10-06 (User chốt):** XÓA BỎ HOÀN TOÀN. Nick chưa đủ 30 ngày VÀ chưa đủ 10 video có budget = 0.
- **Lý do:** Thả nick non đi follow sớm dù chỉ 3-5 nick vẫn bị TikTok gắn cờ bot/spammer và silent-drop, gây lãng phí tài nguyên và làm hỏng tài khoản.

---

## 3. Progressive Backoff: Tầng Cooldown Streak >= 4 (15 Ngày)

Khi nick bị TikTok nhả follow (`set_follow_failed()`):
- **Streak 1 (Lần đầu):** Cooldown 3 ngày (+3 ngày đến 23:59:59 local).
- **Streak 2 (2 lần liên tiếp):** Cooldown 5 ngày (+5 ngày).
- **Streak 3 (3 lần liên tiếp):** Cooldown 7 ngày (1 tuần).
- **Streak >= 4 (Tái phạm nặng):** Cooldown **15 ngày** (Cách ly sâu đối với tín hiệu Persistent Spammer).

### Grace Buffer `max_diff_days = 19`:
- Buffer 19 ngày = 15 ngày cooldown + 4 ngày grace buffer chống lệch timezone/DST hoặc trễ lịch cron ca chạy cách ngày.
- Nếu sau 15 ngày (ví dụ ngày 16): Hết cooldown active, nick chuyển sang `is_post_cooldown_warmup` (budget nhẹ 3-5).
- Nếu quá 19 ngày mà nick mới bị fail lại: Coi như cữ mới, reset fail streak về 1 thay vì cộng dồn tiếp.

---

## 4. Telemetry Semantic Invariant

- `mode_str`: Chỉ ghi `"warmup"` khi `self.is_post_cooldown_warmup` thực sự active (`fail_streak > 0` và `follow_failed == False`).
- Nick đạt chuẩn trưởng thành (`age >= 30` VÀ `video >= 10`) ghi `"full"`.
- Nick bị chặn ghi `"blocked"`.
