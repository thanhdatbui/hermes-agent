# Case: Tỷ Lệ Like Thực Tế Bị Pha Loãng Do Fast Swipe & Trọng Số Phân Bổ Tab Trong Nuôi Feed (2026-10-03)

## 1. Hiện tượng & Phản ánh từ Thực địa
- User phản ánh: Tỷ lệ thả tim (like rate) thực tế của các nick (kể cả nick đã có bạn bè và following ở Row 1 & Row 2) luôn chỉ loanh quanh 10% – 20%, dù cấu hình logic ghi nhận tỷ lệ thích cho tab Following là 35% và Friends là 45% – 65%.
- Trích xuất dữ liệu đo kiểm thực tế trên 80 máy chạy Row 1 tại `D:/Taadaa/runtime/kibe/live/2026-10-03`:
  - **Ca 06:00 (Row 1 - 80 máy):**
    - Tổng like toàn ca: 190 / 1.399 video (**13.6%**).
    - For You: 165 / 1.270 video (**13.0%**).
    - Following: 4 / 39 video (**10.3%**) — chỉ 10/80 máy có lượt xem tab Following.
    - Friends: 21 / 90 video (**23.3%**) — chỉ 16/80 máy có lượt xem tab Friends.
  - **Ca 08:00 (Row 1 - 80 máy):**
    - Tổng like toàn ca: 154 / 1.303 video (**11.8%**).
    - Following: 8 / 71 video (**11.3%**) — chỉ 12/80 máy ghé xem.
    - Friends: 6 / 44 video (**13.6%**) — chỉ 8/80 máy ghé xem.

## 2. Nguyên nhân Gốc rễ Kỹ thuật (Root Cause)

### A. Pha loãng do cơ chế Fast Swipe (Lướt nhanh xen kẽ Deep Inspect)
- Trong `feed_swipe_smoke.py`, cơ chế Fast Swipe xen kẽ được kích hoạt để giảm tải CPU và tránh dump UI XML liên tục:
  - Cứ sau 1 video **Deep Inspect** (có dump XML, có chụp ảnh, có cơ chế like), hệ thống sẽ chạy 2 – 4 video **Fast Swipe**.
  - **Tại các video Fast Swipe:** Code chạy lệnh vuốt và gọi `continue` ngay sau khi kiểm tra focused activity. Hoàn toàn **KHÔNG kiểm tra like và KHÔNG thả tim (like_rate = 0%)**.
  - Hệ quả: Trong 1 phiên nuôi 18 video, chỉ có khoảng 5 – 6 video được Deep Inspect. Tỷ lệ like cấu hình (ví dụ Friends: 65%, Following: 35%) **chỉ áp dụng trên 5 – 6 video Deep Inspect này**. Khi tính trên tổng 18 video của cả phiên, tỷ lệ like thực tế bị chia 3, tụt xuống chỉ còn **10% – 15%**.

### B. Trọng số phân bổ tab (70/15/15) khiến đa số máy không ghé tab Following / Friends
- `DEFAULT_FEED_DISTRIBUTION`: For You (70%), Following (15%), Friends (15%).
- Cơ chế đổi tab `videos_until_tab_decision` chọn ngẫu nhiên mỗi 3 – 8 video.
- Trong một phiên nuôi 16 – 22 video (trung bình 18 video), cơ hội bốc thăm đổi tab chỉ xảy ra 2 – 3 lần. Với xác suất 70% rơi vào For You mỗi lần bốc, có tới **>80% số máy trong ca không bao giờ chuyển sang tab Following hay Friends**.
- Ngoài ra, nếu tab Friends / Following rỗng nội dung hoặc hiện banner gợi ý kết nối bạn bè, cơ chế fallback tự động đẩy máy trở về tab For You ngay tại video đầu tiên.

## 3. Bài học Vận hành & Hướng Xử lý
1. **Muốn tỷ lệ like thực tế đạt 40% – 60% cho tab Bạn bè / Following:**
   - Cần cấu hình riêng cho tab Friends / Following: giảm chu kỳ Fast Swipe (hoặc tắt Fast Swipe trong tab Friends để 100% video bạn bè đều được inspect và like).
   - Nâng `_deep_like_rate` cho Friends lên 85% – 90% nếu vẫn giữ Fast Swipe.
2. **Cân bằng lại phân bổ tab cho nick đã có kết nối:**
   - Với các nick Row 1 & 2 đã có bạn bè/following, điều chỉnh `feed_distribution` sang tỷ lệ cân bằng hơn (ví dụ 50% For You / 25% Following / 25% Friends) để máy có cơ hội tương tác chéo bài của nhau trong farm.
