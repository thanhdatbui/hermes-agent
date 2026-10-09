# Post-Cooldown Warmup Leak and Unfilled Budget Triage

## 1. Hiện tượng "Acc Mới Ra Tù Chạy Quá Nhiều Follow" (Warmup Leak)
### Cơ chế lỗi & Root cause
- **Quy định nghiệp vụ:** Nick vừa mãn hạn cooldown (`is_post_cooldown_warmup`) chỉ được phép chạy Warmup an toàn **3 – 5 follow/ngày** để thử phản ứng của TikTok.
- **Lỗi logic trong `follow_state.py`:**
  - `is_post_cooldown_warmup` được định nghĩa là `self.fail_streak > 0 and not self.follow_failed`.
  - Khi Phiên 1 của ngày chạy, nick được cấp đúng budget Warmup (3–5 lượt) và bấm follow thành công.
  - Tuy nhiên, trong hàm `mark(uid, STATUS_FOLLOWED)`, hệ thống ngay lập tức gọi:
    ```python
    self._data["fail_streak"] = 0
    self._data["follow_failed"] = False
    ```
  - **Hệ quả:** Ngay sau lượt follow thành công đầu tiên ở Phiên 1, `fail_streak` bị reset về 0. Khi Phiên 2 của cùng ca/ngày đó khởi động, hàm `session_budget()` kiểm tra thấy `fail_streak == 0` nên nhận định nick là tài khoản trưởng thành bình thường (`mode: 'full'`).
  - Hệ thống cấp tiếp full budget phiên (10–20 lượt), khiến nick vừa ra tù chạy tới **11 – 15 lượt/ngày**, phá vỡ ngưỡng bảo vệ Warmup.

### Khuyến nghị kỹ thuật
- Không reset `fail_streak = 0` ngay tại từng action `mark()`.
- Phải duy trì trạng thái `warmup_date == today` hoặc yêu cầu hoàn thành trọn vẹn cả ngày với budget clamp tối đa 3–5 lượt cho toàn bộ các phiên trong ngày đó trước khi hoàn toàn gỡ cờ warmup.

---

## 2. Hiện tượng "Acc Khoẻ Chạy Không Đủ Budget" (Underfilled Budget)
### Nguyên nhân kỹ thuật từ log thực tế
1. **Mất phiên do Timeout khâu chuẩn bị (`follow-timeout`):**
   - Phiên 1 bị kẹt mạng, VPN hoặc loading màn hình TikTok vượt quá soft deadline -> runner báo `status: timeout`, kết thúc phiên với 0 follow. Nick chỉ còn 1 phiên duy nhất để chạy trong ca.
2. **Nghẽn UI ở Mode 2 (Anchor Mining):**
   - Danh sách following của Anchor bị trống hoặc TikTok đổi selector nút Follow khiến runner ghi nhận `MANUAL_REVIEW: follower row không có nút follow semantic`.
   - Hệ thống kích hoạt fallback sang Mode 1 (`mode2_degraded=True`).
3. **Chạm trần Soft Deadline phiên ở Mode 1:**
   - Mode 1 gõ phím tìm kiếm từng UID và vuốt feed giãn cách giữa các lượt tốn nhiều thời gian.
   - Khi thời gian phiên chạm mốc `has_time_for_next_action(reserve_seconds=90.0)`, runner chủ động dừng sớm (graceful exit) để bảo đảm đóng app an toàn, không để sót session treo.
