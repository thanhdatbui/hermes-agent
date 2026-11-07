---
name: farm-proxy-isolation-and-anti-direct-leak
description: Kỷ luật an toàn cách ly mạng farm, tuyệt đối cấm bypass proxy để chạy Direct trên mạng nhà làm lộ IP cá nhân và trigger checkpoint.
tags: [farm, proxy, network, security, gpm, s7]
---
# Farm Proxy Isolation & Anti-Direct Leak Discipline

## 1. Bối Cảnh & Nguy Cơ Lộ IP Cá Nhân (The Home-Network Direct Leak Trap)
Khi thao tác với các tài khoản quan trọng (Google AI Pro, TikTok, Gmail Farm):
- **Hiện tượng sai lầm**: Khi proxy farm (MobiProxy 4G `51xx`, R3G `514x/100xx`) gặp sự cố (502 Bad Gateway, timeout, ngắt kết nối), agent sốt sắng muốn mở trình duyệt GPM nên tự ý xóa proxy để chuyển sang Direct (mạng nhà cá nhân của Operator).
- **Hậu quả nghiêm trọng**:
  1. Mạng nhà cá nhân (FPT/Viettel tại Đà Nẵng,...) có ASN, dải IP và vị trí địa lý khác biệt 100% so với hạ tầng farm (Thái Bình, TP.HCM, dải di động MobiFone/Viettel 4G).
  2. Việc gửi request trực tiếp từ mạng nhà khiến Google / TikTok phát hiện sự dịch chuyển địa lý bất thường (Impossible Travel / Geo-mismatch), kích hoạt ngay cơ chế **Fraud / Abuse Detection**.
  3. Hậu quả tức thì: Google đá văng phiên (`sessionexpired`), bắt xác minh danh tính (`VALIDATION_REQUIRED`), hoặc khóa tài khoản vĩnh viễn (`TOS_VIOLATION`).

## 2. Invariant Bất Biến (Strict Network Isolation Invariant)
1. **CẤM TUYỆT ĐỐI CHẠY DIRECT MẠNG NHÀ**:
   - Trong mọi trường hợp thao tác GPM hoặc Automation Farm, CẤM agent tự ý gỡ bỏ proxy để chạy Direct khi chưa có lệnh rõ ràng từ User.
   - Tài khoản đã được quy hoạch chạy proxy nào (Mobi 4G, R3G, proxy S7) thì BẮT BUỘC chỉ được khởi động qua đúng proxy đó.
2. **KHI PROXY BỊ LỖI / TIMEOUT / 502**:
   - BẮT BUỘC coi đây là trạng thái **BLOCKED** do hạ tầng mạng ngoài.
   - Trích xuất bằng chứng (Curl/Socket error, 502 Bad Gateway) và báo cáo trực diện cho User.
   - TUYỆT ĐỐI CẤM "chữa cháy" bằng cách cắm qua mạng nhà hoặc đổi sang proxy lạ ngoài quy hoạch.
3. **ĐỒNG BỘ PROXY THIẾT BỊ (S7) VÀ TRÌNH DUYỆT (GPM)**:
   - Khi cứu tài khoản yêu cầu xác minh thiết bị: BẮT BUỘC Profile GPM và máy S7 phải đi qua cùng một cổng proxy hoặc cùng một gateway quy hoạch của cụm đó để đảm bảo tính nhất quán danh tính.
