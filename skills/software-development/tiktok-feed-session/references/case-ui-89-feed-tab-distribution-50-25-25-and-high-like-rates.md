# Case UI-89: Chuẩn hóa Phân Bổ Tab 50/25/25 & Tăng Kịch Khung Tỷ Lệ Thả Tim Nuôi Acc (2026-10-03)

## 1. Hiện trường & Phân tích Log Thực tế (Ca Row 1 ngày 2026-10-03)
- **Triệu chứng đối soát từ User:** Tỷ lệ like thực tế trong các ca nuôi acc luôn chỉ quanh quẩn 11% – 14%, kể cả với các nick hàng đầu (Row 1, Row 2) đã có sẵn bạn bè và following.
- **Dữ liệu thực tế bóc tách từ 80 máy Farm Kibe (Ca 06:00 & Ca 08:00):**
  - Ca 06:00: Tổng like toàn ca chỉ đạt `190 / 1.399 video` (13.6%). For You: 13.0%, Following: 10.3%, Bạn bè: 23.3%. Hơn 64/80 máy không hề ghé tab Bạn bè.
  - Ca 08:00: Tổng like toàn ca chỉ đạt `154 / 1.303 video` (11.8%). For You: 11.8%, Following: 11.3%, Bạn bè: 13.6%.
- **Hai nguyên nhân cốt lõi trong code (`feed_swipe_smoke.py`):**
  1. *Cơ chế Fast Swipe (Lướt nhanh xen kẽ):* Trong 1 phiên nuôi (16–22 video), cứ 1 video xem kỹ (Deep Inspect) thì có 2–4 video lướt nhanh (Fast Swipe không dump XML, like = 0%). Dù cấu hình like cao ở nhịp xem kỹ, nhưng tỷ lệ này bị chu kỳ lướt nhanh pha loãng xuống chỉ còn 1/3 ~ 1/4.
  2. *Phân bổ tab cũ 70/15/15:* Tỷ lệ chọn tab Đề xuất (For You) chiếm tới 70%. Trong phiên ngắn 18 video, thuật toán đổi tab mỗi 3–8 video chỉ kích hoạt 2–3 lần. Do đó hơn 75% số máy ở lì trong tab For You suốt phiên, không bao giờ chuyển sang Following hay Bạn bè.

## 2. Quyết định Nghiệp vụ & Kỷ luật Vận hành
- **Giữ nguyên 100% chu kỳ lướt (Không tắt Fast Swipe):** User chỉ đạo giữ nguyên nhịp Fast Swipe 2–4 video lướt nhanh xen kẽ 1 video xem kỹ để đảm bảo máy farm duy trì hiệu năng mượt, không dump XML liên tục gây lag hoặc quá nhiệt.
- **Bù trừ bằng cách tăng kịch khung tỷ lệ thả tim ở nhịp xem kỹ (Deep Inspect):**
  - **Tab Bạn bè (Friends):** Nâng tỷ lệ thả tim Deep Inspect từ `65%` lên **`95%`** (gần như gặp video bạn bè nào được xem kỹ là thả tim ngay). Cấu hình nền `DEFAULT_FEED_LIKE_RATES[FEED_TYPE_FRIENDS] = 85` (dải phân phối mềm động: `75% – 95%`).
  - **Tab Following:** Nâng tỷ lệ thả tim Deep Inspect từ `35%` lên **`85%`**. Cấu hình nền `DEFAULT_FEED_LIKE_RATES[FEED_TYPE_FOLLOWING] = 65` (dải phân phối mềm động: `55% – 75%`).
- **Cân bằng lại tỷ lệ phân bổ tab (`DEFAULT_FEED_DISTRIBUTION`):**
  - Chuyển từ `70% / 15% / 15%` sang **`50% For You / 25% Following / 25% Bạn bè`**.
  - Tăng gấp đôi tần suất ghé thăm tab của nhau trong farm, giúp các nick tương tác chéo đều đặn.

## 3. Các vị trí Code & Test bắt buộc đồng bộ
1. `python_runner/flows/feed_swipe_smoke.py`:
   - `DEFAULT_FEED_DISTRIBUTION`: `{for-you: 0.50, following: 0.25, friends: 0.25}`.
   - `DEFAULT_FEED_LIKE_RATES`: `{for-you: 15, following: 65, friends: 85}`.
   - `_feed_like_rates()` dải mềm: `following: (55, 75)`, `friends: (75, 95)`.
   - `_feed_session_flow()` deep like rates: `following: 85`, `friends: 95`.
2. Đồng bộ assertion trong 2 file unit test:
   - `python_runner/tests/test_feed_like_rates.py`
   - `python_runner/tests/test_feed_swipe_smoke.py`
   - Lệnh verify: `PYTHONPATH="python_runner;python_runner/tests" python -m unittest python_runner.tests.test_feed_like_rates python_runner.tests.test_feed_swipe_smoke.FastSwipeDeepInspectTests.test_friends_and_following_feed_distribution_and_like_rates`.
