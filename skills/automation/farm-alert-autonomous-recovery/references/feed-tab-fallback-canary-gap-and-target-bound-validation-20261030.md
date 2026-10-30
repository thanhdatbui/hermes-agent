# Feed Tab Fallback State Sync & Target-Bound Canary Discipline (2026-10-30)

## 1. Bản Chất Sự Cố Hệ Thống (34/52 Máy Dính `feed not confirmed`)
- Tại commit `43fa019`, cơ chế graceful fallback được thêm vào `feed_swipe_smoke.py`: khi tab Following hoặc Friends gặp lỗi mạng/trống, script tự động tap quay lại tab Đề xuất (`FEED_TYPE_FOR_YOU`).
- **Lỗ hổng chết người (State Desynchronization):**
  Script đổi `current_feed_type = FEED_TYPE_FOR_YOU` và `next_feed_type = FEED_TYPE_FOR_YOU`, nhưng **KHÔNG ĐỒNG BỘ** lại:
  * `confirm["detected"]` (vẫn mang giá trị cũ `friends`/`following`)
  * `confirm["feed_type"]`
  * `expected_label` (vẫn là `"Following feed"` hoặc `"Friends feed"`)
- **Hậu quả:** Dòng tiếp theo gọi `_is_navigation_mismatch_row(confirm, "for-you")` thấy `confirm["detected"] != "for-you"` nên đánh giá là `MISMATCH` $\rightarrow$ lọt vào nhánh `retry_navigation` $\rightarrow$ `_capture_step` bắt lỗi kỳ vọng Following nhưng thực tế là For You $\rightarrow$ dập lỗi hàng loạt `feed not confirmed` (65.4% máy lỗi).

## 2. Chuẩn Hóa Patch Hợp Đồng O(1)
Khi kích hoạt fallback về For You, bắt buộc phải cập nhật đủ 3 biến trạng thái:
```python
current_feed_type = FEED_TYPE_FOR_YOU
next_feed_type = FEED_TYPE_FOR_YOU
confirm["status"] = ExitStatus.DEGRADED.value
confirm["safety_status"] = "ok"
confirm["detected"] = FEED_TYPE_FOR_YOU
confirm["feed_type"] = FEED_TYPE_FOR_YOU
expected_label = _expected_feed_label(FEED_TYPE_FOR_YOU)
videos_until_tab_decision = random.randint(5, 10)
```

## 3. Bẫy "Canary Hình Thức" Khi Sửa Tab Navigation
- **Hiện tượng vi phạm:** Sửa lỗi ở nhánh fallback tab con (`friends`/`following`), nhưng khi chạy Canary lại dùng lệnh mặc định `--recovery-test-swipes 2`.
- **Tại sao Canary 2 swipes bị vô hiệu hóa:**
  * Biến đếm `videos_until_tab_decision` khởi tạo `random.randint(3, 8)`.
  * Khi chỉ lướt 2 video, bộ đếm không bao giờ về $\le 0$, TikTok chỉ lướt thuần 2 video For You rồi teardown lấy exit 0.
  * Trong `log.jsonl`, số lần gọi `fallback_feed_tab` bằng **0**. Code vừa sửa hoàn toàn không được chạm vào trên máy thật.
- **Kỷ luật Target-Bound Canary bắt buộc cho Tab Fallback:**
  * BẮT BUỘC ép máy chuyển tab bằng cách truyền `--feed-distribution '{"for-you": 0.2, "following": 0.4, "friends": 0.4}'` hoặc tăng `--max-swipes 5`.
  * Hậu kiểm log bắt buộc: Phải grep `log.jsonl` xác nhận có event `action: fallback_feed_tab` VÀ ngay sau đó tiếp tục lướt feed thành công mà không có lỗi `feed not confirmed`.
