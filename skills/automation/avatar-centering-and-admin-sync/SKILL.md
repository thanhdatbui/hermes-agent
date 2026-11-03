---
name: avatar-centering-and-admin-sync
description: "Kỷ luật trích xuất Avatar căn giữa tâm chống lẹm mặt và tối ưu dung lượng đồng bộ sang Admin host"
---
# Avatar Centering and Admin Sync Discipline

Sử dụng skill này khi thực hiện trích xuất, cắt avatar từ video và đồng bộ media sang máy chủ Admin farm (`192.168.110.119`).

## 1. Bẫy Cắt Cụt Nửa Mặt (Anti-Half-Face Crop Trap)
- **Bản chất lỗi:** Đối tượng chuyển động lệch về mép khung hình dọc (9:16). Nếu crop theo toạ độ fixed hoặc góc phần tư cứng mà không tính tâm biên sẽ chém cụt nửa mặt, nửa mõm hoặc tai của đối tượng.
- **Quy chuẩn trích xuất:**
  1. **Lọc frame nét:** Dùng OpenCV đo phương sai Laplacian (`lap_var > 150`, độ sáng trung bình `60 < mean < 220`).
  2. **Căn giữa tâm (Subject Centering):** Crop hình vuông tỷ lệ 1:1 (`608x608` hoặc `512x512`). Tính toán tâm biên an toàn: nếu bounding box chạm sát mép ảnh gốc, phải bù trừ offset lùi tâm vào phía trong để giữ trọn vẹn toàn bộ khuôn mặt/đầu và tai.
  3. **Canvas Proposal:** Luôn vẽ viền tròn mô phỏng avatar TikTok để kiểm tra trước khi trình User duyệt; đảm bảo các chi tiết quan trọng không bị lọt ra ngoài vòng bo tròn.

## 2. Kỷ Luật Đồng Bộ Media Sang Host Admin (`sync_avatar_to_admin.py`)
- Script `sync_avatar_to_admin.py` đẩy dữ liệu qua SSH chunk base64 (`admin_ssh.py`).
- **Bẫy Timeout khi file lớn:** Với file ảnh dung lượng lớn (>80KB), việc chia nhiều chunk nhỏ qua lệnh SSH liên tiếp sẽ gây timeout 35s - 120s.
- **Biện pháp tối ưu kích thước:**
  - Luôn nén/resize ảnh avatar về chuẩn vuông `400x400` đến `500x500`, chất lượng JPEG 85% (`cv2.imwrite(..., [int(cv2.IMWRITE_JPEG_QUALITY), 85])`).
  - Dung lượng file tối ưu là `<= 30KB`. Ở mức này, SSH chỉ cần ~14 chunk và hoàn tất trong vòng 10-15s, không bao giờ chạm timeout.
- **Hậu kiểm 2 đầu:**
  - Cục bộ: `ls -l D:/TIKTOK-videonuoinick/<id>/avatar.jpg`
  - Host remote: `python D:/Taadaa/tools/admin_ssh.py "dir D:\\TIKTOK-videonuoinick-admin\\<id>\\avatar.jpg"`
  - Xác nhận file tồn tại, dung lượng khớp và có cờ `.manual_avatar_locked`.

## 3. Chống Bẫy Quán Tính Ngữ Cảnh Khi Nhận Ảnh User (Anti-Context-Inertia)
- **Cơ chế lỗi:** Khi đang trao đổi về chủ đề cắt avatar hoặc vật nuôi, User quăng ảnh chụp màn hình phản hồi (phụ tùng, vòi nước, thông báo lỗi). Agent bị "quán tính ngữ cảnh", không đọc pixel ảnh mới mà tiếp tục suy luận mù bám theo chủ đề cũ (ví dụ: nhìn ảnh vòi nước Kangen Water lại phán là chú cún cưng).
- **Kỷ luật bắt buộc:** Hễ User gửi ảnh mới vào, Agent BẮT BUỘC phải trích xuất tối thiểu 2 đặc điểm vật lý thật (chữ hiển thị trên ảnh, vật thể/bàn tay/chi tiết pixel thực tế) trước khi đưa ra bất kỳ kết luận hay câu trả lời nào. CẤM TUYỆT ĐỐI đoán mò theo mạch chat trước đó.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
