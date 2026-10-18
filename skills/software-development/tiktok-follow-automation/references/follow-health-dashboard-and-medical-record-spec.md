# Follow Health Dashboard & Sổ Bệnh Án UX/Architecture Specification

## Bối cảnh & Vai trò
Dashboard theo dõi sức khỏe Follow (`follow_health`) và Sổ Bệnh Án chi tiết (`follow_records` / `follow_detail_component.py`) là trung tâm giám sát an toàn cho toàn bộ farm tài khoản TikTok. Khi tài khoản bị phạt, nhả follow, hoặc dưỡng sau vi phạm, hệ thống xếp loại và cấp quota dò an toàn tự động.

## 1. Nguyên Tắc Thiết Kế UI/UX Sổ Bệnh Án (Mobile & Desktop)
- **CẤM giấu sổ bệnh án trong popup/modal bé**: Trên thiết bị di động (màn hình hẹp), modal 2 cột cố định (`display: flex`) sẽ khiến cột chi tiết Quota và Bảng UID bị đẩy văng ra ngoài khung nhìn.
- **First-Class Tab**: Sổ Bệnh Án phải được nâng cấp thành 1 Tab độc lập toàn màn hình (`setView('follow_records')`) trên thanh điều hướng chính của Dashboard.
- **Bố cục Responsive**:
  - Desktop (>900px): Master-detail 2 cột (trái: danh sách nick; phải: Quota + Bảng UID).
  - Mobile (<=900px): Tự động chuyển thành dạng cột dọc (`flex-direction: column`), danh sách nick giới hạn chiều cao tối đa (`max-height: 34vh`), nhường không gian bên dưới cho dữ liệu bệnh án và bảng UID.

## 2. Phân Nhóm Tài Khoản & Bộ Lọc Nhanh (Anti-Scroll)
Khi farm có hàng nghìn tài khoản, tuyệt đối không bắt người vận hành cuộn chuột tìm kiếm. Phải cung cấp các nút pill-tab chuyển nhanh:
1. **🔴 Cooldown (Bị nhả)** (`tier: cooldown`): Các nick bị đánh gậy nhả follow hoặc vi phạm streak, đang chịu thời gian đóng băng an toàn.
2. **🌱 Hồi phục 1** (`tier: probation_tier1`): Giai đoạn dưỡng ban đầu sau khi mãn hạn cooldown hoặc tài khoản mới vào guồng. Quota thăm dò an toàn ở mức tối thiểu (4-5 fl/ca).
3. **🟡 Hồi phục 2** (`tier: probation_tier2`): Giai đoạn dưỡng nâng cao sau khi đã tích lũy ca sạch. Quota tăng dần (6-8 fl/ca) trước khi đánh giá tốt nghiệp.
4. **🟢 Khỏe (Nòng cốt)** (`tier: healthy` / `graduated: true`): Tài khoản đã tốt nghiệp, chạy theo Quota tự động và trần an toàn đã chứng minh.

> **LƯU Ý NGHIỆP VỤ BẮT BUỘC**: Tuyệt đối không gộp chung `probation_tier1` và `probation_tier2` thành một nhãn "Hồi phục" duy nhất. Phải tách rõ thành 2 nhóm riêng trên cả giao diện danh sách lẫn thanh tab đếm số lượng để người vận hành phân biệt được tiến trình hồi phục của nick.

## 3. Tương Tác 4 Thẻ Chỉ Số Quota
Bốn thẻ chỉ số trên đầu trang bệnh án cần có tooltip giải thích rõ ràng và hỗ trợ tương tác:
- **Nhóm Cohort (`rookie` / `mid` / `veteran`)**: Bấm vào thẻ để tự động kích hoạt bộ lọc danh sách tài khoản theo đúng nhóm Cohort đó.
  - *Rookie*: < 30 follow tích lũy, trần an toàn tối đa 4-6 fl.
  - *Mid*: 30 - 99 follow tích lũy, trần an toàn 4-8 fl.
  - *Veteran*: >= 100 follow tích lũy, trần an toàn 5-9 fl (+10% canary probe).
- **Trần Đã Chứng Minh (`proven_safe_ceiling`)**: Số lượng follow cao nhất từng hoàn thành an toàn trong lịch sử.
- **Trần Dò Ca Tới (`active_ceiling`)**: Quota chỉ tiêu mà bộ lập lịch sẽ cấp cho ca chạy tiếp theo.
- **Gãy Gần Nhất (`last_failed_ceiling`)**: Mức quota tại ca chạy bị nhả follow gần nhất (dùng để xác định ngưỡng trần nguy hiểm cần tránh).
