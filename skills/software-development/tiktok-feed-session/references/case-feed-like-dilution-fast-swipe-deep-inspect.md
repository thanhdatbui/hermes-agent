# Hiện Tượng Pha Loãng Tỷ Lệ Thả Tim Do Fast Swipe & Quy Tắc Giữ Nguyên Chu Kỳ Vuốt (2026-10-03)

## 1. Bản Chất Hiện Tượng Pha Loãng (Dilution Effect)
- Trong luồng nuôi acc (`feed_swipe_smoke.py`), cơ chế **Fast Swipe** xen kẽ 2–4 video lướt nhanh (chỉ xem 2–5s, không dump XML, like = 0%) với 1 video **Deep Inspect** (dump XML, kiểm tra an toàn và thả tim).
- Tỷ lệ video Deep Inspect trong phiên thực tế chỉ chiếm **25% – 30%** tổng số video.
- Dù cấu hình like rate lý thuyết là 35% (Following) và 45% (Bạn bè), nhưng khi bị Fast Swipe pha loãng:
  - Tỷ lệ like thực tế toàn ca chỉ đạt **10% – 14%** (ngang với For You 12–16%).
  - Trên 80 máy chạy thật, tỷ lệ like Following chỉ đạt ~10.3% – 11.3%, Bạn bè đạt ~13.6% – 23.3%.

## 2. Kỷ Luật Vận Hành Khi Điều Chỉnh Theo Yêu Cầu User
- **YÊU CẦU CỐT LÕI TỪ USER:** "Tăng tỉ lệ, k tắt fast swipe, làm đi", "Giữ nguyên chu kì lướt chỉ tăng tỉ lệ thả tim lên cao hơn nữa để đạt con số mong muốn".
- **QUY TẮC BẮT BUỘC:**
  1. **TUYỆT ĐỐI KHÔNG TẮT FAST SWIPE:** Tắt fast swipe sẽ khiến mọi video đều dump XML, làm nóng máy, nghẽn CPU và tăng rủi ro crash UI trên 80–160 máy chạy song song.
  2. **GIỮ NGUYÊN 100% CHU KỲ VUỚT:** Giữ nguyên `videos_until_deep_inspect = random.randint(fast_swipe["interval_min"], fast_swipe["interval_max"])` (2–4 video) trên mọi tab (For You, Following, Bạn bè). Không tự ý hạ chu kỳ lướt nếu User đã yêu cầu giữ nguyên.
  3. **BÙ TỶ LỆ BẰNG CÁCH NÂNG KỊCH KHUNG DEEP LIKE RATE:**
     - Tab Bạn bè (`FEED_TYPE_FRIENDS`): Nâng `_deep_like_rate` lên **95% – 100%** (gặp video bạn bè ở nhịp Deep Inspect là chắc chắn thả tim). Tỷ lệ nền nâng lên 85% (mềm động: 75% – 95%).
     - Tab Following (`FEED_TYPE_FOLLOWING`): Nâng `_deep_like_rate` lên **85%**. Tỷ lệ nền nâng lên 65% (mềm động: 55% – 75%).
     - Sau khi bù trừ chu kỳ Fast Swipe, tỷ lệ like thực tế trên tổng video bạn bè sẽ đạt **~35% – 45%**, và Following đạt **~25% – 30%** mà không làm thay đổi nhịp lướt tự nhiên của máy.

## 3. Đồng Bộ Hóa Test Suite
- Khi thay đổi `DEFAULT_FEED_LIKE_RATES` và dải phân phối mềm `_feed_like_rates`, BẮT BUỘC cập nhật đồng thời 2 file test:
  - `python_runner/tests/test_feed_like_rates.py`
  - `python_runner/tests/test_feed_swipe_smoke.py` (`FastSwipeDeepInspectTests`)
- Lệnh verify focused < 5s:
  `PYTHONPATH="python_runner;python_runner/tests" python -m unittest python_runner.tests.test_feed_like_rates python_runner.tests.test_feed_swipe_smoke.FastSwipeDeepInspectTests.test_friends_and_following_feed_distribution_and_like_rates`
