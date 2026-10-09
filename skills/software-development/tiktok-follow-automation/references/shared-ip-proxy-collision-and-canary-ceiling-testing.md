# Shared IP Proxy Collision & Canary Ceiling Testing

## 1. Sự Cố Trùng Lặp IP Proxy (1 IP : 2 Máy) & Lây Nhiễm Cờ Phạt (Cross-Machine Taint)

### Hiện trường thực tế (09/10/2026):
* Quy hoạch Farm Kibe: 80 máy Samsung S7 chia sẻ 39–40 đường proxy (tỷ lệ 1 Proxy : 2 Máy, ví dụ Cổng 5101 gán M1 & M39, Cổng 5116 gán M14 & M52).
* Trong 6 nick nòng cốt bị TikTok nhả follow sáng 09/10/2026, có 4 nick nằm trong 2 cặp chung chính xác 1 IP:
  * **Cặp Cổng 5116:** Lúc 06:21, M52 (`@vy.nguyen8730`) vào ca follow, ăn 1 follow rồi bị TikTok ngắt (`FOLLOW_FAILED`). Đúng 18 phút sau (06:39), M14 (`@hong.bo.anh83`) nhảy vào app cày follow trên chính IP 5116 đó -> TikTok đã gắn cờ nghi vấn IP từ 18 phút trước, M14 vừa bấm follow lượt đầu tiên là bị nhả ngay lập tức (0 lượt) và dính án phạt Cooldown 3 ngày.
* Đối soát lịch sử: Từng có 79 ca chạy trong đó 2 máy chung 1 IP cùng cày follow trong ngày, với hơn 7.200 lượt follow cách nhau dưới 10 phút (thậm chí 5–38 giây). Khi 2 máy cùng gửi write request (follow) lên TikTok từ cùng 1 IP trong khoảng thời gian hẹp, hệ thống Anti-Fraud của TikTok sẽ kích hoạt rate-limit chùm.

### Cơ Chế Bảo Vệ: Session-Level Mutex Theo IP ("1 Thức - 1 Dưỡng"):
* **Không phải khóa cả ngày (không làm giảm 50% công suất):** Phiên follow của 1 máy chỉ kéo dài 10–15 phút. Trong 24h (1.440 phút), chia lệch khung giờ (ví dụ Máy A chạy sáng, Máy B chạy chiều/tối).
* **Quy tắc Mutex:**
  - Tại một thời điểm, trên 1 IP chỉ cho phép tối đa 1 máy ở trạng thái `FOLLOW_SESSION` (hành vi ghi nhạy cảm).
  - Máy còn lại cùng IP đó trong lúc này chỉ được phép ở trạng thái `PASSIVE_FEED` (lướt xem video dưỡng sinh thuần túy) hoặc nghỉ hẳn.
  - Sau khi Máy A kết thúc phiên và nhả lock, Máy B mới được phép vào phiên follow của mình.

---

## 2. Chiến Lược Dò Trần Bằng Đội Dò Đường (Canary Cohort Testing)

### Cạm bẫy "Lấy mẫu số nhỏ áp đặt trần cả dàn":
* Không dùng toàn bộ dàn máy để vừa cày sản lượng vừa dò trần. Khi trần sập, cả dàn sẽ dính cờ đỏ hàng loạt (Blast Radius quá lớn).
* Không vội vàng kết luận trần cứng cho cả dàn chỉ dựa trên vài ca bị nhả lẻ tẻ.

### Phân tầng kiểm thử trần (Canary Architecture):
1. **90–95% Dàn chính (Core Fleet):** Giữ ở cận dưới an toàn tuyệt đối (ví dụ 8–10 follow/ca). Nhóm này chịu trách nhiệm tạo sản lượng đều đặn, không mạo hiểm.
2. **5–10% Đội dò đường (Canary Cohort):** Chọn ra 3–5 nick trâu nhất (những nick có `Max Safe` lịch sử từng đạt 40–50 như M28, M50). Chỉ nhóm nhỏ này mới được tăng dần tải (+2 follow mỗi chu kỳ) để thăm dò phản ứng của thuật toán TikTok.
3. **Quy tắc nghiệm thu trần:**
   - Nếu Canary vượt qua 3 chu kỳ sạch liên tiếp ở mức cao hơn -> Mới cân nhắc nâng nhẹ cận trên của dàn chính.
   - Nếu Canary dính nhả -> Bán kính thiệt hại chỉ gói gọn trong 2-3 nick thử nghiệm, 95% dàn chính hoàn toàn an toàn.

---

## 3. Chống Over-Engineering Trong Điều Phối Lịch Chạy

* **User Invariant:** Khi hệ thống đã có sẵn nhịp cơ sở tự nhiên (chu kỳ cách 2 ngày mới chạy 1 ca + dưỡng sinh random), CẤM tự ý đẻ thêm các luật phân bổ gượng ép như "chia chẵn/lẻ" hay "cụm ngày 1/ngày 2".
* Càng can thiệp nhiều rule cứng gượng ép, profile hành vi của farm càng mất tính ngẫu nhiên và dễ bị AI Anti-Fraud của TikTok phát hiện mẫu lặp.
