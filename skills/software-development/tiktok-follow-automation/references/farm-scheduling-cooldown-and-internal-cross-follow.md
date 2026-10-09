# Farm Scheduling, Cooldown, and Internal Cross-Follow Dynamics

Tài liệu chuẩn hóa kiến thức vận hành, chu trình chạy, phân bổ slot và đối chiếu thực chiến thuật toán TikTok cho dàn Phone Farm (cày chéo nội bộ & nuôi acc).

---

## 1. Quy Tắc Móng Trước Khi Follow (Hard Gate $\ge 10$ Video)
- **Acc mới (0 - 30 ngày):** Tuyệt đối KHÔNG cho đi follow (0 follow). 
- Chỉ chạy lướt nuôi gốc (feed session) + đăng video đều đặn vào các khung giờ vàng (9h, 16h, tối muộn) cho đến khi tài khoản tích lũy đủ $\ge 10$ video.
- Thời gian giai đoạn này khoảng 30 - 40 ngày. Mục đích: xây dựng móng vững chắc, tạo trust score của một Creator thật trước khi phát sinh hành vi tương tác ngoại vi.

---

## 2. Tỷ Lệ Phiên Tự Nhiên: 2 Follow : 1 Đăng Video
- **Bản chất "2 lần follow 1 lần đăng video":** Đây là **tỷ lệ cấp phiên (session-level ratio)**, không phải 2 lượt click follow.
- Cứ **2 phiên chạy follow** (mỗi phiên chạy đủ hạn mức an toàn 10 - 15 follow/phiên) $\rightarrow$ xen kẽ **1 phiên upload video mới** lên profile.
- Giúp tài khoản giữ vững trạng thái "nhà sáng tạo nội dung đang tương tác kết nối cộng đồng", xóa sạch nhãn "consumer rác / spam bot".

---

## 3. Chu Kỳ Xoay Tua Slot & Ngày Nghỉ Trắng Toàn Farm (White Day)

### A. Chu kỳ 4 ngày (Mô hình 160 máy - An toàn tối đa)
- **Lịch slot:** Ngày 1 (Slot 1, 3, 5) $\rightarrow$ Ngày 2 (Slot 2, 4, 6) $\rightarrow$ Ngày 3 (Slot 7, 8) $\rightarrow$ Ngày 4 (Nghỉ 100%).
- Mỗi slot chạy 1 ngày, nghỉ 3 ngày liên tiếp (72h cooldown).
- Acc mới chưa cứng bắt buộc dùng nhịp 72h cooldown này để tránh bị thuật toán tích tụ điểm nghi vấn.

### B. Chu kỳ 3 ngày (Mô hình 4 - 4 - Nghỉ - Tối ưu tốc độ)
- **Lịch slot:** Ngày 1 (Slot 1, 2, 3, 4) $\rightarrow$ Ngày 2 (Slot 5, 6, 7, 8) $\rightarrow$ Ngày 3 (Nghỉ 100% toàn farm).
- Mỗi slot chạy 1 ngày, nghỉ 2 ngày liên tiếp (48h cooldown).
- Chỉ áp dụng cho acc đã cứng ($\ge 10$ video, trust score tốt, đã qua giai đoạn móng).

### C. Ý nghĩa sống còn của Ngày Nghỉ Trắng (White Day)
- Toàn bộ 100% máy trong farm KHÔNG thực hiện bất kỳ thao tác bấm follow nào (chỉ chạy script lướt feed giải trí hoặc nghỉ).
- **Phá vỡ tính đồng điệu (Low Entropy Pattern):** Bot thường có lịch trình quá hoàn hảo (ngày nào cũng mở app follow rồi tắt). Ngày nghỉ trắng làm phân phối hành vi tự nhiên hơn, ngăn chặn các mô hình machine learning quét cluster/botnet dồn dập trên cùng dải IP/Proxy.

---

## 4. Phép Tính Follow Chéo Nội Bộ (Internal Network Math)
- **Định luật bảo toàn lượt follow (Zero-sum graph):** Tổng số lượt gửi đi = Tổng số lượt nhận về.
- Mỗi nick gửi đi trung bình ~250 follow/tháng.
- Muốn 1 nick nhận đủ 1.000 follow nội bộ từ các nick khác trong dàn $\rightarrow$ Bắt buộc mất:
  $$\frac{1.000 \text{ lượt cần nhận}}{250 \text{ lượt/tháng}} = \mathbf{4 \text{ tháng}}$$
- Cộng thêm giai đoạn nuôi móng 10 video ban đầu (~1 tháng) $\rightarrow$ **Tổng thời gian vòng đời hoàn thiện 1 lứa là ~5 tháng** (hoặc ~3.5 tháng với chu kỳ 3 ngày của acc cứng).
- Số lượng máy lớn (50, 100 hay 160 máy) chỉ giải quyết bài toán quy mô mẻ thu hoạch (batch size), không thể rút ngắn tốc độ sinh học của 1 nick đơn lẻ.
- **Rủi ro đồ thị khép kín (Closed-ring Graph):** Follow chéo nội bộ có tỷ lệ tương hỗ (reciprocity) gần 100%, rất dễ bị TikTok quét chùm. **Bắt buộc kẹp 20% - 30% follow các kênh lớn cùng ngách ngoài farm** để làm loãng đồ thị liên kết.

---

## 5. Kỷ Luật Fail-Fast Khi Dính Phạt Nhả
- Khi phát hiện bị nhả follow ở ca đầu: **Dừng ngay lập tức (Fail-fast)**, cấm cố đấm ăn xôi chạy tiếp trong ca.
- Chuyển slot đó sang chế độ thuần lướt nuôi (chỉ lướt feed, thả tim nhẹ).
- Thời gian cooldown phục hồi tối thiểu là **48h (2 ngày)** trước khi cho chạy lại chế độ dò nhả warmup.
