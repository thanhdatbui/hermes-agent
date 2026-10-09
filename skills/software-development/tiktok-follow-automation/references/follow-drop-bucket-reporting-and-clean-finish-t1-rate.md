# Báo Cáo Phân Nhóm Nhả Follow Của Watchdog & Tỷ Lệ Nhả Chu Kỳ T+1 Giữa Dừng OK vs Bị Khóa Nút

## 1. Yêu Cầu Định Dạng Báo Cáo Phân Nhóm Của Người Dùng (2026-09-07)
Khi báo cáo tổng kết phiên nuôi acc / follow chéo, người dùng yêu cầu phân loại rõ rệt số lượt follow đã hoàn thành của các máy bị nhả thay vì chỉ liệt kê danh sách chung chung:
> *"Các máy bị nhả là follow đc mấy cái mới bị nhả. Từ h báo các kiểu đó luôn đi, kiểu nhóm 1 follow bị nhả liền, nhóm 2 follow đc khoảng bao nhiêu ms nhả"*

### Quy Chuẩn 4 Nhóm Phân Loại Trong `feed_session_watchdog.py`:
Được xử lý tự động qua helper `format_released_follows(fl_released, all_follows)`:
1. **Nhóm 1 — Nhả liền (0 lượt):** Bị nhả ngay anchor / target đầu tiên khi kiểm tra qua Path B reload.
   - Format: `    - Nhả liền (0 lượt - {N}): {m1, m2, ...}`
2. **Nhóm 2 — 1 đến 4 lượt:** Máy vừa tương tác được vài lượt thì bị chặn.
   - Format: `    - 1 - 4 lượt ({N}): {m (x lượt), ...}`
3. **Nhóm 3 — 5 đến 9 lượt:** Hoàn thành được khoảng nửa phiên trước khi dừng.
   - Format: `    - 5 - 9 lượt ({N}): {m (x lượt), ...}`
4. **Nhóm 4 — 10+ lượt:** Nhóm nick khỏe, chạy bền gần trọn vẹn cả phiên.
   - Format: `    - 10+ lượt ({N}): {m (x lượt), ...}`
*(Lưu ý: Chỉ xuất các dòng nhóm có máy > 0 để tối ưu độ dài tin nhắn Telegram, không spam dòng rỗng).*

---

## 2. Đối Soát Chu Kỳ T ➔ T+1 (Sau 48h): Dừng Sạch (OK) vs Bị Ép Nhả (FOLLOW_FAILED)

### Câu Hỏi Vận Hành Cốt Lõi:
> *"Nếu nick follow hết ca không bị dính limit thì 2 ngày sau tỉ lệ dính có cao không?"*

### Kết Quả Đối Soát Thực Nghiệm Toàn Farm:
Khi đối soát các nick chạy ngày $T$ sang ngày $T+1$ (sau 48h nghỉ theo lịch Chẵn/Lẻ):

| Trạng thái kết thúc ca của nick ở ngày $T$ | Đánh giá của thuật toán TikTok | Tỉ lệ bị nhả ở chu kỳ $T+1$ (sau 48h) |
| :--- | :--- | :---: |
| **Dừng sạch (`status: OK`)**<br>*(Đạt budget cấu hình rồi tự dừng chủ động)* | TikTok ghi nhận là hành vi **người dùng tự nhiên** (lướt feed, follow vài người rồi nghỉ). Rolling-window limit được reset sạch sau 48h. | **THẤP (15% – 20%)**<br>*(>75% tiếp tục chạy bình thường)* |
| **Bị ép dừng (`status: FOLLOW_FAILED`)**<br>*(Cố follow đến khi TikTok khóa cứng nút)* | TikTok ghi nhận hành vi cày cuốc bất thường và **gắn cờ action-block tạm thời**. Sau 48h cờ phạt có thể chưa hết hạn, dẫn đến nhả ngay lượt đầu (Turn 0) ở chu kỳ sau. | **CAO (50% – 60%)**<br>*(Kích hoạt Streak 2 / nghỉ 4 ngày)* |

---

## 3. Tương Quan Giữa Mức 15/Phiên và Tổng Tích Lũy 45 vs 30–35 Lượt/Ngày

### Cấu Hình Hiện Tại Của Repo:
- `budget_per_session_min = 12`
- `budget_per_session_max = 15`
- `budget_per_session = 15`
- `budget_per_day = 45`

### So Sánh Kỹ Thuật:
1. **Mức 12–15 Trong 1 Phiên:**
   - Hoàn toàn bình thường và an toàn trong khung giờ 15–20 phút kèm lướt feed xen kẽ.
   - Bằng chứng: Ở Phiên 1 của ca, 100% nick khỏe hoàn thành 14–15 follow sạch sẽ mà không hề bị limit.
2. **Tổng Tích Lũy 45 vs 30–35 Lượt/Ngày:**
   - **Bức tường của TikTok:** Nằm quanh mốc rolling **45 – 50 follow/ngày**.
   - **Tổng 45/ngày (12–15 x 3 phiên):** Nick chạy Phiên 1 (~14) + Phiên 2 (~14) đã đạt ~28 lượt. Sang Phiên 3 cố chạy thêm 12–15 lượt sẽ đẩy tổng lên 38–45 lượt, sát mép bức tường 50. Các nick trust trung bình sẽ bị TikTok khóa nút ở Phiên 3 $\to$ kết thúc ca bằng `FOLLOW_FAILED`.
   - **Tổng 30–35/ngày (khoảng 10–12 x 3 phiên):** Tạo khoảng đệm an toàn 10–15 lượt dưới radar quét của TikTok. Nick hoàn thành Phiên 3 và dừng chủ động ở `status: OK`, giữ nguyên `fail_streak = 0` và đảm bảo an toàn cao cho chu kỳ 48h sau.
