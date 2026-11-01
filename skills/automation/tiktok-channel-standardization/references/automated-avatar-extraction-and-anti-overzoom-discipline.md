# Kỷ Luật Trích Xuất Avatar Thẩm Mỹ & Cấm Đoán Mò Yêu Cầu Cận Cảnh

## 1. Bản Chất Vấn Đề Từ Phản Hồi User
Trong các phiên chuẩn hóa avatar từ video/ảnh gốc:
1. **Bẫy Đoán Mò Cận Cảnh (Over-Zooming Trap):**
   - User không hề yêu cầu "phải cắt dí sát vào mặt", nhưng Coordinator tự suy diễn quá mức, cố tình crop lấy mỗi phần đầu/mặt rồi phóng to lên.
   - Kết quả: Ảnh bị phóng to kỹ thuật số (digital zoom) làm vỡ hạt, mờ căm, chỉ thấy một mảng lông hoặc cục da bầy hầy dính sát camera, mất toàn bộ thẩm mỹ.
2. **Công Cụ Cắt Tự Động Sẵn Có Trong Repo (Codebase Truth):**
   - Không tự viết script opencv crop mò với tọa độ cứng.
   - Trong repo `D:/Taadaa/tools` đã có sẵn công cụ chuẩn hóa:
     `D:/Taadaa/tools/extract_high_confidence_avatars.py`
     - Sử dụng bộ lọc độ nét **`Laplacian Variance (sharpness score)`** trên từng frame video: `sharp = cv2.Laplacian(gray_roi, cv2.CV_64F).var()`. Chỉ lấy frame có `sharp >= 90`.
     - Tự động phát hiện khuôn mặt/chủ thể và tính toán bounding box cân đối, giữ tỷ lệ khung hình tự nhiên không gây méo/vỡ hạt.
3. **Nguyên Tắc Chọn Frame Gốc Độ Nét Cao (HD Native Frame):**
   - Luôn chọn frame từ video nhận diện thương hiệu (video có view cao nhất hoặc video đặc trưng của kênh).
   - Downscale từ frame HD (ví dụ: box 720x720 downscale về 512x512 bằng `INTER_AREA`), **CẤM TUYỆT ĐỐI** crop mẩu nhỏ < 350px rồi upscale lên làm nhòe ảnh (No Micro-Crop Upscaling).
4. **Kho Avatar Thú Cưng Tuyển Chọn Chuẩn Studio Trên Farm:**
   - Khi video nguồn quá tối hoặc không có góc quay tĩnh đẹp, hệ thống Taadaa Farm đã có sẵn các kho avatar thú cưng chuẩn Studio HD, đạt tỷ lệ view cao tại các folder gốc đã kiểm chứng:
     - `D:/video goc/385/avatar.jpg`: Poodle/Bichon trắng xù siêu nét.
     - `D:/video goc/399/avatar.jpg`: Golden Retriever mỉm cười chuẩn studio.
     - `D:/video goc/334/avatar.jpg`: Samoyed tuyết trắng lanh lợi.
     - `D:/video goc/353/avatar.jpg`: Cún con lông nâu cam ngây thơ.
   - Trình bày cho User bằng bảng so sánh Preview hình tròn TikTok (`make_circle_preview`) với nhãn rõ ràng để User chọn, cấm tự ý up ảnh bẩn lên thiết bị.

## 2. Quy Trình Trích Xuất Avatar Chuẩn Hóa
1. **Tìm video đại diện:** Trích xuất các frame rõ nét nhất từ video chính (không lấy video rác/video cơ khí lẫn lộn).
2. **Khung hình tự nhiên:** Giữ trọn dáng đứng hoặc toàn thân có bối cảnh đẹp (Full Body / 3/4 Body) nếu chủ thể nhỏ. Tránh zoom cưỡng bức.
3. **Soi mắt kiểm tra trước khi gửi:**
   - BẮT BUỘC dùng `browser_vision` kiểm tra ảnh sau khi lưu.
   - Nếu thấy ảnh vỡ hạt, mờ hoặc bố cục dị dạng -> Hủy ngay, không gửi đối phó cho User.
