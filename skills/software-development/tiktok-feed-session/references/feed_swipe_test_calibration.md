# Feed Swipe Smoke Test & Calibration Rules

## 1. Đồng bộ Assertions giữa Code và Test (`test_feed_swipe_smoke.py`)

Khi thay đổi cấu hình tương tác hoặc tham số vuốt feed trong `flows/feed_swipe_smoke.py`, các bài test unit/smoke cần được đồng bộ chính xác:

- **Summary columns**:
  - Thứ tự các cột tương tác xã hội trong `build_feed_swipe_summary`:
    ```python
    "liked",
    "followed",
    "comment_peeked",
    "sponsored_skipped",
    ```
- **Default Like Rates**:
  - `DEFAULT_FEED_LIKE_RATES[FEED_TYPE_FOR_YOU] = 8`
  - `DEFAULT_FEED_LIKE_RATES[FEED_TYPE_FOLLOWING] = 35`
  - `DEFAULT_FEED_LIKE_RATES[FEED_TYPE_FRIENDS] = 45`
  - Chú ý: Tránh assertion lệch `FEED_TYPE_FRIENDS` với giá trị cũ (80).

- **Swipe Duration Range**:
  - Baseline swipe duration tuân theo:
    - `DEFAULT_SWIPE_DURATION_MIN_MS = 240`
    - `DEFAULT_SWIPE_DURATION_MAX_MS = 400`
  - Trong `test_feed_swipe_flow_does_not_call_social_actions`, duration sinh ra nằm trong khoảng 240..400ms (hoặc 330ms default khi không jitter). Cần đảm bảo range assertion bao phủ được dải này (e.g. `200 <= duration_ms <= 850`).
