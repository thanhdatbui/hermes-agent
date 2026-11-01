# Bẫy Logic Ghim Top Video TikTok & Cơ Chế Khắc Phục (Post-Mortem 2026-10-31)

## 1. Bản chất sự cố
Người dùng phàn nàn: *"Là sao nx t đã ép script phải luôn pin bài view cao nhất lên vidoe đầu mà"* khi thấy kênh có 3 bài ghim nhưng bài view cao nhất (27,9K) lại nằm ở Ô 2/3, còn Ô 1 bị bài mới cắn đề xuất (10,7K) hoặc bài view thấp chiếm đóng. Đồng thời trước đó số bài ghim bị hụt từ 3 xuống còn 2.

## 2. Các bẫy kỹ thuật trong logic Pin & Swap
1. **Bẫy đối soát chuỗi cứng (`raw_text`) sau khi Unpin:**
   - Trong luồng `_swap_pinned_tile`, sau khi bỏ ghim bài cũ (`lowest`), TikTok làm mới UI và đẩy các video dịch chuyển vị trí.
   - Code cũ dùng: `new_target = next((t for t in tiles if not t["is_pinned"] and t["raw_text"] == target["raw_text"]), None)`.
   - Nếu chuỗi text bị biến động hoặc làm tròn số view khác một ký tự (`10,7K` vs `10.700`), `new_target` bị `None` $\to$ văng lỗi `TARGET_NOT_FOUND_AFTER_UNPIN`.
   - **Giải pháp:** Đối soát linh hoạt ưu tiên theo view số nguyên: `t["views"] == target["views"]`. Nếu không khớp, tự động fallback bốc video chưa ghim có view cao nhất: `new_target = max(unpinned, key=lambda t: t["views"])`.

2. **Khuyết cơ chế Rollback khi Swap:**
   - Khi unpin bài cũ thành công nhưng bước pin bài mới gặp lỗi hoặc không tìm thấy bài mới, kênh bị **lủng mất 1 slot ghim** (từ 3 video rớt xuống 2 video).
   - **Giải pháp:** Bọc toàn bộ các bước sau unpin bằng hàm `rollback`: nếu fail ở bất kỳ bước nào, tự động ghim lại bài `lowest` cũ để bảo toàn số lượng ghim.

3. **Bẫy điều kiện `if not dry_run and not auto_swap`:**
   - Hàm `_enforce_top_pin_at_slot1` chịu trách nhiệm ép bài view cao nhất về Ô 1 trước đây bị bọc bởi `if not dry_run and not auto_swap:`.
   - Tuy nhiên, trong hầu hết các lệnh chạy thực tế và watchdog tự động, `auto_swap=True` $\to$ điều kiện bị `False` $\to$ **`_enforce_top_pin_at_slot1` không bao giờ được gọi**.
   - **Giải pháp:** Bỏ điều kiện `not auto_swap`. Luôn gọi `_enforce_top_pin_at_slot1` sau khi hoàn tất pin hoặc swap.

4. **Hàm `_swap_pinned_tile` thiếu bước Enforce Slot 1:**
   - Khi swap bài mới thay bài cũ, bài vừa swap có thể chỉ là top 3 view (ví dụ 10,7K), nhưng do cơ chế LIFO của TikTok, bài được ghim sau cùng sẽ tự động nhảy vào Ô 1, đẩy bài top 1 (27,9K) sang Ô 2.
   - **Giải pháp:** Kích hoạt `_enforce_top_pin_at_slot1` ngay cuối hàm `_swap_pinned_tile`.
