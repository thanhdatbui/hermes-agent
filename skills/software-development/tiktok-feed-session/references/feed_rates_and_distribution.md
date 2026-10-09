# Cấu Hình Phân Bổ Tab Feed và Tỉ Lệ Like (Feed Distribution & Like Rates)

## 1. Tỉ Lệ Phân Bổ Tab Feed Mặc Định (DEFAULT_FEED_DISTRIBUTION)
Được định nghĩa tại `python_runner/flows/feed_swipe_smoke.py`:
- **For You (`for_you`)**: 70% (`0.70`)
- **Following (`following`)**: 15% (`0.15`)
- **Friends (`friends`)**: 15% (`0.15`)

Tổng phân bổ = 1.0 (100%).

## 2. Tỉ Lệ Like Mặc Định Theo Từng Tab (DEFAULT_FEED_LIKE_RATES)
- **For You (`for_you`)**: 8%
- **Following (`following`)**: 30%
- **Friends (`friends`)**: 70%

## 3. Quy Tắc Fast Swipe và Deep Inspect Like Rate
- Fast swipe chỉ hoạt động trên tab For You (`FEED_TYPE_FOR_YOU`). Khi chuyển sang tab Following hoặc Friends, flow bắt buộc chuyển 100% video sang Deep Inspect (dump XML) để tương tác chuẩn xác theo từng tab.
- Tại nhịp Deep Inspect, biến `_deep_like_rate` chỉ nhận `fast_swipe["deep_like_rate_percent"]` (40%) khi:
  1. `is_feed_session` là True.
  2. `fast_swipe["enabled"]` là True.
  3. `current_feed_type == FEED_TYPE_FOR_YOU`.
  4. Operator không cấu hình like-rate tường minh (`_like_rate` hoặc `feed_session.like_rate`).
- Nếu đang ở tab Following hoặc Friends, like rate BẮT BUỘC lấy từ `like_rates.get(current_feed_type, like_rate_percent)` để giữ đúng tỉ lệ 30% (Following) và 70% (Friends), không bị ghi đè bởi 40% của fast swipe.

## 4. Pitfall Cần Tránh Khi Viết Unit Test
- Khi test nhịp Deep Inspect, chú ý kiểm tra cả 3 trường hợp feed:
  - Tab For You không cấu hình tường minh -> nhận rate bù Fast Swipe (40%).
  - Tab Following -> nhận rate tab Following (30%).
  - Tab Friends -> nhận rate tab Friends (70%).
  - Khi operator cấu hình tường minh (`_like_rate`) -> ưu tiên tuyệt đối cấu hình của operator.
