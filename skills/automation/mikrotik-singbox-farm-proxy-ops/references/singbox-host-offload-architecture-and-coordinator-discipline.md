# Giải Pháp Tách Sing-box Sang PC Host Để Giải Phóng CPU MikroTik & Kỷ Luật Thuyết Trình

## 1. Bản Chất Kỹ Thuật: Tại Sao Sing-box Làm Nghẽn CPU Mini PC MikroTik
- **Phần cứng MikroTik x86 RouterOS:** Được thiết kế tối ưu cho Routing, Switching, FastPath, Connection Tracking và Packet Filtering ở tầng L3/L4 (Kernel-space). Khi chỉ làm nhiệm vụ NAT/Routing, CPU RouterOS thường tiêu tốn < 15%.
- **Nghẽn cổ chai Container RouterOS:**
  - Sing-box chạy trong Container Docker của RouterOS giao tiếp qua card mạng ảo `veth-singbox`.
  - Mọi gói tin từ 80–160 máy S7 (cày video TikTok) khi chui vào Container bị **văng khỏi cơ chế tăng tốc FastPath**.
  - Nhân Linux của Container phải thực hiện hàng chục nghìn ngắt mạng phần mềm (`softirq`) và chuyển đổi ngữ cảnh (`context switch`) giữa Kernel-space và User-space để unpack/repack L7 Proxy.
  - Với lưu lượng 60–120 Mbps sinh ra 40.000 – 105.000 packets/giây (pps), CPU Mini PC 4 nhân bị kẹt cứng ở ngưỡng **92% – 99%**.

## 2. Kiến Trúc "Tàng Hình" Di Dời Sing-box Sang PC Kibe (Zero-Config S7)
Không cần cài app nặng nề (V2Ray, tun2socks) lên điện thoại S7 và không cần chạm vào cấu hình 160 máy:
- **Nguyên lý:**
  1. **80–160 Samsung S7:** Giữ nguyên 100% cấu hình Wi-Fi Proxy trỏ về `192.168.110.2:20001..20280`. Khi proxy sập, cơ chế Captive Portal Check của Android vẫn tự gắn "Dấu chấm than" và ngắt kết nối an toàn, bảo đảm Zero-Leak.
  2. **PC Kibe (`192.168.110.123`):** Chạy tiến trình Sing-box Windows (hoặc Docker WSL2). Lắng nghe trên các cổng `20001..20280` và forward traffic ra Thái Bình (MobiProxy + R3G). Chip desktop i5/i7 chỉ tốn 1–3% CPU để gánh toàn bộ 160 luồng này.
  3. **MikroTik RouterOS (`192.168.110.2`):**
     - Sửa rule NAT chuyển hướng:
       ```routeros
       /ip firewall nat add chain=dstnat dst-address=192.168.110.2 dst-port=20001-20280 protocol=tcp action=dst-nat to-addresses=192.168.110.123
       ```
     - Tắt vĩnh viễn container Docker `*6` trên RouterOS.
     - Toàn bộ gói tin được MikroTik chuyển tiếp ở tầng phần cứng (FastPath wire-speed), đưa CPU MikroTik rơi từ 96% về dưới 15%.

## 3. Kỷ Luật Thuyết Trình & Ứng Xử Của Coordinator (Anti-Advisor-Blabbering)
- **Tập trung vào kết luận và giải pháp:**
  - Hội đồng Cố vấn (Advisors) là cơ chế thẩm định nội bộ của Coordinator để tìm ra rủi ro và giải pháp.
  - **CẤM TUYỆT ĐỐI** nhai lại nguyên văn các câu dài dòng, các đoạn tranh luận lý thuyết hay trích xuất biên bản của Advisor cho User khi User đang hỏi phương án hành động cụ thể ("Chứ k có cách nào giảm tải cho mini pc à?").
  - Khi User hỏi giải pháp, Coordinator phải đưa ra ngay:
    1. **Bản chất vấn đề** (ngắn gọn, ví dụ đời thực dễ hiểu).
    2. **Phương án khả thi nhất** (được Advisor đồng thuận).
    3. **Tác động đến hệ thống** (có phải cài lại máy không, rủi ro gì).
- **Tuyệt đối cấm lặp lại câu hỏi đã trả lời hoặc bỏ qua thắc mắc của User:**
  - Khi User hỏi một khái niệm kỹ thuật ("Đồng bộ tự động IP sang R3G là sao?"), BẮT BUỘC trả lời trực diện vào cơ chế vận hành thực tế trước, không được lảng tránh hay chuyển chủ đề.
