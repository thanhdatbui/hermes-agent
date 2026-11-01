# Kỷ Luật Phân Giải Ảnh & Chống Phóng Đại Micro-Crop Vỡ Hạt

## 1. Bản Chất Sự Cố (Root Cause)
Khi User phản hồi về phương án avatar, Coordinator thường mắc sai lầm cơ học nghiêm trọng:
1. **Micro-Crop & Upscaling Trap:**
   - Ảnh gốc toàn cảnh có độ phân giải 512x512.
   - Thay vì giữ nguyên bố cục tổng thể hài hòa hoặc lấy frame từ video có góc quay cận cảnh gốc, Agent tự suy diễn hoặc cắt một vùng cực nhỏ quanh mặt/mũi (chỉ 180x180 px hoặc 120x120 px).
   - Sau đó dùng `cv2.resize` phóng to ngược lên 512x512.
   - **Hậu quả:** Ảnh bị vỡ nát pixel, nhòe nhoẹt, mất nét hoàn toàn, tạo thành một mảng lông bầy hầy mờ căm dính sát ống kính.
2. **Ảo Giác Mô Tả (Text-Vision Disconnect):**
   - Mặc dù ảnh vỡ nát, Agent không mở mắt nhìn thật mà vẫn dùng văn mẫu ca ngợi: *"khuôn mặt sắc nét, 2 mắt to tròn, mũi đen bóng"*.
   - User mở ảnh ra thấy một mảng lông mờ tịt không thể chấp nhận được.
3. **Hiểu Sai Yêu Cầu Của User:**
   - User không đòi hỏi phải dí sát vào lỗ mũi, User cần ảnh đẹp, rõ ràng, đúng chủ thể và nhận diện được thương hiệu của kênh.

## 2. Quy Tắc Cơ Học Khắc Phục (Mechanical Rules)

### Quy Tắc 1: Minimum Crop Window Ratio (>= 70%) & Resolution Floor (>= 350px)
- Khi thực hiện crop avatar từ ảnh tĩnh hoặc frame video:
  - Vùng crop tối thiểu phải chiếm **ít nhất 70%** kích thước ảnh gốc, hoặc kích thước vùng chọn tối thiểu phải đạt **>= 350x350 px**.
  - **CẤM TUYỆT ĐỐI** crop vùng < 50% kích thước ảnh gốc (như vùng 180x180 px) rồi upscale nội suy gây vỡ hạt.
- Nếu muốn lấy cận cảnh: Phải trích xuất từ **video có góc quay cận cảnh gốc (close-up shot)**, không được zoom kỹ thuật số (digital zoom) trên ảnh toàn cảnh độ phân giải thấp.

### Quy Tắc 2: Ưu Tiên Ảnh Gốc Bố Cục Tự Nhiên & Video Nhận Diện Thương Hiệu
- Một bức ảnh toàn thân/nửa thân của thú cưng hoặc creator sắc nét, ánh sáng hài hòa, thấy rõ khuôn mặt trong tổng thể luôn **tốt hơn gấp 1000 lần** một bức ảnh zoom sát vào mũi làm vỡ nát pixel.
- Khi ảnh gốc đã đẹp và rõ mặt: Giữ nguyên khung hình đầy đủ (Full body / Upper body), không cố tình crop nhỏ.
- Khi kho video nguồn hỗn tạp nhiều chủ đề, **BẮT BUỘC** trích xuất frame từ chính video có view cao nhất / video đại diện của kênh (ví dụ: cún múa bụng quấn khăn chuông tím ở video 1).

### Quy Tắc 3: Soi Mắt Độc Lập Sau Khi Export (Post-Export Vision Gate)
- Trước khi đính kèm `MEDIA:<path>` gửi User:
  - BẮT BUỘC gọi `browser_navigate` và `browser_vision` mở file đã lưu ra xem.
  - Đặt câu hỏi cụ thể cho Vision: *"Ảnh có bị vỡ hạt (pixelated), nhòe mờ (blurry) hay bị zoom quá sát mất thẩm mỹ không?"*.
  - Nếu Vision báo ảnh nhòe/vỡ hạt ➔ **HỦY BỎ NGAY LẬP TỨC**, quay về dùng bản gốc chưa crop, cấm gửi bản vỡ hạt cho User.
