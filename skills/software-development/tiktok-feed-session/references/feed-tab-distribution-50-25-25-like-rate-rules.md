# Chuẩn hóa Phân Bổ Tab (50/25/25) và Tỷ Lệ Thả Tim Thực Tế trong Feed Session

## 1. Hiện tượng & Bằng chứng thực tế (Log hiện trường)
- **Vấn đề đối soát:** Dù cấu hình like rate `Following: 35%` và `Friends: 45%` (Deep inspect 65%), nhưng log thực tế toàn ca 80 máy (Row 1) tỷ lệ like thực tế chỉ loanh quanh **10% – 14%**:
  - `Following`: chỉ 10.3% – 11.3% likes.
  - `Friends`: chỉ 13.6% – 23.3% likes.
  - Hơn 80% số máy không hề ghé sang tab Following hay Bạn bè trong suốt phiên 18 video.

## 2. Nguyên nhân gốc rễ kỹ thuật
1. **Cơ chế Fast Swipe (Lướt nhanh xen kẽ):**
   - Cứ 1 video xem kỹ (Deep Inspect) thì có 2–4 video lướt nhanh (Fast Swipe).
   - Fast Swipe hoàn toàn KHÔNG dump XML và KHÔNG thả tim (`like = 0%`).
   - Do đó, tỷ lệ like tại nhịp Deep Inspect bị pha loãng mạnh khi tính trên tổng số video của phiên.
2. **Phân bổ tab cũ quá lệch về For You (70/15/15):**
   - Thuật toán bốc thăm đổi tab (`_weighted_feed_choice`) diễn ra mỗi 3–8 video. Với 70% xác suất rơi vào For You, trong 18 video chỉ có 2–3 lần bốc thăm, khiến đa số máy ở lì trong For You cả phiên.

## 3. Quy tắc chuẩn hóa (User chốt 2026-10-03)
- **Giữ nguyên 100% chu kỳ lướt:**
  - TUYỆT ĐỐI KHÔNG tắt Fast Swipe và KHÔNG sửa `videos_until_deep_inspect` (vẫn giữ 2–4 video lướt nhanh xen kẽ 1 video xem kỹ) để đảm bảo CPU/RAM máy farm vận hành nhẹ nhàng, an toàn.
- **Tăng kịch khung tỷ lệ thả tim ở nhịp xem kỹ (Deep Inspect):**
  - `Tab Bạn bè (Friends)`: Nâng lên **`95%`** (gần như gặp video bạn bè là thả tim ngay).
  - `Tab Following`: Nâng lên **`85%`**.
  - Tỷ lệ nền mềm động (`_feed_like_rates`): Following `55% – 75%` (base 65%), Friends `75% – 95%` (base 85%).
- **Cân bằng phân bổ tab sang 50/25/25:**
  - `DEFAULT_FEED_DISTRIBUTION`:
    - `FEED_TYPE_FOR_YOU`: **`0.50`** (50%)
    - `FEED_TYPE_FOLLOWING`: **`0.25`** (25%)
    - `FEED_TYPE_FRIENDS`: **`0.25`** (25%)
  - Giúp cơ hội ghé thăm tab của nhau tăng gấp đôi trong mỗi phiên 18 video (trung bình 4–5 video Following và 4–5 video Bạn bè).
