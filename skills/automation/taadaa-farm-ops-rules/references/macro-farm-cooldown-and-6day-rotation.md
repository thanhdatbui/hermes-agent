# Chiến lược Vận Hành Vĩ Mô Farm 80-160 Máy: Nhịp Nghỉ, Follow Budget & Chu Kỳ Xoay Tua (Đúc kết 16/09/2026)

## 1. Bản chất thuật toán TikTok nhìn vào Farm
- **Micro-behavior (Vi mô):** Vuốt lệch trục ($X \in [450, 540], dx \ne 0$), rewind swipe 5-8%, independent bookmark 3-5%, comment peek 8-16%, profile dwell 6-12s, PTR ngẫu nhiên.
- **Macro-pattern (Vĩ mô):** 
  - Thuật toán anti-abuse quét cả chu kỳ tuần/tháng và tương quan giữa các tài khoản cùng dải mạng/thiết bị.
  - Cày follow liên tục 7 ngày/tuần làm tích lũy điểm nghi vấn (anomaly score) không bao giờ về 0.
  - Tỷ lệ đối xứng follow chéo 100% trong bầy nội bộ là dấu vết botnet graph điển hình.

## 2. Công thức Vàng: 2 Phiên Follow / 1 Phiên Upload Video
- **Móng 10 video ban đầu:**
  - Acc mới reg trong ~30 ngày đầu: **Tuyệt đối 0 follow**.
  - Chỉ chạy lướt feed nuôi giải trí và đăng video mồi vào các khung giờ vàng (9h sáng, 16h chiều, tối muộn) cho đến khi tích lũy đủ $\ge 10$ video.
  - Khi đã có móng 10 video và profile có view tự nhiên, tài khoản được xếp vào diện Creator thật, mở khóa quyền đi cày follow chéo an toàn.
- **Tỷ lệ 2 Follow : 1 Upload:** Cứ 2 phiên cày follow thì xen kẽ 1 phiên upload video mới để "rửa" trust score.

## 3. Chu kỳ Vĩ mô 6 ngày (4 Acc / Ngày + Ngày Dưỡng Sinh Rửa Trust)
Khung giờ máy khớp chuẩn 4 Ca (Sáng, Trưa, Tối, Đêm), 1 ngày máy gánh 4 slot:
- **Day 0:** Nhóm lẻ (Row 1, 3, 5, 7) -> Cày Follow (10–20/phiên) + Upload.
- **Day 1:** Nhóm chẵn (Row 2, 4, 6, 8) -> Cày Follow (10–20/phiên) + Upload.
- **Day 2:** Nhóm lẻ (Row 1, 3, 5, 7) -> **DƯỠNG SINH RỬA TRUST (100% chỉ lướt feed, 0 follow, 0 upload)**.
- **Day 3:** Nhóm chẵn (Row 2, 4, 6, 8) -> Cày Follow (10–20/phiên) + Upload.
- **Day 4:** Nhóm lẻ (Row 1, 3, 5, 7) -> Cày Follow (10–20/phiên) + Upload.
- **Day 5:** Nhóm chẵn (Row 2, 4, 6, 8) -> **DƯỠNG SINH RỬA TRUST (100% chỉ lướt feed, 0 follow, 0 upload)**.
- **Day 6:** Tự động quay vòng về Day 0 (`day_cycle % 6`).

*Ưu điểm của chu kỳ 6 ngày so với chu kỳ 3 ngày:*
- Trạng thái farm bị phân tán (State Entropy cao), xóa sạch nhịp tim bầy đàn (cluster heartbeat).
- Nhịp đăng video của 1 nick: cách 2 ngày $\to$ cách 4 ngày $\to$ cách 2 ngày $\to$ cách 4 ngày (trung bình 3 ngày/video = 10 video/tháng), hoàn toàn tự nhiên.

## 4. Cơ chế Opportunistic Upload (Đăng video cơ hội chống trượt nhịp)
- Không cố định upload chỉ ở Phiên 2. Kích hoạt `-AllowUploadHook` ở **cả Phiên 1 lẫn Phiên 2** vào ngày cày.
- Dựa vào sổ cái liên tiến trình `shift_upload_history.json`:
  - Phiên 1 đăng thành công $\to$ ghi nhận ledger. Phiên 2 tự động bỏ qua (`already_uploaded_in_shift`), tránh đăng trùng.
  - Phiên 1 lỗi mạng/popup $\to$ Phiên 2 tự động phát hiện và đăng bù ngay lập tức, ngăn ngừa trượt nhịp đăng video kéo dài 6-8 ngày.

## 5. Quy tắc Clear Cache & Quản trị Phần cứng S7
- **Tuyệt đối KHÔNG clear cache trước mỗi lần switch nick:** Tránh tạo signature bot lặp lại máy móc.
- **Clear cache định kỳ cuối ngày / cuốn chiếu:** Nhằm mục đích duy nhất là giải phóng bộ nhớ máy Samsung S7 (32GB), chống tràn disk gây crash app.
- **Staggering 30s – 40s:** Khởi động so-le giữa các máy để không burst request đồng loạt lên proxy.
