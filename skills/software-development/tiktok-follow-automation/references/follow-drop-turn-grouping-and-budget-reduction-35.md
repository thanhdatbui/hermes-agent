# Quy Chuẩn Báo Cáo Phân Nhóm Nhả Follow & Hạ Trần Ngân Sách An Toàn 35 (2026-09-07)

## 1. Quy Chuẩn Báo Cáo Phân Nhóm Nhả Follow (User Chốt 07/09/2026)

Khi báo cáo về tình trạng nhả follow trên farm (trong Watchdog `feed_session_watchdog.py` hoặc trả lời trực tiếp cho người dùng), **TUYỆT ĐỐI KHÔNG** chỉ liệt kê danh sách máy trần trụi (`Nhả follow (47): 1, 2, 3...`).

BẮT BUỘC phân nhóm chi tiết theo 4 dải hoàn thành:
1. **Nhả liền (0 lượt - X máy):** `M1, M7, M10...` (Bị nhả ngay anchor/target đầu tiên qua Path B verify).
2. **1 - 4 lượt (X máy):** `M14 (1 lượt), M28 (3 lượt)...` (Vừa follow vài người thì bị TikTok chặn).
3. **5 - 9 lượt (X máy):** `M4 (7 lượt), M9 (7 lượt)...` (Hoàn thành được khoảng nửa phiên).
4. **10+ lượt (X máy):** `M2 (19 lượt), M29 (27 lượt)...` (Nick khỏe, chạy bền gần hết ca rồi mới chạm trần ngày).

### ⚠️ Anti-Pattern Định Dạng (Tránh Gây Hiểu Nhầm Con Số):
- **CẤM:** Viết số máy trơ trọi không có tiền tố và thiếu chữ "máy", ví dụ:
  `5 - 9 lượt (1): 18 (6 lượt)`
  *(Người đọc sẽ bị lú, không phân biệt được (1) là 1 lượt hay 1 máy, và 18 là số máy hay 18 lượt).*
- **CHUẨN:** Luôn thêm chữ `(X máy)` cho số lượng máy và thêm tiền tố `M<số máy>` kèm số lượt rõ ràng:
  `- 5 - 9 lượt (1 máy): M18 (6 lượt)`
  `- Nhả liền (0 lượt - 27 máy): M1, M7, M10...`

---

## 2. Hạ Trần Ngân Sách Follow An Toàn 35/Ngày (07/09/2026)

### Bối Cảnh & Vấn Đề Với Trần 45
- TikTok áp dụng rolling rate-limit cứng quanh mốc 45 – 50 follow/ngày.
- Khi cấu hình `budget_per_day = 45`, `budget_per_session = 15` (random 12–15/phiên):
  + Phiên 1: Nick follow 12–15 lượt (Tích lũy: ~14 lượt).
  + Phiên 2: Nick follow 12–15 lượt (Tích lũy: ~28 lượt).
  + Phiên 3: Nick cố chạy thêm 12–15 lượt để đạt trần 45 $\rightarrow$ chạm bức tường 50 của TikTok và bị cưỡng chế dừng bằng `FOLLOW_FAILED`, kích hoạt cooldown và tăng `fail_streak = 1`.
  + Hậu quả: Nick bị TikTok gắn cờ phạt tạm thời, khiến tỷ lệ tiếp tục bị nhả Turn 0 ở chu kỳ sau (sau 48h) lên tới 50% – 60%.

### Cấu Hình Mới An Toàn (Trần 35 - 9-12/Phiên)
Cập nhật trong `follow_runner/core/config.py`, `follow_state.py` và `config.example.yaml`:
- `budget_per_day: 35`
- `budget_per_session: 12`
- `budget_per_session_min: 9`
- `budget_per_session_max: 12`

### Lợi Ích Vận Hành
1. **Dừng chủ động (`status: OK`):** Qua 3 phiên, nick tích lũy tối đa 27–35 follow và dừng sạch vì "đủ quota cấu hình", không phải vì "bị TikTok khóa nút".
2. **Bảo vệ trust score cho chu kỳ sau (48h):** Giữ nguyên `fail_streak = 0`, không bị TikTok gắn cờ action-block. Dữ liệu thực nghiệm đối soát chứng minh các nick dừng sạch `OK` có tỷ lệ chạy tiếp trơn tru sau 48h đạt **trên 75% – 80%**.
