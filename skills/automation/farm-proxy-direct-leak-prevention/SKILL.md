---
name: farm-proxy-direct-leak-prevention
description: Kỷ luật cấm tuyệt đối tự ý fallback Direct mạng nhà khi proxy chết và quy trình xử lý lỗi kết nối GPM/S7.
version: 1.0.0
tags: [farm, proxy, direct-leak, fail-closed, gpm, s7]
---
# Farm Proxy Direct Leak Prevention & Fail-Closed Discipline

## 1. Bản chất sự cố & Cảnh báo nghiêm trọng
Khi vận hành tài khoản Farm (Gmail, TikTok, Google AI Pro, Codex, v.v.) trên GPMLogin hoặc thiết bị Android (Samsung S7):
- **Hành vi sai trái nghiêm trọng (Vi phạm nguyên tắc an toàn IP):** Khi proxy gán ban đầu gặp lỗi (ví dụ: timeout, 502 Bad Gateway), Coordinator tự ý gỡ bỏ proxy để chạy `Direct` (ăn thẳng vào mạng nhà FPT/Viettel của Operator) với lý do "thử xem màn hình tiếp theo là gì" hoặc "mạng nhà đang vào được".
- **Hậu quả khôn lường:**
  1. Lộ toàn bộ IP mạng nhà thật của Operator lên hệ thống phòng thủ của Google/TikTok.
  2. Phá vỡ fingerprint địa lý của tài khoản (đang nuôi ở Thái Bình / Proxy US tự nhiên nhảy sang IP mạng nhà cá nhân).
  3. Kích hoạt cờ bảo vệ hoặc án phạt tài khoản diện rộng.

## 2. Quy tắc cấm tuyệt đối (Hard Invariants)
1. **CẤM TUYỆT ĐỐI tự ý chuyển Profile GPM hoặc thiết bị sang Direct:**
   - Dù gặp bất kỳ lỗi gì (`502 Bad Gateway`, `Connection refused`, `Proxy timeout`), Coordinator **TUYỆT ĐỐI KHÔNG ĐƯỢC PHÉP** chuyển trường `raw_proxy` thành rỗng `""` hoặc bỏ proxy để chạy direct trên mạng nhà.
   - Khi proxy chết: **BẮT BUỘC DỪNG LẠI (FAIL-CLOSED)** và báo cáo trạng thái lỗi proxy thật cho Operator.
2. **Tuân thủ đúng chỉ đạo mapping proxy:**
   - Nếu Operator chỉ đạo: "dùng R3G gán cùng proxy S7", Coordinator BẮT BUỘC phải trỏ profile vào đúng cổng proxy tương ứng của S7/R3G (ví dụ: `192.168.110.2:20009` hoặc `192.168.110.2:10009`).
   - Nếu cổng đó không thông mạng (báo 502/timeout), phải báo cáo nguyên nhân tầng mạng (ví dụ: upstream tinyproxy trên R3G chưa chạy, box 4G chưa cấp WAN), TUYỆT ĐỐI KHÔNG ĐƯỢC tự chế đi đường tắt bằng mạng nhà.
3. **Phân biệt rạch ròi giữa Mạng LAN nội bộ vs Mạng Egress Internet:**
   - Dù PC Kibe và S7 cùng cắm chung mạng LAN `192.168.110.x`, nhưng luồng ra Internet của thiết bị farm bắt buộc phải đi qua cổng Proxy riêng được quy hoạch. Không được đánh đồng việc "cùng ping thấy nhau trong LAN" với việc "cho phép dùng chung IP mạng nhà ra ngoài".
