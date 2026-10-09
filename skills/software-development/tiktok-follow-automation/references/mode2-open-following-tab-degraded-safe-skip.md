# Mode 2 Open Following Tab Fail Sau Ladder & Bẫy Nhả Follow (2026-09-28)

## 1. Hiện tượng & Bối cảnh
Khi chạy Mode 2 (`mode2_follow_followers.py`), bot tìm kiếm tài khoản Anchor nội bộ (Tik1/Tik2), truy cập profile và mở tab **"Đã follow" (Following)** để quét danh sách nick farm cần follow chéo.

Tại báo cáo Feed Session Watchdog, xuất hiện 2 dạng lỗi / cảnh báo follow:
1. `Lỗi script/xác minh (1): mở tab Đã follow fail cho <anchor> sau ladder (lần 2) (1: M72)`
2. `Nhả follow (0 lượt - 3 máy): M33, M34, M38` kèm `Lệch -1 so với script báo 1`

## 2. Phân tích nguyên nhân & Kiến trúc xử lý

### A. Lỗi mở tab Đã follow fail sau ladder (lần 2)
* **Nguyên nhân:**
  - Sau khi tap tab Đã follow, UI không kịp hiển thị `RecyclerView` chứa danh sách, hoặc loading animation kéo dài vượt deadline `_open_following_tab`.
  - Trên màn hình profile, node text tab Đã follow có thể nằm ở `android:id/text1` nhưng chưa được kích hoạt event tap chuẩn hoặc bị chệch focus.
* **Cải tiến logic (Evolution):**
  - **Phiên bản cũ:** Nếu sau 2 lần thử (ladder recovery + retry) vẫn không mở được tab, flow gán `res.status = "MANUAL_REVIEW"` và `res.failed = True` -> Gây fail toàn bộ session follow của máy.
  - **Phiên bản mới (Safe-Skip):** Khi mở tab fail sau lần 2, flow ghi nhận `mode2_degraded = True`, log lý do vào `mode2_degraded_reasons`, gọi `_back_to_feed(engine)` và **`continue` safe-skip** sang anchor tiếp theo thay vì ngắt phiên bằng `MANUAL_REVIEW`.
  - **Lưu ý Watchdog merge:** Khi có nhiều run trong cùng phiên (ví dụ 06:01 và 08:00), nếu run đầu bị `MANUAL_REVIEW` và run sau `OK (degraded)` nhưng `followed = 0`, cơ chế `merge_follow_result` có thể vẫn giữ nguyên failure detail của run trước đó nếu không được reset cẩn thận.

### B. Bẫy Nhả Follow (Anti Follow-Release Guard)
* **Nguyên nhân:**
  - Khi bot follow anchor, sau bước kiểm tra phá cache (`_ensure_anchor_followed` / `verify_follow.py`), TikTok phát hiện tương tác bất thường hoặc tài khoản đang bị hạn chế tương tác tạm thời, tự động chuyển nút Follow về lại trạng thái chưa follow (nhả liền 0 lượt).
* **Cơ chế tự vệ đúng:**
  - Lập tức kích hoạt `FOLLOW_FAILED`, ngắt follow session ngay lập tức để bảo vệ tài sản nick.
  - Cập nhật `follow_state_<machine>_row_<N>.json`: `follow_failed: true`, tăng `fail_streak`.
  - Toàn bộ các ca tiếp theo trong ngày của nick đó sẽ tự động chuyển sang `skip_follow_daily_cooldown`, chỉ nuôi feed dưỡng sinh, cấm cố tình bấm follow lại bằng tay qua ADB.
