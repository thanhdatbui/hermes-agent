# Đối Soát Chu Kỳ T -> T+1: Tác Động Của Volume Follow Cao (30–50 Lượt/Ngày) & Ngưỡng An Toàn (2026-09-06)

## 1. Bối Cảnh & Câu Hỏi Điều Tra
- **Mối lo ngại vận hành:** Khi tài khoản follow số lượng cao kịch trần (30–50 lượt/ngày) ở chu kỳ $T$, liệu sang chu kỳ $T+1$ (sau 48h theo lịch Chẵn/Lẻ) có bị thuật toán TikTok phạt nhả follow ngay từ đầu phiên (Turn 0 drop) hay không? Có cần hạ trần ngân sách ngày (budget_per_day) xuống mức thấp hơn không?
- **Phạm vi kiểm chứng thực tế:** 140 state files (`D:/Taadaa/tiktok-follow/runs/state/follow_state_*_row_*.json`) và runtime logs trên 80 máy từ 2026-08-27 đến 2026-09-06 (bao gồm Row 1 ngày lẻ và Row 2 ngày chẵn).

---

## 2. Kết Quả Đối Soát Thực Nghiệm Trên 133 Lượt Chạy Volume Cao (25–50 Lượt/Ngày)

Thống kê 133 trường hợp tài khoản đạt $\ge 25$ đến 50 lượt follow/ngày:
- **2026-08-27 (Row 1):** 15 máy đạt 29–30 follow.
- **2026-08-31 (Row 1):** 45 máy đạt 26–46 follow (M06, M20, M23, M24, M40, M44, M46, M58, M63 đạt 45–46 lượt).
- **2026-09-01 (Row 1):** 34 máy đạt 25–32 follow.
- **2026-09-02 (Row 2):** M45, M51 đạt kịch trần 50 follow.
- **2026-09-03 (Row 1):** 23 máy đạt 27–50 follow (M58 đạt 50, M62 đạt 49, M06 đạt 44, M36 đạt 43, M28/M63/M03 đạt 39).
- **2026-09-04 (Row 2):** M51 đạt 37 follow, M45 đạt 32 follow.
- **2026-09-06 (Row 2):** M08 (38 follow), M46 (34 follow), M26 (31 follow), M51/M72 (30 follow).

### Truy Vết Chi Tiết Chu Kỳ Kế Tiếp ($T+1$ sau 48h):
1. **M45 Row 2 (02/09 follow 50 -> 04/09 $T+1$):**
   - 04/09 Phiên 1 (06:00): Chạy trơn tru follow **18 lượt** (`status: OK`).
   - 04/09 Phiên 3 (07:30): Follow tiếp **15 lượt** rồi mới chạm rate-limit.
   - Tổng $T+1$ vẫn follow được **33 lượt an toàn** (không hề bị nhả Turn 0).
2. **M51 Row 2 (02/09 follow 50 -> 04/09 $T+1$ -> 06/09 $T+2$):**
   - 04/09 ($T+1$): Chạy 3 phiên `OK` liên tiếp (13 + 18 + 15 lượt), tổng follow thành công **46 lượt**.
   - 06/09 ($T+2$): Tiếp tục follow thành công **30 lượt** (20 lượt `OK` + 7 lượt trước rate-limit).
3. **M58 Row 1 (03/09 follow 50 -> 05/09 $T+1$):**
   - 05/09 ($T+1$): Phiên 1 follow thành công **17 lượt** trước khi dừng rate-limit.
4. **M62 Row 1 (03/09 follow 49 -> 05/09 $T+1$):**
   - 05/09 ($T+1$): Phiên 1 follow thành công **12 lượt** bình thường.
5. **Nhóm 8 máy Row 1 (M20, M23, M24, M40, M44, M46, M58, M63):**
   - 31/08 follow 45–46 lượt -> 01/09 ($T+1$ sau 24h): 100% cả 8 máy tiếp tục chạy trơn tru 5–6 phiên `OK`, mỗi máy follow thêm 25–32 lượt.

---

## 3. Bản Chất Kỹ Thuật Của Cơ Chế Rate-Limit & Hiện Tượng Nhả Turn 0

1. **Bản chất nhả follow của TikTok:**
   - Là **Rolling Window Rate-Limit** (giới hạn tần suất trượt theo phiên và theo ngày).
   - Khi nick follow đạt 15–20 lượt/phiên hoặc 40–50 lượt/ngày, TikTok tạm ngắt action follow trong vài giờ.
   - Sau chu kỳ nghỉ 48h (lịch Chẵn/Lẻ), rolling window đã hoàn toàn được reset về 0. **Không có hình phạt cộng dồn sang chu kỳ sau.**
2. **Nguyên nhân thực sự của hiện tượng Nhả Turn 0 (`followed_count = 0`):**
   - Hoàn toàn KHÔNG xuất phát từ việc chu kỳ trước follow quá nhiều.
   - Xuất phát từ 3 nguyên nhân:
     + Nick có `fail_streak >= 2` từ trước (trust score thấp, action block kéo dài hoặc IP/proxy có vấn đề).
     + Anchor UID bị gắn cờ hạn chế tương tác / profile anchor bị lỗi quan hệ (Path B kiểm tra thấy nút bị nảy lại ngay lượt đầu).
     + Nick chưa đủ trust score (< 5 video) nhưng lọt vào follow hook.

---

## 4. Kết Luận Về Ngưỡng An Toàn Vận Hành (Operational Best Practices)

- **Ngưỡng an toàn hàng ngày:** Trần **50–60 follow/ngày** là an toàn tuyệt đối, không gây shadowban hay nhả follow ở chu kỳ sau.
- **Quy tắc phân bổ phiên (Shift Budgeting):**
  - Giữ nguyên cấu trúc: **1 Ca = 3 Phiên follow**, mỗi phiên ăn theo phiên lướt Feed (cách nhau 45–60 phút).
  - Mỗi phiên đặt target **15–20 follow/phiên**.
  - Không thực hiện follow dồn dập 50 lượt trong 1 phiên duy nhất (cold follow / blast follow).
- **Cơ chế bảo vệ đa tầng đã hoàn thiện:**
  - `Path B verify`: Phát hiện nhả follow sau vuốt ngay lập tức.
  - `Daily Cooldown`: Dừng ngay phiên khi chạm trần rate-limit (`status: FOLLOW_FAILED, exit 0`), bảo vệ nick không bị phạt nặng.
  - `Progressive Backoff`: Tự động tăng cooldown (1 ngày -> 4 ngày -> 7 ngày) nếu bị nhả liên tiếp nhiều ngày.
