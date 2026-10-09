# Quy Chuẩn Vuốt Ngón Tay Sinh Học (Humanized Thumb Arc Swipe)

## 1. Mục Tiêu & Cơ Sở Thiết Kế
Tránh hệ thống chống bot của TikTok phát hiện thao tác vuốt máy móc (thời lượng cố định, đường vuốt thẳng tắp, hoặc chạm vào các pill tương tác đáy video).

## 2. File Quy Định
- Repo: `D:/Taadaa/tiktok-luot nuoi acc`
- File: `python_runner/flows/feed_swipe_smoke.py`

## 3. Bộ Thông Số Chuẩn Hóa (Đã thẩm định)

### A. Thời lượng vuốt (Swipe Duration)
- `DEFAULT_SWIPE_DURATION_MIN_MS = 240` (thay vì 550ms quá chậm)
- `DEFAULT_SWIPE_DURATION_MAX_MS = 400` (thay vì 750ms)
- `DEFAULT_SWIPE_DURATION_MS = 330`
- `DEFAULT_FEED_SWIPE_UP_COMMAND = ["input", "swipe", "450", "1380", "450", "480", "330"]`

### B. Hành lang an toàn & Bảo vệ lệch góc (`_perform_feed_swipe`)
- Kiểm tra độ lệch đầu vào:
  ```python
  if abs(raw_end_x - start_x) > 45:
      end[0] = start_x
  else:
      end[0] = max(440, min(540, raw_end_x))
  ```
- Clamp hành lang X cuối cùng: `[440, 540]` để bảo đảm không trượt vào mép trái/phải hoặc các nút like/share.

### C. Cơ chế đường cong ngón cái (`_build_swipe_parameters`)
- Mô phỏng vòng cung ngón tay cái thực tế:
  ```python
  start_x = max(470, min(525, BASE_SWIPE_START[0] + x_offset))
  drift = 0 if jitter_px == 0 else random.randint(-35, 15)
  end_x = max(440, min(540, start_x + drift))
  start_y = random.randint(1330, 1410) if jitter_px != 0 else BASE_SWIPE_START[1]
  end_y = random.randint(430, 510) if jitter_px != 0 else BASE_SWIPE_END[1]
  ```
- Dải Y bắt đầu: `1330..1410` (tránh 100% việc ngón tay chạm trúng khung tin nhắn/bình luận ở `y=1485..1563` hoặc search pill ở `y=1500..1650`).
- Dải Y kết thúc: `430..510`.

## 4. Verification & Testing Pitfalls
1. **Signature của `_build_swipe_parameters`:**
   - Nhận `ctx: DeviceContext` là positional argument đầu tiên. Khi test cô lập, dùng `unittest.mock.MagicMock()`.
   - Các tham số keyword-only bắt buộc: `swipe_count`, `watch_min_seconds`, `watch_max_seconds`, `duration_min_ms`, `duration_max_ms`, `jitter_px`, `artifact_prefix`.
2. **File encoding & CRLF trên Windows:**
   - File `feed_swipe_smoke.py` rất lớn (>23,000 dòng) với định dạng kết dòng Windows (CRLF). Khi thực hiện thay thế chuỗi đa dòng, chuẩn hóa CRLF/LF để tránh miss anchor.
