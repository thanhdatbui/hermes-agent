# Kỷ Luật Nhận Diện Chủ Thể Kênh: Bẫy Video Thú Cưng vs Nữ Creator Thực Tế

## 1. Ngữ Cảnh & Bản Chất Sai Lệch (The Creator vs Pet Trap)
- Trong các kho video nuôi nick (ví dụ kho nguồn `D:/video goc/<F_src>`), clip đầu tiên hoặc một số clip ban đầu có thể chỉ quay thú cưng (chó/mèo/chim cảnh) hoặc đồ vật.
- **Bẫy:** Nếu chỉ xem lướt clip 1 hoặc clip view cao nhất, Coordinator có thể vội vàng kết luận kênh thuộc ngách "Thú cưng" và tạo bảng Proposal Canvas toàn ảnh thú cưng.
- **Thực tế:** Kênh thường thuộc về một **Nữ Creator** (chủ nhân) — người xuất hiện xuyên suốt ở các clip vlog, dạo phố, thử đồ, sinh hoạt hằng ngày ở các clip tiếp theo. Khi User yêu cầu "Đổi ava khác", điều đó thường báo hiệu rằng phương án ban đầu đã lệch chủ thể thực sự của kênh.

## 2. Quy Trình Khảo Sát Đa Tầng Tránh Bẫy Cục Bộ
1. **Khảo sát diện rộng toàn kho video (Multi-clip Sampling):**
   - Không được chỉ lấy mẫu ở `1.mp4` hoặc 1 clip duy nhất.
   - Bắt buộc quét mẫu (sample) các mốc thời gian (1.5s, 4s, 8s) trên ít nhất 5-10 video trải đều trong kho (từ đầu, giữa đến cuối danh sách video).
2. **Phân biệt Nhân Vật Chủ Thể (Human Creator) vs Đối Tượng Phụ (Pet/Prop):**
   - Nếu kho video có người xuất hiện thường xuyên, chủ thể kênh là **Người (Creator)**, thú cưng chỉ là một phần nội dung vlog.
   - Avatar kênh TikTok cá nhân luôn ưu tiên khuôn mặt của Creator (trừ khi toàn bộ 100% video không có người và tên kênh định vị chuyên biệt về pet).
3. **Trích Xuất Chân Dung Nữ Creator Sạch Chữ:**
   - Dùng Haar Cascade hoặc chọn frame cận cảnh khuôn mặt có nụ cười tự nhiên, ánh sáng tốt.
   - Cắt khung vuông tâm mặt (cx, cy) với kích thước side vừa vặn (headroom cân đối).
   - Chạy kiểm tra WinRT OCR xác nhận 100% rỗng (`''`), đảm bảo không dính watermark hay chữ trên áo/nền.
4. **Tái Lập Canvas v2 Ngay Lập Tức:**
   - Khi User phản hồi "Đổi ava khác", ngay lập tức chuyển hướng sang bộ chân dung Creator người thật, chuẩn bị đủ 4 phương án đa dạng trang phục/bối cảnh để User lựa chọn.
