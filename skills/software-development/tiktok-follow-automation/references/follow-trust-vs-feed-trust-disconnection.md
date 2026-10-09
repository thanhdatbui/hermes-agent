# TikTok Follow Trust vs Feed Trust: ByteDance Risk Engine Disconnection

## 1. Bản Chất Kỹ Thuật (ByteDance Security SDK Action Scoring)

ByteDance **KHÔNG** sử dụng một điểm Trust Score duy nhất cho toàn bộ tài khoản. Hệ thống chia tách thành các pipeline tính điểm độc lập:

```
┌─────────────────────────────────────────────────────────────┐
│           TIKTOK ACTION TRUST SCORING ARCHITECTURE          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Pipeline 1: Feed / Content Consumption Trust               │
│     - Dwell time, video completion rate, likes, scrolls     │
│     - Rất dễ hồi phục bằng cách cho nick lướt feed          │
│                                                             │
│  Pipeline 2: Relationship / Follow Action Trust             │
│     - Tỷ lệ commit thành công, velocity (follow/phút),      │
│       mức độ tương tác 2 chiều (follow-back rate)           │
│     - BỊ TÁCH BIỆT HOÀN TOÀN VỚI FEED TRUST                 │
│     - Khi rơi vào vùng đỏ (<10/100), KHÔNG HỒI PHỤC         │
│       chỉ bằng việc lướt feed thụ động                      │
│                                                             │
│  Pipeline 3: Session Intent / Fingerprint Integrity         │
│     - Thời gian từ lúc mở app đến khi phát sinh action đầu  │
│     - Mở app <60s đã lao vào Search UID hoặc Following list │
│       sẽ bị đánh dấu ngay là Bot Pattern                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Giải Mã Hiện Tượng "Nghỉ Cooldown 7 Ngày + Lướt Feed Nhưng Bấm 1 Follow Vẫn Bị Phạt Tiếp"

### Tại sao lướt feed không cứu được?
- Việc lướt feed hàng ngày chỉ gửi tín hiệu tích cực vào **Pipeline 1 (Feed Trust)**.
- **Pipeline 2 (Follow Trust)** vẫn đang bị đóng băng ở mức âm/vùng đỏ do tiền án vi phạm cũ (đặc biệt là đợt spam mù do lỗi Case UI-82 trước ngày 02/10).
- TikTok server kiểm tra điều kiện:
  `if follow_trust < MIN_COMMIT_THRESHOLD: silent_drop_action()`
- Dù feed trust cao, khi follow trust dưới ngưỡng, **gói tin follow bị drop ngay lập tức** tại server gate mà không phụ thuộc vào việc nick đã nghỉ bao nhiêu ngày.

### Tại sao không nên nâng Cooldown lên 1 tháng?
- Chu kỳ rolling window và decay của ByteDance cho vi phạm cấp tài khoản là **14 ngày (nửa tháng)**.
- Cooldown 1 tháng biến nick thành tài khoản chết (zombie capacity), lãng phí tài nguyên thiết bị mà không giải quyết được gốc rễ nếu nick không có hành vi mồi.
- **Thang Cooldown chuẩn hóa:**
  - Streak 1: **3 ngày**.
  - Streak 2: **5 ngày**.
  - Streak 3: **7 ngày**.
  - Streak $\ge 4$: **15 ngày** (cách ly sâu 2 tuần, tương ứng 1 chu kỳ decay 14 ngày của TikTok).

---

## 3. Chiến Lược Hồi Phục Follow Trust (Actionable Protocol)

Để phá vỡ vòng lặp bị phạt lại sau cooldown (Streak 3–5), cần thực hiện 2 giai đoạn:

### Giai đoạn 1: Signal Seeding (Ủ Tín Hiệu Gần-Follow)
Trong thời gian cách ly (7–15 ngày cooldown), nick lướt feed phải bổ sung hành vi:
1. Tap vào avatar/tên tác giả từ video trên For You feed để vào Profile cá nhân.
2. Xem 2–3 video trên profile đó (watch time > 60%).
3. Thả tim 1 video.
4. **TUYỆT ĐỐI KHÔNG BẤM NÚT FOLLOW.**
> *Mục đích:* Gửi sự kiện `profile_visit` và `profile_video_watch` vào hệ thống đánh giá của TikTok, chứng minh nick có hành vi quan tâm người dùng một cách tự nhiên.

### Giai đoạn 2: Micro-Follow Probe (Mồi Vi Lượng)
Khi hết hạn cooldown:
1. **CẤM cấp full budget (10–20 follow).**
2. Chỉ cấp **1 follow duy nhất** vào 1 tài khoản lớn có độ uy tín cao (verified hoặc >1M follower).
3. Đợi 24h đối soát qua Web/Path B:
   - Nếu giữ được follow: Kênh Follow Trust bắt đầu hồi phục $\rightarrow$ nâng lên mức warmup (3–5 follow).
   - Nếu vẫn bị drop: Tiếp tục cách ly 15 ngày và chạy lại Signal Seeding.
