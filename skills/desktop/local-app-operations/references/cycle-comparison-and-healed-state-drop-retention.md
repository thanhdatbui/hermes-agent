# Cycle Comparison and Healed-State Drop Retention Pitfalls in Farm Dashboards

## 1. The Healed State Drop-Erasure Pitfall (Trạng Thái Hồi Phục Nuốt Chửng Lịch Sử Drop)

### Triệu chứng
Khi người vận hành chạy script giải cứu/phục hồi tài khoản (Reconciliation / Healing script, ví dụ `reconcile_unfair_streaks.py`), script gỡ cờ cooldown (`cooldown_until_date = None`, `follow_failed = False`) và chuyển tài khoản sang diện Hồi Phục.
Ngay sau đó, trên Dashboard Sổ Bệnh Án / Phân Tích Chu Kỳ (`cycle_comparison`), chỉ số:
- **Tỉ lệ ăn nhả đuôi (chạm trần)** tụt về `0.0% (0 nick)`!
- **Tỉ lệ chạy SẠCH 100%** nhảy vọt lên `100.0%` ảo!

### Nguyên nhân cốt lõi
Hàm tính toán chu kỳ sử dụng logic phụ thuộc vào cờ trạng thái hiện tại:
```python
# SAI LẦM: Kiểm tra drop dựa trên trạng thái cooldown hiện tại
has_drop = bool(a.get("is_in_cooldown")) and a.get("drop_day") in cycle_dates
```
Khi nick vừa được giải cứu (xóa `is_in_cooldown`), câu điều kiện trên trả về `False`. Kết quả là toàn bộ sự kiện nhả follow / chạm trần thực tế đã diễn ra trong chu kỳ đó bị xóa sổ khỏi thống kê lịch sử, tạo ra báo cáo "sạch ảo" gây nhầm lẫn nghiêm trọng cho người vận hành.

### Giải pháp chuẩn hóa (Event-Based Drop Retention Invariant)
Thống kê lịch sử chu kỳ BẮT BUỘC phải dựa trên sự kiện lịch sử bất biến (Event Log), hoàn toàn tách rời khỏi cờ cooldown động ở thời điểm hiện tại:
```python
# CHUẨN XÁC: Đánh giá dựa trên ngày lỗi thực tế, không phụ thuộc cờ cooldown hiện tại
last_failed_date = a.get("last_failed_date")
drop_day = a.get("drop_day")
has_drop = (last_failed_date in cycle_dates) or (drop_day in cycle_dates)
```

---

## 2. Multi-Cycle Cohort Breakdown Standard (Tiêu Chuẩn So Sánh Đa Chu Kỳ Theo Nhóm)

Khi phân tích hiệu quả vận hành của farm (như chu kỳ Parity 96h / 4 ngày luân phiên):
1. **Không dừng lại ở 1 chu kỳ đối chiếu:** Luôn hiển thị chuỗi thời gian tối thiểu **3–4 chu kỳ liên tiếp** (ví dụ: `19–20/10`, `15–16/10`, `11–12/10`, `07–08/10`) để người vận hành nhận diện xu hướng thoái hóa hoặc phục hồi của dàn nick.
2. **Bắt buộc phân rã theo nhóm Cohort (Cohort Breakdown):**
   - 🟢 **Cựu binh (Veteran):** Tỷ lệ sạch vs chạm trần khi nã trần cao.
   - 🟡 **Trung cấp (Mid):** Tốc độ leo trần và ngưỡng gãy trung gian.
   - 🔴 **Tân binh (Rookie):** Tỷ lệ tù ngầm / nhả ngay phát đầu (`fl == 0`).
3. **Phân định rõ "Tổng Active" vs "Thực Chiến (Eligible)":**
   - `Total Active`: Toàn bộ nick có lệnh chạy trong ngày.
   - `Immediate Drop (fl == 0)`: Nick vừa vào bấm phát đầu bị bật ngược lại hoặc check anchor fail (tù nặng / non).
   - `Eligible (fl >= 1)`: Nick có lực thực chiến, hoàn thành ít nhất 1 follow an toàn.

---

## 3. IP Circuit Breaker Saved-Machine Cross-Impact (Hiệu Ứng Khóa Chùm Cựu Binh)

Khi một thiết bị làm ngắt IP Circuit Breaker 48h (ví dụ M17 làm trip proxy lúc 06:51):
- Thiết bị chạy chung proxy (nhất là `saved_machines`, ví dụ M55 đi cùng M17 trên proxy 5121) sẽ bị ngắt bảo vệ 48h.
- Hậu quả: Nick cựu binh trên máy cứu cánh (như `anh.le0052` M55 R1) hoàn toàn không được chạy trong suốt chu kỳ 48h đó dù tài khoản hoàn toàn khỏe mạnh.
- **Quy tắc điều tra:** Khi thấy số nick thực chiến của nhóm Cựu binh sụt giảm bất thường giữa các chu kỳ, luôn truy vấn bảng `ip_circuit_breaker` để xác minh xem có cựu binh nào bị "cháy thành vạ lây" do máy partner làm sập proxy hay không trước khi kết luận nick bị bệnh.
