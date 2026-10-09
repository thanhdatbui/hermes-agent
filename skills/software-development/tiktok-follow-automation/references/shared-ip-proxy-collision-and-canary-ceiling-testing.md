# Shared IP Proxy Collision & Canary Ceiling Testing

## 1. Sự Cố Trùng Lặp IP Proxy (1 IP : 2 Máy) & Lây Nhiễm Cờ Phạt (Cross-Machine Taint)

### Hiện trường thực tế (09/10/2026):
* Quy hoạch Farm Kibe: 80 máy Samsung S7 chia sẻ 39–40 đường proxy (tỷ lệ 1 Proxy : 2 Máy, ví dụ Cổng 5101 gán M1 & M39, Cổng 5116 gán M14 & M52).
* Trong 6 nick nòng cốt bị TikTok nhả follow sáng 09/10/2026, có 4 nick nằm trong 2 cặp chung chính xác 1 IP:
  * **Cặp Cổng 5116:** Lúc 06:21, M52 (`@vy.nguyen8730`) vào ca follow, ăn 1 follow rồi bị TikTok ngắt (`FOLLOW_FAILED`). Đúng 18 phút sau (06:39), M14 (`@hong.bo.anh83`) nhảy vào app cày follow trên chính IP 5116 đó -> TikTok đã gắn cờ nghi vấn IP từ 18 phút trước, M14 vừa bấm follow lượt đầu tiên là bị nhả ngay lập tức (0 lượt) và dính án phạt Cooldown 3 ngày.
* Đối soát lịch sử: Từng có 79 ca chạy trong đó 2 máy chung 1 IP cùng cày follow trong ngày, với hơn 7.200 lượt follow cách nhau dưới 10 phút (thậm chí 5–38 giây).
* **BẪY DỮ LIỆU LỖI 31/08 & 01/09 (User Correction):** Dữ liệu ngày 31/08 và 01/09 đo được tỷ lệ nhả 0% thực chất là do HÀM VERIFY CŨ BỊ LỖI (nhận diện sai trạng thái follow), sau đó mới được vá lại. Khi lọc riêng dữ liệu chuẩn xác của tháng 10/2026:
  - Co-run (2 máy/IP cùng chạy trong ngày): 24 / 34 ca bị nhả (**70.6%**) 🔴
  - Solo (1 máy/IP chạy lẻ): 39 / 107 ca bị nhả (**36.4%**)
  -> Rủi ro dính nhả khi chạy đôi cùng IP cao gần gấp đôi so với chạy đơn!

### Hiện tượng "Ăn nhả dắt dây" (Cascading Domino Failure):
Truy vết chi tiết timestamp 8 ca chết đôi trên cùng IP tháng 10/2026 chứng minh: Khi Máy A dính `FOLLOW_FAILED`, TikTok cắm cờ IP nghi vấn. Máy B vào sau trong vòng 2 – 25 phút bị dính nhả ngay từ lượt đầu (0 lượt):
- 09/10 (Port 5102): M2 fail 06:22 -> M40 vào 06:24 dính nhả ngay (cách 1.9 phút).
- 09/10 (Port 5116): M52 fail 06:21 -> M14 vào 06:39 dính nhả ngay (cách 18.2 phút).
- 09/10 (Port 5122): M56 fail 06:22 -> M18 vào 06:38 dính nhả ngay (cách 16.3 phút).
- 07/10 (Port 5104): M4 fail 06:31 -> M42 vào 06:39 dính nhả ngay (cách 8.7 phút).
- 07/10 (Port 5132): M64 fail 06:25 -> M26 vào 06:43 dính nhả ngay (cách 18.3 phút).
- 07/10 (Port 5137): M69 fail 06:43 -> M31 vào 06:50 dính nhả ngay (cách 7.4 phút).
- 07/10 (Port 10001): M72 fail 06:29 -> M33 vào 06:47 dính nhả ngay (cách 17.9 phút).
- 03/10 (Port 5131): M25 fail 06:24 -> M63 vào 06:46 dính nhả ngay (cách 22.8 phút).

### Giải Pháp Chuẩn: IP Circuit Breaker (Cầu Dao Tự Ngắt Theo IP)
* **Bẫy Cấm Cứng / Session Mutex (User Correction):** Nếu cấm cứng 1 IP / 1 máy hoặc khóa mutex theo phiên trong ca chạy batch thì sẽ làm mất 50% công suất của dàn máy trong phiên đó.
* **Cơ chế Soft Guard tối ưu (Đã triển khai):**
  1. **Tự động ngắt khi có sự cố:** Khi Máy A dính `FOLLOW_FAILED` (`set_follow_failed` trong `follow_state.py`), hàm `trip_ip_breaker(machine)` tự động kích hoạt giật cầu dao, ghi nhận proxy bị `TRIPPED` vào bảng `ip_circuit_breaker` trong SQLite `tiktok_tracker.db` đến hết ngày (`23:59:59`).
  2. **Safe-skip máy anh em:** Khi Máy B chuẩn bị chạy (`run_follow.py`), preflight gọi `check_ip_breaker(machine)`. Nếu IP đang bị ngắt, Máy B tự động skip ca với trạng thái `CIRCUIT_BREAKER_SKIPPED` (`failed=False`, `follow_failed=False`), không phạt nick, đồng thời ghi nhận `saved_machines` vào DB.
  3. **Giám sát trực quan:** Dashboard port 1905 hiển thị widget `⚡ Cầu Dao Tự Ngắt IP` và gắn nhãn Proxy Port + Partner Machine (`M28 :5134 (🔗M66)`) trên ma trận.

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
