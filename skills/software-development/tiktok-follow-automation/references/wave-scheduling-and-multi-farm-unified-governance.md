# Wave Scheduling & Multi-Farm Unified Governance (Kibe + Admin)

## 1. Bản Chất Kỹ Thuật Anti-Fraud: Sticky IP vs Wave Scheduling

### Lợi ích của Residential Sticky Proxy:
- Thuật toán TikTok gắn chặt bộ 3: `[Hardware Device + ASN/Dải IP Cố Định + Vị Trí]`.
- Giữ nguyên IP ổn định trong thời gian dài (Home Wi-Fi pattern) giúp nick tích lũy **Aging Trust Score**.
- Tuyệt đối tránh xoay IP liên tục (Rotating proxy) vì sẽ kích hoạt cờ **Impossible Travel** và bóp reach/chặn action.

### Rủi ro Co-run Cùng IP & Hiện Tượng Dắt Dây (Cascading Failure):
- Khi 2 máy chạy chung 1 IP gửi request follow gần như đồng thời (hoặc cách nhau vài phút), TikTok nhận diện lưu lượng bất thường từ cùng 1 IP gia đình.
- Nếu Máy A bị dính cờ nhả (`FOLLOW_FAILED`), IP đó bị TikTok tạm khóa trong 12-24h.
- Máy B vào sau sẽ bị nhả ngay ở lượt đầu tiên (0 lượt) dù nick hoàn toàn khỏe mạnh.

---

## 2. Kiến Trúc Lập Lịch Phân Tách 2 Wave (Proxy-Bucket Partitioning)

Để bảo toàn 100% công suất mà không bị trảm dắt dây:

```
[40 Cổng Proxy] (Mỗi cổng 2 máy: M1-M39, M2-M40...)
       │
       ▼
[Wave 1 (Turn 1)]: Bốc đúng 1 máy / proxy (Tối đa 40 máy) -> Shuffle ngẫu nhiên
       │
       ├─► 100% các máy chạy song song hoàn toàn ĐỘC LẬP IP
       │
       ▼
[Canary Circuit Breaker Gate]:
       ├─► Nếu Máy A dính FOLLOW_FAILED -> Cúp cầu dao IP cổng đó đến hết ngày (23:59:59)
       │
       ▼
[Wave 2 (Turn 2)]: Chạy 40 máy thứ hai còn lại
       ├─► Các cổng sạch: Máy B vào chạy bình thường
       └─► Các cổng đã bị cúp: Máy B tự động Safe-Skip (CIRCUIT_BREAKER_SKIPPED), cứu nick 100%
```

---

## 3. Quy Chuẩn Vận Hành Đủ 2 Cụm Farm (Unified Kibe + Admin)

Mọi báo cáo, dashboard và công cụ thống kê BẮT BUỘC bao quát cả 2 cụm:
- **Cụm Kibe:** Máy 1 – 80 (640 accounts), proxy cổng `51xx` (`D:/OneDrive/TaadaaData/kibe/PROXYgandienthoai.xlsx`).
- **Cụm Admin:** Máy 201 – 280 (615 accounts), proxy cổng `100xx` (`D:/OneDrive/TaadaaData/admin/PROXYgandienthoai.xlsx`).
- **Tổng Quy Mô Toàn Farm:** 160 máy / 1.255 accounts.
- **Tập Trung CSDL & State:** Toàn bộ dữ liệu follow, session stats và circuit breakers lưu chung tại `D:/Taadaa/data/tiktok_tracker.db` để dễ dàng tra cứu, kiểm soát đồng bộ toàn farm.
