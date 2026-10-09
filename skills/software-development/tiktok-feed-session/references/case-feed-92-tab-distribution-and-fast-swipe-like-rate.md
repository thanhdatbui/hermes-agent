# Case Feed-92: Chuẩn Hóa Phân Bổ Tab 50/25/25 & Nâng Tỷ Lệ Thả Tim Following/Bạn Bè (Giữ Nguyên Fast Swipe)

## 1. Bối cảnh & Hiện tượng (2026-10-03)
- User kiểm tra thực tế ca nuôi nick (Row 1/2) và phát hiện tỷ lệ thả tim (like) thực tế chỉ loanh quanh 10% – 20% dù các nick đã có bạn bè và following đầy đủ.
- Trích xuất dữ liệu log 80 máy ca sáng (Row 1):
  - **Tab Following:** Chỉ đạt 10.3% – 11.3% like (8-12 máy có xem, 4-8 lượt like trên 39-71 video).
  - **Tab Bạn bè (Friends):** Đạt 13.6% – 23.3% like (8-16 máy có xem, 6-21 lượt like trên 44-90 video).
  - **Tổng toàn ca:** Chỉ đạt 11.8% – 13.6% like trên tổng số ~1.300 - 1.400 video.

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Pha loãng do cơ chế Fast Swipe (Lướt nhanh):**
   - Trong 1 phiên nuôi (16–22 video), cơ chế Fast Swipe xen kẽ: Cứ xem kỹ 1 video (Deep Inspect) thì lại lướt nhanh 2–4 video tiếp theo.
   - Các video lướt nhanh hoàn toàn KHÔNG thả tim (like = 0%) để tiết kiệm CPU và không dump XML.
   - Dù cấu hình Deep Inspect là 35% (Following) và 65% (Bạn bè), nhưng tính trên toàn bộ số video của tab thì bị chu kỳ 2–4 fast swipe pha loãng xuống chỉ còn ~10% – 20%.
2. **Tỷ lệ ghé thăm tab cũ lệch về For You (70/15/15):**
   - Phân bổ cũ: 70% For You, 15% Following, 15% Bạn bè.
   - Với phiên ngắn ~18 video, việc bốc thăm mỗi 3–8 video khiến hơn 80% máy không bao giờ chuyển sang tab Following hay Bạn bè.

## 3. Quyết định & Chỉ đạo của User
- **CẤM TẮT FAST SWIPE:** User chỉ đạo rõ: *"Tăng tỉ lệ, k tắt fast swipe, làm đi"*. Fast swipe bắt buộc giữ nguyên 100% để bảo vệ hiệu năng máy farm, chống lag UI/quá tải CPU.
- **GIỮ NGUYÊN CHU KỲ LƯỚT:** User chỉ đạo: *"Giữ nguyên chu kì lướt chỉ tăng tỉ lệ thả tim lên cao hơn nữa để đạt con số mong muốn"*. Giữ nguyên nhịp 2–4 video lướt nhanh xen kẽ 1 video xem kỹ cho tất cả các tab.
- **CÂN BẰNG PHÂN BỔ TAB:** Chốt tỷ lệ mới: **`50% For You / 25% Following / 25% Bạn bè`** (50-25-25) để tăng gấp đôi cơ hội các máy ghé thăm tab của nhau.

## 4. Chuẩn hóa kiến trúc & Code (`feed_swipe_smoke.py`)
1. **Phân bổ tab (`DEFAULT_FEED_DISTRIBUTION`):**
   ```python
   DEFAULT_FEED_DISTRIBUTION = {
       FEED_TYPE_FOR_YOU: 0.50,
       FEED_TYPE_FOLLOWING: 0.25,
       FEED_TYPE_FRIENDS: 0.25,
   }
   ```
2. **Tỷ lệ thả tim nhịp xem kỹ (`_deep_like_rate` khi Fast Swipe bật):**
   ```python
   if current_feed_type == FEED_TYPE_FOR_YOU:
       _deep_like_rate = fast_swipe["deep_like_rate_percent"]
   elif current_feed_type == FEED_TYPE_FRIENDS:
       _deep_like_rate = 95  # Nâng lên 95% (gần như gặp video bạn bè xem kỹ là like)
   else:
       _deep_like_rate = 85  # Following nâng lên 85%
   ```
3. **Cấu hình nền & Dải mềm động:**
   - `DEFAULT_FEED_LIKE_RATES`: Following `65%`, Bạn bè `85%`.
   - `_feed_like_rates`: Following ngẫu nhiên `55% – 75%`, Bạn bè ngẫu nhiên `75% – 95%`.

## 5. Đồng bộ kiểm thử (Unit Tests)
- Cập nhật đồng bộ các assertions trong:
  - `python_runner/tests/test_feed_like_rates.py`
  - `python_runner/tests/test_feed_swipe_smoke.py`
- Lệnh verify độc lập < 5s:
  ```bash
  PYTHONPATH="D:/Taadaa/tiktok-luot nuoi acc/python_runner;D:/Taadaa/tiktok-luot nuoi acc/python_runner/tests" python -m unittest python_runner.tests.test_feed_like_rates python_runner.tests.test_feed_swipe_smoke.FastSwipeDeepInspectTests.test_friends_and_following_feed_distribution_and_like_rates
  ```
  Kết quả đạt 17/17 tests passed (0.015s).
