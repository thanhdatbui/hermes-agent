# Boundary Kích Hoạt Gate 6 (Media Evidence) & Quy Tắc Chống Spam Screencap Đen

## 1. Bản Chất Vấn Đề (Failure Mode)
- **Triệu chứng:** Trong các phiên thảo luận hạ tầng, chẩn đoán điện/UPS/mạng hoặc tư vấn lý thuyết, Coordinator vô thức chụp screencap ADB điện thoại S7 và đính kèm `MEDIA:<path>` ở cuối tin nhắn.
- **Hậu quả:** 
  - Máy S7 thường ở trạng thái `mWakefulness=Dozing` (ngủ sâu, tắt màn hình), khiến ảnh chụp ra đen ngòm vô dụng.
  - Gây ức chế cho người dùng ("Đang nói chuyện điện thì gửi ảnh S7 làm gì, không thể cứ spam ảnh như vậy").

## 2. Boundary Kích Hoạt Gate 6 Chuẩn (Action Verb + Artifact)
Gate 6 **CHỈ ĐƯỢC PHÉP KÍCH HOẠT** khi thỏa mãn MỌI điều kiện sau:
1. **Action Verb:** Có một lệnh/script can thiệp thực tế ĐÃ CHẠY trên thiết bị (batch job, canary run, fix bug handler, tap UI, recovery).
2. **Artifact:** Có kết quả thực thi cụ thể cần nghiệm thu bằng mắt trên màn hình thiết bị.
3. **Màn hình sáng:** Thiết bị phải ở trạng thái màn hình sáng (`mWakefulness=Awake`), hoặc có đánh thức trước khi chụp (`input keyevent 224`).

## 3. Danh Sách CẤM Kích Hoạt Gate 6 / CẤM Đính Kèm MEDIA
TUYỆT ĐỐI KHÔNG chụp screencap hay đính kèm `MEDIA:` trong các trường hợp sau:
- Thảo luận, tư vấn, hỏi đáp kỹ thuật (điện lưới, ổ cắm, UPS, mạng Wi-Fi, router, switch).
- Lập kế hoạch, đề xuất giải pháp chưa chạy thực tế trên thiết bị.
- Monitoring thụ động (chỉ đọc log, ping IP, inspect status, uptime).
- Khi không có hành động can thiệp vật lý nào diễn ra trong turn chat hiện tại.

## 4. Quy Tắc Khi Cần Lấy Ảnh Thiết Bị
- Nếu thực sự cần lấy ảnh hiện trường thiết bị đang ngủ, BẮT BUỘC đánh thức trước:
  ```bash
  adb -s <serial> shell "input keyevent 224"
  adb -s <serial> exec-out screencap -p > <path>
  ```
- Tuyệt đối không gửi ảnh đen kịt do chụp trong lúc máy đang dozing/sleep.
