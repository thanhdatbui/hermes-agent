# Timing Budget & Video Range Cho Feed Session TikTok (Chốt 22/08/2026)

## 1. Cấu hình hằng số chuẩn
Trong `D:\Taadaa\tiktok-luot nuoi acc\python_runner\flows\multi_machine_feed_session.py`:
```python
FEED_SESSION_MIN_TOTAL_VIDEOS = 10
FEED_SESSION_MAX_TOTAL_VIDEOS = 14
DEFAULT_DEVICE_TIMEOUT_SECONDS = 1500.0  # 25 phút
```

## 2. Ngân sách thời gian (Timing Budget trên Galaxy S7)
- **Setup ban đầu (mở TikTok, xác thực Profile preflight):** ~2.5 phút (150 giây).
- **Mỗi video lướt qua:** ~40–50 giây (Watch delay 2–8s + swipe kéo + chụp màn hình + dump UI XML qua ATX port 7912 + duyệt qua ~17 popup handler).
- **Kịch bản trung bình (12 video):** `12 × 45s + 150s = 690s` (~11.5 phút). Dư ~13.5 phút so với trần 25 phút.
- **Kịch bản tối đa (14 video):** `14 × 50s + 150s = 850s` (~14.2 phút). Dư **10.8 phút buffer an toàn**, dù có gặp 4-5 video mạng lag hay quét popup retry liên tục cũng không chạm trần 1500s.
- **CẢNH BÁO:** Không nâng trần lên 25–30 video vì trên máy S7 cũ sẽ mất 26–30 phút, gây lỗi `run plan max_duration_seconds exceeded before capture swipe_XX_after`.

## 3. Tải trọng an toàn 1 ngày (Daily Load per Machine & Account)
- **Phân bổ theo 3 Block trong ngày:**
  - Block 1 (Sáng 06:00 – 10:30): Account A chạy 3 phiên nhỏ (cách nhau 40–50 phút).
  - Block 2 (Chiều 12:00 – 17:00): Account B chạy 3 phiên nhỏ (cách nhau 40–55 phút).
  - Block 3 (Tối 18:30 – 23:30): Account A chạy 3 phiên nhỏ (cách nhau 45–55 phút).
  - Đêm (00:00 – 06:00): Nghỉ hoàn toàn.
- **Tổng cộng:**
  - 1 máy chạy 6–9 phiên/ngày (tổng thời gian hoạt động thực tế ~1.5 – 2.5 tiếng / 24 tiếng, ngủ nghỉ ~90% thời gian).
  - 1 account xem ~40–70 video/ngày: hành vi cực kỳ tự nhiên, không bị spam liên tục.
