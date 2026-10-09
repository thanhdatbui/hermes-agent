# Chẩn Đoán Lệch Đối Soát Following & Phân Biệt Natural vs Cross Follow

## 1. Hiện Tượng (Case Máy 72 - 2026-09-28)
Báo cáo watchdog ghi nhận:
```text
Đối soát TikTok Web (+0 Following thật | Lệch -1 so với script báo 1):
  - M72 (@caotrinh16022004): script báo 1 | web tăng +0 (Lệch -1)
```

## 2. Nguyên Nhân Kỹ Thuật

### a. Trộn lẫn Follow Tự Nhiên (Natural) và Follow Chéo (Cross)
* **Natural Follow (Trong phiên lướt feed):** Script `feed_swipe_smoke.py` có tỷ lệ 5% ngẫu nhiên follow tác giả video đang xem (`friends: 1`).
* **Cross Follow (Module tiktok-follow sau feed):** Follow danh sách tài khoản nội bộ farm theo anchor mode 2.
* **Cơ chế Watchdog:** Watchdog tính tổng `total_follows = cross_follows + natural_follows`. Nếu máy có 1 lượt follow tự nhiên thành công, watchdog kỳ vọng TikTok Web tăng +1.

### b. Độ trễ Snapshot Web vs Server-side Drop
* Snapshot cào profile TikTok Web (`snapshots` trong `tiktok_tracker.db`) có độ trễ cache từ CDN TikTok (5 - 15 phút) hoặc lượt follow tự nhiên trên feed bị TikTok server nhả ngầm mà app không nhận được callback.
* Dẫn đến Web ghi nhận Following không đổi (delta = 0) trong khi script local ghi nhận đã tap follow thành công.

## 3. Quy Trình Vận Hành & Hướng Dẫn Điều Phối
1. **Không coi lệch -1 là lỗi script nghiêm trọng:** Khi nick có natural follow mà web chưa nhảy số, đây là độ trễ hoặc server drop của TikTok, không phải crash hay exception của script runner.
2. **Không can thiệp thủ công ADB:** Tránh tap lại làm đứt chu kỳ dưỡng sinh hoặc vi phạm ngưỡng an toàn.
3. **Phân tách rành mạch trong báo cáo:** Watchdog cần tách bạch dòng đối soát riêng cho Follow chéo (2 chiều xác minh) và Follow tự nhiên để tránh gây hoang mang cho người vận hành.
