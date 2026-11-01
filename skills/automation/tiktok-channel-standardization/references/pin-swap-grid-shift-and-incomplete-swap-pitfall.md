# Pin Swap Grid Shift Pitfall & Incomplete Swap Failure (2026-10-31)

## 1. Bản Chất Sự Cố "Hụt Slot Ghim" (3 ghim rớt còn 2 ghim)
- **Hiện tượng:** Kênh đang ghim đủ 3 video (ví dụ: 27,6K – 14,3K – 5,1K). Khi video mới nổ view (10,6K > 5,1K), watchdog kích hoạt hàm swap (`_swap_pinned_tile`). Kết quả: video 5,1K bị nhả ghim thành công, nhưng video 10,6K không được ghim lên $\to$ Kênh chỉ còn 2 video ghim, video 10,6K rớt xuống hàng thường.
- **Nguyên nhân cốt lõi (Grid Shift Trap):**
  1. Khi unpin video view thấp nhất, TikTok lập tức trả video đó về vị trí thời gian trong lưới feed thông thường.
  2. Việc chèn lại video vừa unpin vào lưới làm thay đổi toàn bộ chỉ số index và toạ độ trung tâm (`center (cx, cy)`) của các video phía sau.
  3. Video mục tiêu (10,6K) bị đẩy dịch chuyển vị trí hoặc trôi khỏi viewport ban đầu.
  4. Nếu hàm ghim bước 2 tìm kiếm theo toạ độ cũ hoặc `next((t for t in tiles if ...))` không tìm thấy $\to$ Thao tác tap thất bại (`TARGET_NOT_FOUND_AFTER_UNPIN` hoặc `ACTION_SHEET_NOT_FOUND`), văng lỗi `UNKNOWN` / `False`.
  5. **Hệ quả không có Rollback:** Thao tác nhả ghim là đơn hướng (irreversible without recovery). Không có cơ chế rollback ghim lại bài cũ hoặc thử lại nhiều lần, tài khoản bị bỏ rơi ở trạng thái khuyết 1 slot ghim.

## 2. Kỷ Luật Kiến Trúc Khắc Phục (Two-Phase Atomic Swap)
1. **Pre-flight Target Lock trước khi Unpin:**
   - Trước khi bấm unpin bài cũ, bắt buộc định vị và xác nhận video mục tiêu (10,6K) đang nằm trong viewport hoặc lưu trữ chính xác chữ/thông số định danh duy nhất (cover text, view count, timestamp).
2. **Dynamic Viewport Re-scan sau Unpin:**
   - Sau khi unpin thành công, KHÔNG được tái sử dụng toạ độ cũ.
   - Bắt buộc dump lại UI XML tươi qua `atx-agent` (hoặc cuộn bù nếu video mục tiêu bị đẩy xuống dưới mép màn hình).
   - Tìm kiếm candidate theo số view giảm dần (`cands = sorted(..., key=lambda t: t['views'], reverse=True)`).
3. **Rollback Safety / Recovery Gate:**
   - Nếu bước ghim video mới gặp sự cố (tap miss, sheet không hiện):
     * Không được thoát ngang để lại state lỗi.
     * Bắt buộc kích hoạt Fallback: Ghim lại bài cũ vừa nhả ghim hoặc ghim bài có view cao nhất kế tiếp trong viewport để luôn bảo toàn đủ 3 slot ghim hiển thị cho kênh.
