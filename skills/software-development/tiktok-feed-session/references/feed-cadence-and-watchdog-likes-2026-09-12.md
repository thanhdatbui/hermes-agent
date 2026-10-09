# Quy chuẩn Video Range, Fast Swipe Cadence & Watchdog Likes (2026-09-12)

## 1. Khung Video Mỗi Phiên Lướt Feed
- `FEED_SESSION_MIN_TOTAL_VIDEOS = 16`
- `FEED_SESSION_MAX_TOTAL_VIDEOS = 22`
- `FEED_SESSION_MAX_SWIPES = 28`
- **Thời lượng vận hành thực tế:**
  - Thực tế trên máy S7 / Android farm: 8-11 video mất ~13.7 phút/máy do độ trễ dump UI XML + xử lý popup.
  - Khi nâng lên 16-22 video (nhờ cơ chế Fast Swipe không dump XML), thời lượng thực tế tăng nhẹ lên **~16 đến 20 phút/máy**.
  - Timeout tối đa của máy là `DEFAULT_DEVICE_TIMEOUT_SECONDS = 2100.0` (35 phút), do đó mức 16-22 video là mức an toàn tuyệt đối.

## 2. Nhịp Fast Swipe Xen Kẽ Deep Inspect & Bù Trừ Xác Suất Thả Tim
- **Tab Đề xuất (For You - 70% thời lượng):**
  - Xen kẽ giữa Fast Swipe (lướt nhanh 2.0s – 5.0s, không dump XML, không like) và Deep Inspect (xem chậm 8.0s – 12.0s, dump XML để like/follow).
  - **Bù trừ xác suất Like ở For You:** Vì Fast Swipe không thả tim, nên ở các lượt Deep Inspect, tỷ lệ like được nâng lên **40%** (`DEFAULT_DEEP_LIKE_RATE_PERCENT = 40`).
  - Phép tính xác suất tổng thể: Cứ 3-4 video có 1 video Deep Inspect x 40% = **10% - 12% Like toàn phiên For You** (đúng chuẩn tỷ lệ vàng của người thật).
- **Tab Đang theo dõi (Following - 15%) & Bạn bè (Friends - 15%):**
  - **100% video chạy Deep Inspect (xem chậm)**, cấm Fast Swipe ở 2 tab này.
  - Thời gian xem video: Following (4.0s – 12.0s), Friends (5.0s – 15.0s).
  - Tỷ lệ like: Following 30%, Friends 70%.

## 3. Bug Selector Like TikTok & Bản Vá Tiền Tố (Prefix Match)
- **Nguyên nhân tê liệt like:** TikTok cập nhật UI nối thêm số lượng like vào `content-desc`: `"Thích video. 41,3K lượt thích"`. Code cũ dùng so sánh bằng tuyệt đối `content_desc == "Thích"` khiến 100% video bị bỏ qua, farm lướt 556 video với 0 lượt like.
- **Bản vá chuẩn:** Quét `iter_elements(root)` với prefix match:
  - Nút like: `desc.lower().startswith("thích video")` hoặc `desc == "Thích"` hoặc `desc.lower().startswith("like video")` hoặc `desc == "Like"` hoặc `like_icon` in resource_id, kết hợp `element.attrib.get("clickable") == "true"`.
  - Nút đã thích: `desc.lower().startswith("đã thích video")`, `"bỏ thích"`, `"liked video"`.

## 4. Giám Sát Watchdog Telegram
- File `feed_session_watchdog.py` trích xuất trường `like_counts` từ file `summary.txt` từng máy.
- Báo cáo định dạng Telegram hiển thị trực tiếp:
  `• Lướt Feed (N lượt thả tim):`
- **Chỉ số an toàn:** Nếu tổng likes của cả farm báo về = 0 qua 2 ca liên tiếp -> Báo động ngay selector Like bị drift!
