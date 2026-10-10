# Quy trình Xoay tua 4 Ngày (3 Ca/ngày) & Phục hồi Trust Score TikTok Farm (2026-10-10)

## 1. Nguyên lý Cốt lõi & Bài học Thực chiến từ Dàn Nuôi > 50% Trust Retention

- **Hiện tượng "Silent Follow Drop" (Nhả Follow):**
  - Khi TikTok backend đã đánh giá rủi ro và rollback 1 lượt follow (`not_followed` sau verify hoặc reload), **100% các lượt follow tiếp theo trong session đó sẽ bị drop sạch**.
  - **Quy tắc Thép:** CẤM TUYỆT ĐỐI cố bấm tiếp khi đã phát hiện nhả follow. Phải dập tắt session ngay lập tức tại điểm nhả đầu tiên để bảo vệ nick.
  - Cửa ải Anchor (kênh nguồn): Bắt buộc kiểm tra follow Anchor trước khi vào danh sách. Nếu follow Anchor đã bị nhả thì vào danh sách bấm cũng vô ích.
- **Không tự ý xóa án Cooldown:**
  - Án phạt `fail_streak` và `cooldown_until_date` phản ánh đúng hiện trạng tài khoản đang bị TikTok đưa vào diện theo dõi (High Scrutiny Bucket). CẤM tự ý reset hoặc xóa án khi chưa có lệnh rõ ràng từ Operator.

---

## 2. Chu kỳ Vận hành 4 Ngày (3 Ca / 3 Slot mỗi máy / ngày)

Mỗi máy cõng 8 slot (Row 1 đến Row 8). Lịch chạy loại bỏ hoàn toàn ca đêm (00:00 - 02:30), chỉ chạy 3 ca ban ngày (Sáng 06h/08h, Trưa 12h/14h, Tối 18h/20h).

### Lịch phân bổ chi tiết 4 ngày:

| Ngày | Ca 1 (Sáng 06h / 08h) | Ca 2 (Trưa 12h / 14h) | Ca 3 (Tối 18h / 20h) | Chế độ Follow & Upload |
| :--- | :---: | :---: | :---: | :--- |
| **Ngày 1** | **Nhóm A** (Row 1 hoặc Row 2) | **Nhóm A** (Row 3 hoặc Row 4) | **Nhóm A** (Row 5 hoặc Row 6) | Feed + Đi Follow + Upload (Phiên 2) |
| **Ngày 2** | **Nhóm B** (Row còn lại) | **Nhóm B** (Row còn lại) | **Nhóm B** (Row còn lại) | Feed + Đi Follow + Upload (Phiên 2) |
| **Ngày 3** | **Row 7** | **Row 8** | **Ca Dưỡng Sinh** *(Nick nhả / Nick yếu)* | Row 7, 8 cày thường; Ca tối: Pure Feed (0 Follow) |
| **Ngày 4** | **Ca 1 Tái cân bằng** | **Ca 2 Tái cân bằng** | **Ca 3 Tái cân bằng** | **NGÀY DƯỠNG SINH TOÀN FARM:** 0 Follow, vẫn đăng video & lướt feed bình thường |
| **Ngày 5** | **BẮT ĐẦU CHU KỲ MỚI** | *(Xúc xắc ngẫu nhiên 50/50 giữa Nhóm Lẻ [1,3,5] và Nhóm Chẵn [2,4,6])* | | |

---

## 3. Bản chất của Ngày Dưỡng Sinh (Ngày 4) & Quy tắc Đăng Video

- **Ngày 4 là "Behavioral Normalization Day" (Tái cân bằng hành vi):**
  - Không phải là tắt máy hoàn toàn, mà là ngày thực hiện các hành vi rủi ro thấp (Low-risk behaviors).
  - Ưu tiên chọn các nick đang bị nhả follow hoặc nick có trust score yếu để chạy 3 ca lướt feed.
- **Quy tắc Đăng Video trong Ngày Dưỡng Sinh:**
  - **VẪN ĐĂNG VIDEO BÌNH THƯỜNG:** Hệ thống Recommendation (phân phối video) độc lập với hệ thống Anti-Spam (quét follow). Một Creator thật khi không đi tương tác vẫn đăng video và xem feed đều đặn. Việc giữ nhịp đăng video chứng minh với TikTok đây là tài khoản sáng tạo nội dung thật.
  - **TẮT DUY NHẤT HÀNH ĐỘNG FOLLOW:** Ngày 4 tuyệt đối **0 FOLLOW** toàn bộ máy.

---

## 4. Xúc xắc Đảo Nhóm ở Ngày 5 (Temporal Entropy)

- Tại sao phải xúc xắc ở Ngày 5:
  - Nếu Ngày 1 luôn chạy cố định `1, 3, 5` và Ngày 2 luôn chạy `2, 4, 6`, hệ thống AI Anomaly Detection của TikTok sẽ phát hiện ra **Batch Temporal Pattern** (nhóm nick có chu kỳ hoạt động máy móc lặp lại theo lịch chẵn/lẻ).
  - Khi bốc thăm ngẫu nhiên ở Ngày 5 (hoặc nhóm lẻ đi trước, hoặc nhóm chẵn đi trước), sự tương quan hành vi (correlation) bị phá vỡ, giữ cho hoạt động farm luôn mang tính ngẫu nhiên của người dùng thật.
