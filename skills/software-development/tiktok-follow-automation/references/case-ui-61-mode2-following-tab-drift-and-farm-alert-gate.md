# Case UI-61: Tab Header Drift "Đang follow / Đang theo dõi" & Farm Alert Threshold

## Triệu chứng
- Ca nuôi acc / follow ghi nhận hàng loạt máy (ví dụ 13/14 máy chạy Mode 2) bị kẹt và trả về lỗi:
  `MANUAL_REVIEW: mở tab Đã follow fail cho {uid} sau ladder (lần 2)`
- Nhưng Watchdog nuôi acc (`feed_session_watchdog.py`) không bắn thông báo đỏ về kênh Telegram Farm Alert (`-5373649734`), khiến operator không nắm được sự cố sập cả đàn.

## Root Cause
1. **Lệch Selector Header Quan hệ (Mode 2)**:
   - TikTok tiếng Việt trên máy cập nhật hiển thị tab là `"Đang follow [N]"` hoặc `"Đang theo dõi [N]"`.
   - Trong `follow_runner/flows/mode2_follow_followers.py`, regex `_FOLLOWER_HEADER_RE` và nhãn `_FOLLOWER_EMPTY_LABELS` chỉ nhận dạng `"đã follow"`, `"following"`, `"follower"`, `"người theo dõi"`.
   - Khi vào màn danh sách, `_classify_follower_surface` đánh dấu tab là `invalid` vì match regex thất bại, khiến `_on_follower_list` trả về `False`.
   - Hàm `_open_following_tab` lặp poll 25s không thấy list render -> văng `MANUAL_REVIEW`.

2. **Thiếu Mass Failure Farm Alert Gate**:
   - Watchdog phiên nuôi acc trước đây chỉ gửi báo cáo về `origin` chat hoặc in stdout, chưa cấu hình `send_farm_alert` gửi chéo sang nhóm Farm Alert `-5373649734`.
   - Đồng thời chưa có ngưỡng cứng cảnh báo khi lỗi diện rộng theo từng khâu riêng biệt (Feed, Follow, Upload).

## Giải pháp & Quy chuẩn bắt buộc

1. **Cập nhật Regex & Label Whitelist (`mode2_follow_followers.py`)**:
   ```python
   _FOLLOWER_HEADER_RE = re.compile(
       r"^(follower|followers|người theo dõi|đã follow|đang follow|đang theo dõi|following)(?:\s+(\d+))?$",
       re.IGNORECASE,
   )
   _FOLLOWER_EMPTY_LABELS = {
       "follower",
       "followers",
       "người theo dõi",
       "đã follow",
       "đang follow",
       "đang theo dõi",
       "following",
   }
   ```
   Bắt buộc chạy suite test regression `test_mode2_follow_followers.py` với test case kiểm tra cả `"Đang follow [N]"` và `"Đang theo dõi [N]"`.

2. **Quy tắc Cảnh báo Farm Alert (> 10 máy)**:
   - Trong watchdog phiên nuôi acc (`feed_session_watchdog.py`), bất kỳ khi nào phát hiện **> 10 máy lỗi** ở bất kỳ khâu nào:
     + Lướt Feed Fail > 10 máy
     + Follow Hook Lỗi UI/Script > 10 máy
     + Upload Hook Lỗi > 10 máy
   - BẮT BUỘC dispatch một thông báo khẩn cấp `🚨 [FARM ALERT] PHÁT HIỆN LỖI DIỆN RỘNG (>10 MÁY)` trực tiếp về kênh Farm Alert `-5373649734` kèm danh sách máy bị lỗi.
