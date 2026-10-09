# Cơ chế Tương tác Feed & Fast Swipe (tiktok-luot nuoi acc)

Tài liệu tham chiếu chuẩn cho logic tương tác Feed trong file `flows/feed_swipe_smoke.py`:

## 1. Tỉ lệ Thả tim (Like Rate) theo Feed Tab
- **For You (Đề xuất):** Mặc định 8%. Khi rơi vào nhịp Deep Inspect nâng lên 40% (`DEFAULT_DEEP_LIKE_RATE_PERCENT`) để bù cho các video lướt nhanh không like.
- **Following (Đang follow):** Mặc định 50% (`DEFAULT_FEED_LIKE_RATES["following"]`).
- **Friends (Bạn bè):** Mặc định 80% (`DEFAULT_FEED_LIKE_RATES["friends"]`).

## 2. Tỉ lệ Đọc Comment (Comment Peek)
- **Phân phối:** Động theo phiên 20% – 35% (`session_comment_peek_rate = random.randint(20, 35)`).
- **Phạm vi áp dụng:** Áp dụng như nhau trên mọi feed type, KHÔNG phân biệt tab.
- **Điều kiện kích hoạt:**
  - Chỉ chạy trên nhịp Deep Inspect (`is_deep_inspect_video`).
  - Phải có bình luận (`comment_count > 0`). Bỏ qua nếu 0 comment hoặc tắt tính năng bình luận (`skip_zero_comments`).

## 3. Cơ chế Fast Swipe vs Deep Inspect
- **Fast Swipe (Lướt nhanh):**
  - Chu kỳ: Cứ 2–4 video lướt nhanh thì có 1 video Deep Inspect (`interval_min=2`, `interval_max=4`).
  - Xem ngắn 2.0s – 5.0s.
  - Vuốt thẳng qua ADB (`adb shell input swipe` có tính toán jitter tọa độ ngẫu nhiên).
  - **KHÔNG dump XML, KHÔNG screencap** giúp tiết kiệm CPU và tránh nghẽn uiautomator.
  - An toàn: Sau khi vuốt chỉ chạy lightweight focus check (`get_focused_activity`). Nếu app bị văng/mất focus thì mới force chuyển Deep Inspect phục hồi.
- **Deep Inspect (Kiểm tra sâu):**
  - Chụp màn hình + dump XML để xử lý popup, quảng cáo tài trợ (sponsored skip), thả tim, follow organic hoặc đọc lướt comment.
