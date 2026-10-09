# Case UI-99: Post-Cooldown Same-Day Warmup Persistence & id/u9f Selector Drift Recovery (07/10/2026)

## 1. Hiện tượng & Vấn đề Phát Hiện
1. **Acc mới ra tù bị nhảy vọt quota follow:**
   - Nick vừa mãn hạn cooldown (ví dụ bị phạt 3 ngày) khi được mở lại vào ngày đầu tiên:
   - Phiên 1 (sáng): Chạy đúng budget warm-up (3-5 lượt, ví dụ 4 lượt).
   - Phiên 2 (trưa/chiều): Nhảy vọt lên Full Budget (10-20 lượt, ăn thêm 7-11 lượt), nâng tổng số follow trong ngày lên 11-15 lượt, vi phạm nguyên tắc dưỡng acc sau khi ra tù.
   - **Nguyên nhân kỹ thuật:** Trong `follow_runner/core/follow_state.py`, hàm `mark(uid, STATUS_FOLLOWED)` tự động xóa `fail_streak = 0` ngay khi tài khoản bấm thành công lượt follow đầu tiên. Khi sang Phiên 2 cùng ngày, `fail_streak == 0` khiến `is_post_cooldown_warmup` trả về `False`, hệ thống coi acc là bình thường và cấp full budget.

2. **Module 2 bị lỗi hàng loạt thiếu nút semantic khiến farm degrade sang Module 1:**
   - Nhiều máy chạy Mode 2 bị vướng lỗi: `MANUAL_REVIEW: follower row không có nút follow semantic`.
   - Toàn bộ danh sách following của anchor không tìm thấy nút follow nào, khiến Mode 2 đạt 0 lượt và chuyển fallback sang Mode 1.
   - **Nguyên nhân kỹ thuật:** TikTok cập nhật resource-id của nút follow trong danh sách Following/Follower thành `com.ss.android.ugc.trill:id/u9f`. Do thiếu `id/u9f` trong `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS` (`selectors.py`), `_cluster_follower_rows` gán `follow_button: None` cho tất cả các hàng, kích hoạt chốt an toàn fail-closed.

---

## 2. Quy Chuẩn Kỹ Thuật & Giải Pháp Chuẩn Hóa

### A. Quy chuẩn Warm-up Nick Mới Ra Tù (Same-Day Warmup Persistence)
- **Quy tắc bất biến:** Nick mới ra tù thì TRONG SUỐT NGÀY HÔM ĐÓ MỖI PHIÊN CHỈ ĐƯỢC FOLLOW ÍT (3-5 lượt).
- **CẤM reset liền:** Khi bấm follow thành công trong ngày đầu tiên ra tù, `mark()` TUYỆT ĐỐI KHÔNG được reset `fail_streak` về 0 ngay lập tức.
  - Ghi nhận `recovered_date = today` và giữ nguyên `fail_streak > 0`.
  - Giữ cờ `is_post_cooldown_warmup = True` cho toàn bộ các phiên tiếp theo trong cùng ngày.
- **Chỉ reset sau ngày hôm đó:**
  - Trong `_roll_day()`, khi ngày chuyển sang ngày hôm sau (`today > recovered_date`):
  - Nếu tài khoản không tái phạm (`not self.follow_failed`), hệ thống mới chính thức reset `fail_streak = 0` và xóa `recovered_date`.

### B. Selector Drift Nút Follow `id/u9f`
- Bổ sung đầy đủ các biến thể resource-id `u9f` vào `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS` trong `follow_runner/core/selectors.py`:
  ```python
  FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS = (
      "com.ss.android.ugc.trill:id/tcj", "com.ss.android.ugc.trill:id/thb", "com.ss.android.ugc.trill:id/tvn",
      "com.ss.android.ugc.trill:id/tum", "com.ss.android.ugc.trill:id/u2f", "com.ss.android.ugc.trill:id/u68",
      "com.ss.android.ugc.trill:id/ubp", "com.ss.android.ugc.trill:id/u9f",
      ":id/tcj", ":id/thb", ":id/tvn", ":id/tum", ":id/u2f", ":id/u68", ":id/ubp", ":id/u9f",
      "id/tcj", "id/thb", "id/tvn", "id/tum", "id/u2f", "id/u68", "id/ubp", "id/u9f",
  )
  ```
- Xác nhận trên XML thực tế (`relation_dump.xml`): Nhận diện đầy đủ 100% nút Follow cho các hàng danh sách.
