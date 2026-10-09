# Hạ Ngân Sách Follow An Toàn 35 Lượt/Ngày & Chuẩn Hóa Phân Nhóm Báo Cáo Nhả Follow (2026-09-07)

## 1. Bối Cảnh & Động Lực Hạ Ngân Sách (45 -> 35 Lượt/Ngày)

### Hiện Tượng Farm Khi Chạy Trần 45
- Cấu hình trước đây (Case UI-55): `budget_per_day: 45`, `budget_per_session: 15` (min: 12, max: 15).
- 1 Ca gồm 3 Phiên follow xen kẽ lướt feed:
  + Phiên 1: Nick follow 12–15 lượt `OK` -> tích lũy 12–15 lượt.
  + Phiên 2: Nick follow tiếp 12–15 lượt `OK` -> tích lũy 24–30 lượt.
  + Phiên 3: Nick tiếp tục cố follow để đạt trần 45. Tại mốc này, tổng follow trong ngày vọt lên sát mép bức tường rate-limit cứng 45–50 của TikTok.
  + Hậu quả: Nhiều nick có trust score trung bình bị TikTok kích hoạt chặn rate-limit cuối ca (`status: FOLLOW_FAILED`), tăng `fail_streak = 1` và dính daily cooldown. Khi thử lại sau 48h (chu kỳ sau), có tới 50% nick bị phạt nhả Turn 0.

### Ngưỡng An Toàn Mới (Case UI-57 / 07/09/2026)
- **Cấu hình chuẩn hóa mới:**
  + `budget_per_day`: **35** follow/ngày
  + `budget_per_session`: **12** follow/phiên
  + `budget_per_session_min`: **9**
  + `budget_per_session_max`: **12**
- **Hiệu quả kỹ thuật:**
  + Mỗi phiên bốc ngẫu nhiên 9, 10, 11 hoặc 12 follow.
  + Sau 3 phiên, nick tích lũy 27–35 lượt/ngày, tạo một khoảng đệm an toàn (Buffer 15 lượt) nằm hoàn toàn dưới tầm quét của thuật toán TikTok.
  + Nick hoàn thành đủ chỉ tiêu và chủ động dừng ở trạng thái sạch `status: OK`, giữ `fail_streak = 0`.
  + Tỷ lệ nick tiếp tục chạy mượt mà không bị nhả ở chu kỳ sau (48h kế tiếp) đạt **trên 80%** (so với việc bị ép chạm trần `FOLLOW_FAILED`).

---

## 2. Quy Chuẩn Phân Nhóm Báo Cáo Nhả Follow Trong Watchdog

Theo chỉ đạo của người dùng, báo cáo tổng kết phiên của `feed_session_watchdog.py` không được gộp chung danh sách các máy bị nhả follow mà bắt buộc phải phân nhóm chi tiết theo số lượt hoàn thành trước khi bị nhả:

### 4 Dải Phân Nhóm Chuẩn:
1. **Nhả liền (0 lượt):** Nick vừa tap target đầu tiên thì nút nảy lại ngay (`budget_used == 0`). Phản ánh nick bị shadowban tích lũy hoặc trust score yếu.
2. **1 – 4 lượt:** Nick nhả sớm sau vài lượt tương tác.
3. **5 – 9 lượt:** Nick hoàn thành được khoảng 1/2 chỉ tiêu phiên trước khi dừng.
4. **10+ lượt:** Nick chạy bền gần trọn vẹn phiên hoặc tích lũy qua nhiều phiên trước khi chạm trần.

### Định Dạng Mẫu Bắt Buộc:
```text
• Follow chéo (320 lượt follow):
  + Success (12): 3, 5, 8, ...
  + Nhả follow (47):
    - Nhả liền (0 lượt - 27): 1, 7, 10, 11, 13, 17, 19, 24, ...
    - 1 - 4 lượt (7): 14 (1 lượt), 15 (1 lượt), 18 (1 lượt), 20 (1 lượt), 25 (1 lượt), 27 (1 lượt), 28 (3 lượt)
    - 5 - 9 lượt (5): 4 (7 lượt), 9 (7 lượt), 36 (9 lượt), 38 (7 lượt), 70 (9 lượt)
    - 10+ lượt (8): 26 (11 lượt), 39 (14 lượt), 6 (16 lượt), 2 (19 lượt), 31 (19 lượt), 72 (23 lượt), 21 (24 lượt), 29 (27 lượt)
  + Lỗi script/xác minh (0): Không có
  + Bỏ qua (15): ...
```
*(Chỉ hiển thị các dòng nhóm có máy > 0, không in dòng rỗng).*
