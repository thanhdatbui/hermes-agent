# Ngưỡng Ngân Sách An Toàn 35 Follow/Ngày & Quy Chuẩn Báo Cáo Phân Nhóm Nhả Follow (2026-09-07)

## 1. Hạ Trần Ngân Sách 35 Follow/Ngày (9 – 12 Follow/Phiên)

### Bối Cảnh & Động Lực
- **Trần cũ 45/ngày (12–15/phiên x 3 phiên):**
  - Mặc dù trần 45 đã thấp hơn bức tường cứng 50 của TikTok, nhưng ở Phiên 3 các nick khỏe vẫn tích lũy chạm ngưỡng 38–45 follow, dẫn đến ~18% số máy bị TikTok kích hoạt chặn rate-limit cuối ca (`FOLLOW_FAILED: TikTok không nhận follow sau reload — dừng session`).
  - Khi nick kết thúc ngày với `FOLLOW_FAILED`, tỷ lệ bị nhả liền (Turn 0) ở chu kỳ sau (48h kế tiếp) lên tới 50%–60% do cờ phạt tạm thời của TikTok chưa kịp giải phóng hoàn toàn.
- **Cấu hình chuẩn mới 35/ngày (Chốt 07/09/2026):**
  - `budget_per_day = 35`
  - `budget_per_session = 12`
  - `budget_per_session_min = 9`
  - `budget_per_session_max = 12`
  - Mỗi phiên bốc ngẫu nhiên trong khoảng `[9, 10, 11, 12]` follow.

### Lợi Ích Vận Hành
1. **Khoảng đệm an toàn 15 lượt:** Sau 3 phiên, nick tích lũy tối đa 27–35 follow, nằm hoàn toàn dưới vùng radar quét rolling limit của TikTok.
2. **Dừng sạch chủ động (`status: OK`):** Nick kết thúc ca vì hoàn thành đủ quota cấu hình, không bị cưỡng chế dừng bởi rate-limit.
3. **Bảo vệ chu kỳ $T+1$ (sau 48h):** Khi kết thúc ngày ở trạng thái `OK`, `fail_streak` giữ nguyên bằng 0, tỷ lệ nick tiếp tục chạy mượt mà ở chu kỳ sau đạt trên 75%–80%.

---

## 2. Quy Chuẩn Định Dạng Báo Cáo Phân Nhóm Nhả Follow trong Watchdog

### Bài Học Trải Nghiệm Người Dùng (UX Pitfall)
- **Anti-Pattern gây khó hiểu:**
  `5 - 9 lượt (1): 18 (6 lượt)`
  Việc thiếu chữ "máy" ở số lượng và thiếu tiền tố "M" trước số máy khiến người đọc bị rối mắt bởi 2 cặp số liền kề: `(1)` bị tưởng nhầm là 1 lượt follow, và `18` không rõ là máy 18 hay 18 lượt.
- **Chuẩn hiển thị bắt buộc (BẮT BUỘC có chữ "máy" và tiền tố "M"):**
  ```text
  • Follow chéo (404 lượt follow):
    + Success (13 máy): M3, M5, M8, M16, ...
    + Nhả follow (47 máy):
      - Nhả liền (0 lượt - 27 máy): M1, M7, M10, M11, ...
      - 1 - 4 lượt (7 máy): M14 (1 lượt), M15 (1 lượt), M18 (1 lượt), M20 (1 lượt), ...
      - 5 - 9 lượt (5 máy): M4 (7 lượt), M9 (7 lượt), M36 (9 lượt), M38 (7 lượt), M70 (9 lượt)
      - 10+ lượt (8 máy): M2 (19 lượt), M6 (16 lượt), M21 (24 lượt), M29 (27 lượt), ...
    + Lỗi script/xác minh (0): Không có
    + Bỏ qua (15 máy): M12, M46, ...
  ```

### Quy Tắc Code trong `format_released_follows`
- Chuẩn hóa tên máy bằng helper `_format_m(m)`: luôn xuất `M<id>` (ví dụ `M18`, `M4`).
- Luôn kèm chữ `máy` trong ngoặc số lượng: `({len(group)} máy)`.
- Luôn kèm chữ `lượt` trong ngoặc số follow của từng máy: `({cnt} lượt)`.
- Chỉ xuất các dòng phân nhóm có số lượng máy $> 0$ để tránh làm dài tin nhắn Telegram.
