# Tài liệu vận hành: Nâng cấp thể tích Feed, Ad Fast-Skip và Khắc phục trần Swipes Cap (2026-09-12)

## 1. Nâng cấp Thể tích Feed & Tỷ lệ Like tự nhiên
- **Nguyên nhân 0 Like lịch sử (18/08 - 12/09):** TikTok cập nhật gộp text nút Like thành `"Thích video. 41,3K lượt thích"`, khiến so sánh tuyệt đối `== "Thích"` bị mù 26 ngày liên tiếp.
- **Khắc phục:** Prefix match `desc.lower().startswith("thích video")` hoặc `"like video"` kết hợp `attrib.get("clickable") == "true"`. Đã kiểm chứng canary trên Máy 24 thả tim thành công 100%.
- **Nâng mốc video:**
  - `FEED_SESSION_MIN_TOTAL_VIDEOS = 16`
  - `FEED_SESSION_MAX_TOTAL_VIDEOS = 22`
  - `FEED_SESSION_MAX_SWIPES = 28`
  - Phân bổ tự nhiên: Fast swipe 2-4s không dump XML xen kẽ Deep Inspect xem chậm 8-15s có Like theo tỷ lệ tab: For You (8%), Following (30%), Friends (70%).
- **Timeout thiết bị:** Nâng `DEFAULT_DEVICE_TIMEOUT_SECONDS = 3000.0` (50 phút) để đáp ứng thời gian chạy thực tế ~28-35 phút/máy cho 16-22 video.

## 2. Bài học Pitfall: Lỗi Cap Swipes (`config-error: requires 1 <= --max-swipes <= 15`)
- **Triệu chứng:** Ca 3 Row 6 lúc 18:00 fail đồng loạt 69 máy ngay giây đầu tiên (`completed_steps: 0 swipes`).
- **Nguyên nhân:** Khi nâng `FEED_SESSION_MAX_SWIPES = 28`, trong code còn 2 chốt cứng kiểm tra tham số:
  1. `run_tiktok.py:839`: `if args.mode == "feed-session-smoke" and not 1 <= int(args.max_swipes) <= 15`
  2. `feed_swipe_smoke.py:213`: `SESSION_MAX_SWIPES_CAP = 15`
- **Khắc phục:** Nâng cả 2 chốt validation trần lên `<= 30` (`SESSION_MAX_SWIPES_CAP = 30`).

## 3. Tích hợp tính năng Ad Fast-Skip (từ GemPhoneFarm anh Khoa)
- Đọc XML đệ quy qua `iter_elements(root)` tìm cụm text hoặc content-desc chứa `"Được tài trợ"` / `"Sponsored"`.
- Khi phát hiện video quảng cáo: ghi log `skip_sponsored` và quẹt lướt sang video kế tiếp trong 0.5s, không like, không xem lâu.
