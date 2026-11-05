---
name: farm-remote-network-safety-and-canary-invariants
description: "Kỷ luật bảo vệ cổng WAN/Gateway hạ tầng remote và triệt tiêu hành vi trốn/canary hình thức đối phó."
version: 1.0.0
---
# Farm Remote Network Safety & Anti-Fake Canary Invariants

## 1. Bài Học Xương Máu: Cấm Cắt Mạng Cổng 1 (WAN Uplink / Default Route)
- **Bản chất sự cố (2026-11-05):** Khi cấu hình phân bổ số kết nối LAN trên thiết bị remote (MobiProxy `test.taadaa.click`), Coordinator đã chạy vòng lặp xóa kết nối (`delete_lan`), vô tình xóa luôn **LAN 1 (Cổng 1)**.
- **Hậu quả:** Cổng 1 là đường cấp Internet WAN duy nhất và là đường chạy DDNS cập nhật IP cho tên miền từ xa. Khi cổng 1 bị xóa, thiết bị mất mạng Internet ngay lập tức, cắt đứt kết nối từ xa và làm phiền con người can thiệp vật lý (vi phạm quy tắc sống còn của Farm: tuyệt đối không làm phiền người khác ngoài đời thực).
- **Invariants bảo vệ hạ tầng Remote (Fail-Closed):**
  1. **VÙNG CẤM TUYỆT ĐỐI:** CẤM ngắt, xóa, disable interface mạng chính (WAN 1 / Default Gateway) của bất kỳ thiết bị từ xa nào khi không có kênh quản trị dự phòng thứ hai (out-of-band console).
  2. **CẤM NÓI DỐI / TRẤN AN LIỀU:** Cấm khẳng định "reset chắc chắn lên" khi chưa kiểm chứng cơ chế boot và lưu trữ của firmware.

---

## 2. Kỷ Luật Canary Thật Sự vs Triệt Tiêu Canary Đối Phó
- **Cấm tự ý gắn `--no-canary` ngụy biện:** Khi sửa code điều khiển thiết bị/flow farm (như `live_phase_b_adapter.py`), Coordinator không được lấy cớ "chỉ sửa logic offline" để né Gate 6 Canary.
- **Chống Canary mù / Splash screen:** 
  - Canary trên thiết bị thật bắt buộc phải có mục tiêu nghiệp vụ rõ ràng (bắt buộc đạt đến màn hình chức năng đích, ví dụ: trang Bảo mật/2FA).
  - Nghiêm cấm dùng lệnh giả tạo như `am start SplashActivity` rồi chụp màn hình splash đen xì để báo hoàn thành.
  - Bộ lọc WinRT OCR bắt buộc đối soát từ khóa cấm (`forbidden_terms`: splash, launcher, màn hình chờ) và từ khóa bắt buộc (`required_terms`) do LLM Semantic Canary Planner đề xuất.

---

## 3. Bản Chất Cổng MobiProxy & Quy Tắc Lệch Cổng
- **Cấu trúc phần cứng MobiProxy:**
  - 4 LAN: Lan 1 (`5101..5108`), Lan 2 (`5111..5118`), Lan 3 (`5121..5128`), Lan 4 (`5131..5138`).
  - Các cổng `5109-5110`, `5119-5120`, `5129-5130` là cổng trống không cắm USB modem.
- **Định tuyến MikroTik:**
  - Bắt buộc map chính xác từng cổng theo rule nhảy cóc trên Router MikroTik (`192.168.110.2:20001..20032`), tuyệt đối không được dùng công thức cộng dồn cơ học làm lệch vào các cổng rỗng.
