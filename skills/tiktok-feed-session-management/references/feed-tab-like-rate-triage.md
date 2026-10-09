# Triage: Phân Tích Hiện Tượng Tỉ Lệ Like Tab Bạn Bè / Following Thấp Trên Báo Cáo Watchdog

## 1. Bản Chất Đo Lường vs Cấu Hình (Like Rate Gap Sau Case 178 & Case 184)
Trước đây (Plan cũ):
- Tab Bạn bè (`friends`) và Đang Follow (`following`) từng bị ép 100% video Deep Inspect (dump XML), kỳ vọng tỉ lệ like 70% - 80%.

Hiện tại (Từ Case 178 & Case 184):
1. **Fast Swipe Đa Tab (Case 178):**
   - Để giảm tải CPU, chống nghẽn UIAutomator trên Samsung S7 và xóa bỏ hành vi bot bất thường, tab Bạn bè và Following áp dụng cơ chế Fast Swipe xen kẽ tương tự For You.
   - Chu kỳ: Cứ 1 video Deep Inspect thì xen kẽ `2 – 4 video Fast Swipe` (lướt nhanh qua, không dump XML và tuyệt đối không thả tim).
2. **Mẫu số feed_counts tính gộp Fast Swipe (Case 184):**
   - Từ Case 184, mẫu số `feed_counts[feed_type]` trên Watchdog tính gộp toàn bộ các lượt `action in ("swipe", "fast_swipe")`.
   - Do đó, số lượng video hiển thị ở tab Bạn bè (ví dụ `31 video`) gồm:
     - ~60-70% là video Fast Swipe (0 tim).
     - ~30-40% là video Deep Inspect (có xét thả tim).
3. **Trần toán học kỳ vọng trên báo cáo:**
   - Cấu hình `_deep_like_rate` cho Friends là 65% trên các nhịp Deep Inspect.
   - Tỷ lệ like danh nghĩa đo được trên toàn bộ video tab Bạn bè tối đa chỉ đạt:
     $$\text{Rate}_{\text{Watchdog}} \approx \frac{1 \text{ (Deep Inspect)} \times 65\%}{1 + 2.5 \text{ (Fast Swipes)}} \approx \frac{65\%}{3.5} \approx 18.5\%$$
   - Khi cộng thêm yếu tố popup hoặc video đã like sẵn, tỷ lệ like Bạn bè hiển thị trên Watchdog dao động tự nhiên trong khoảng **10% – 15%** (hoàn toàn bình thường).

---

## 2. Vì Sao Tỉ Lệ Like Tab Bạn Bè Thực Tế Thường Đạt ~10% - 15%?
Qua phân tích log `log.jsonl` và `summary.txt` (Live Ca 2 - Phiên 1):
1. **Tỷ lệ Fast Swipe chiếm đa số:**
   - Ví dụ trong 31 video Bạn bè: 17 video Fast Swipe (0 tim), chỉ có 14 video Deep Inspect.
2. **Popup gợi ý & Thiếu nút Like trên video Deep Inspect (`button_not_found`):**
   - Tab Bạn bè trên các nick farm mới rất hay xuất hiện popup `follow_friends_suggestion_popup` ("Kết nối với bạn bè", gợi ý danh bạ/Facebook) che khuất video player hoặc hiển thị list rỗng.
   - Khi runner dismiss popup hoặc không tìm thấy element Like trong XML, lượt like bị bỏ qua (`button_not_found`).
3. **Video đã like sẵn (`already_liked`):**
   - Với các nick farm follow chéo nhau, khi xem lại video của bạn bè đã like ở các ca trước, code an toàn bỏ qua (`video_already_liked`).
4. **Hiệu suất Like trên Video Hợp Lệ:**
   - Trong 14 video Deep Inspect, sau khi trừ các video dính popup hoặc đã like sẵn, chỉ còn ~6 video có nút Like hợp lệ.
   - Runner thả tim thành công 4/6 video (~66.7%), bám sát 100% tỷ lệ cấu hình (`_deep_like_rate = 65%`).
5. **Cơ chế Fallback Màn Rỗng (Empty Feed Fallback - Case 165/180):**
   - Nick chưa follow nhiều bạn bè thường gặp màn hình gợi ý rỗng (không có bài đăng mới). Runner kích hoạt `fallback_to_for_you` để đưa máy về tab Đề xuất, dẫn đến mẫu số video Bạn bè trên toàn farm rất nhỏ (chỉ vài chục video / 80 máy).

---

## 3. Quy Trình Điều Tra & Đối Soát Chuẩn O(1)
Khi operator thắc mắc "sao tỉ lệ thả tim bạn bè thấp":
1. **Kiểm tra số liệu tổng hợp O(1) từ `summary.txt`:**
   ```python
   # Đếm feed_counts và like_counts từ summary.txt của các máy success
   # Xác định tổng số video Friends (swipes) và số tim thực tế (likes)
   ```
2. **Kiểm tra tỷ lệ Fast Swipe vs Deep Inspect ở tab Friends:**
   - Đếm nhãn `action: "fast_swipe"` vs `action: "swipe"` có `feed_type: "friends"`.
   - Nếu tỷ lệ Fast Swipe chiếm ~60-70%, mẫu số đã được pha loãng đúng thiết kế Case 178 + Case 184.
3. **Kiểm tra log `action="like_video"`:**
   - Lọc trong `log.jsonl`:
     - `res="success"`: Các lượt like thành công kèm `like_rate_percent=65`.
     - `err="button_not_found"`: Bị popup che hoặc không render nút Like.
     - `err="already_liked"`: Video đã like từ trước.
4. **Khẳng định kết luận vận hành:**
   - Tỷ lệ ~10-15% ngoài ngoặc là tỷ lệ trên TỔNG SỐ VIDEO (bao gồm cả Fast Swipe).
   - Tỷ lệ thực tế trên video Deep Inspect có nút Like vẫn đạt chuẩn ~65%.
