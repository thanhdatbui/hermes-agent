# Case 143: Tối Ưu Phân Bổ Feed Nuôi & Tách Biệt Tỷ Lệ Like Đẩy Tương Tác Chéo

## 1. Bối cảnh & Vấn đề thực tế (08/09/2026)
- **Phân bổ xem tab cũ:** 85% Đề xuất (For You), 8% Following, 7% Bạn bè. Trong phiên nuôi ngắn 12-15 video, 7% Bạn bè khiến nhiều phiên không ghé tab Bạn bè lượt nào, làm giảm hiệu quả nuôi tương tác đẩy view chéo nội bộ dàn máy.
- **Tỷ lệ like cũ:** 8% For You, 15% Following, 25% Bạn bè.
- **Bug Fast Swipe override like rate:** Tại nhịp Deep Inspect trong `feed_swipe_smoke.py`, logic áp dụng tỷ lệ bù `deep_like_rate_percent` (40%) chung cho mọi tab khi không có config tường minh:
  ```python
  if (
      is_feed_session
      and fast_swipe["enabled"]
      and ctx.config.get("_like_rate", _feed_session_config(ctx).get("like_rate")) is None
  ):
      _deep_like_rate = fast_swipe["deep_like_rate_percent"]  # 40%
  else:
      _deep_like_rate = like_rates.get(current_feed_type, like_rate_percent)
  ```
  Hậu quả: Khi bot chuyển sang tab Bạn bè hoặc Following (vốn 100% chạy Deep Inspect, không có Fast Swipe), tỷ lệ like vẫn bị ép thành 40% thay vì lấy đúng cấu hình riêng của tab đó.

## 2. Thông số chuẩn hóa (Case 143)
1. **Phân bổ lượt xem (`DEFAULT_FEED_DISTRIBUTION`):**
   - **Đề xuất (For You):** `0.70` (70% - giữ mức tối thiểu 70% để tài khoản tiếp tục học tệp sở thích, không bị gắn cờ bot cày view chéo nội bộ).
   - **Bạn bè (Friends):** `0.15` (15% - tăng hơn gấp đôi, đảm bảo mỗi phiên 12-15 video đều ghé tab Bạn bè ~2 video).
   - **Đang follow (Following):** `0.15` (15% - ghé ~2 video/phiên).
2. **Tỷ lệ thả tim (`DEFAULT_FEED_LIKE_RATES`):**
   - **Bạn bè (Friends):** `70` (70% - đẩy tương tác nội bộ mạnh mẽ, chừa 30% organic noise để không bị TikTok quét pattern).
   - **Đang follow (Following):** `30` (30% - tim chọn lọc vừa phải vì có kênh creator bên ngoài).
   - **Đề xuất (For You):** `8` (8% danh nghĩa, nhịp Deep Inspect bù 40% cho Fast Swipe).
3. **Sửa Guard Deep Inspect trong `feed_swipe_smoke.py`:**
   Bắt buộc thêm `and current_feed_type == FEED_TYPE_FOR_YOU`:
   ```python
   if (
       is_feed_session
       and fast_swipe["enabled"]
       and current_feed_type == FEED_TYPE_FOR_YOU
       and ctx.config.get("_like_rate", _feed_session_config(ctx).get("like_rate")) is None
   ):
       _deep_like_rate = fast_swipe["deep_like_rate_percent"]
   else:
       _deep_like_rate = like_rates.get(current_feed_type, like_rate_percent)
   ```

## 3. Quy chuẩn Kiểm thử & Verification
1. **Xung đột PYTHONPATH của Hermes trên Windows:**
   Khi chạy `pytest` từ bash, nếu môi trường có `PYTHONPATH` trỏ vào venv của Hermes (`.../hermes-agent/venv/Lib/site-packages`), module `PIL` sẽ bị xung đột C-extension binary:
   `ImportError: cannot import name '_imaging' from 'PIL'`.
   -> **Bắt buộc:** Đặt `PYTHONPATH=""` khi chạy pytest:
   ```bash
   PYTHONPATH="" D:/Taadaa/python-envs/automation/Scripts/python.exe -m pytest python_runner/tests/test_feed_swipe_smoke.py -k "test_friends_and_following_feed_distribution_and_like_rates"
   ```
2. **Behavioral Test Invariant (Reviewer Gate 1):**
   Khi viết test cho các cấu hình phân bổ hoặc tỷ lệ like, không chỉ assert hằng số tĩnh (`assertEqual(DEFAULT_FEED_LIKE_RATES[...], 70)`), mà bắt buộc phải có test case thực thi logic chọn tỷ lệ (`_deep_like_rate`) theo từng tab để chứng minh guard hoạt động đúng.
