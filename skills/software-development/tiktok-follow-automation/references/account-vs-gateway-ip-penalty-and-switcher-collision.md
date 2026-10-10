# Account-Level vs Gateway IP Penalty & Switcher Collision in TikTok Follow

## 1. Bản Chất Kép Của Án Phạt: Account Penalty vs Gateway IP Anomaly

Khi tài khoản TikTok bị nhả follow (`FOLLOW_FAILED`), hệ thống Anti-Spam của TikTok kích hoạt **đồng thời 2 tầng chế tài khác nhau**:

1. **Tầng Tài Khoản (Account-level Penalty):**
   - Án phạt ghi trực tiếp vào hồ sơ tài khoản trên máy chủ TikTok.
   - Đặc điểm: Một khi đã dính án, tài khoản đó đi đâu (đổi máy, đổi IP, đổi mạng 4G) trong vòng 3–7 ngày tới đều sẽ bị nhả follow ngay lập tức.
   - Xử lý: **Bắt buộc áp dụng Graduated Probation Ladder (Quota hồi phục 3–5 follow/ca)** sau khi mãn hạn Cooldown để re-test độ trust của bản thân nick.

2. **Tầng Gateway / Proxy IP (Gateway-level Anomaly Flag):**
   - Án phạt gắn cờ tạm thời lên dải Subnet / Proxy IP: *"IP này đang có hành vi spam tương tác bất thường"*.
   - Đặc điểm: Khi IP đang bị cắm cờ, **bất kỳ nick nào (kể cả cựu binh siêu khỏe 100–240 follow)** bấm follow qua IP đó đều bị gateway chặn và tuột số (nhả follow).
   - Dữ liệu đối soát thực tế: Bắt được 23 trường hợp cựu binh (như M2, M16, M24, M26...) trước đó chưa từng bị nhả bao giờ, nhưng sang ngày hôm sau chạy trên IP có vết nhả của ngày hôm trước thì bị "chết oan" ngay lượt đầu tiên.

---

## 2. Tử Huyệt "Account Switcher" Khi Đổi IP Nóng (Change IP Trap)

**Tình huống cân nhắc:** Khi 1 nick buổi sáng bị nhả, có nên đổi sang IP mới để các row buổi chiều/tối chạy tiếp không?
**Quy tắc vận hành:** **TUYỆT ĐỐI CẤM ĐỔI IP NÓNG ĐỂ CHẠY CỐ VÌ BẪY ACCOUNT SWITCHER.**

* **Cơ chế kỹ thuật:**
  1. Trên mỗi máy Samsung S7 quản lý 8 account (Row 1 đến Row 8) qua cơ chế Switch Account của TikTok app.
  2. Khi mở TikTok app lên, ứng dụng **luôn luôn restore và render phiên làm việc của nick cũ trước** (chính là nick vừa bị nhả buổi sáng) rồi mới hiển thị UI để bấm Switch sang nick Row sau.
  3. Nếu vừa đổi IP mới vào máy:
     - Khi mở app, nick cũ (đang mang án phạt) lập tức gửi packet ping về server TikTok trên IP mới toanh.
     - Server TikTok liên kết ngay lập tức: *"Tài khoản vi phạm vừa nhảy sang dải IP mới này"*.
     - Sau đó mới switch sang nick Row sau ➔ Nick Row sau ăn trọn cờ đỏ trên IP vừa bị làm bẩn.
  4. Hậu quả: Vừa làm bẩn thêm dải IP mới dự phòng (Proxy Burning Domino), vừa kéo chết nick hàng sau vì chung Hardware ID đã bị đưa vào diện giám sát.

---

## 3. Hiện Tượng "Chiều/Tối Dính Nhả": Phân Biệt Acc Yếu vs Lây Nhiễm IP

Khi phân tích các ca chiều/tối bị nhả trên cùng máy hoặc cùng IP:
* **88% – 94% các ca là do BẢN THÂN ACC QUÁ YẾU (Rookie / 0-follow):**
  - Dàn nick Row 1 & Row 2 là cựu binh (>90% có >= 10-25 video, trust cao).
  - Dàn nick Row 3–8 phần lớn là nick mầm (76% – 90% chưa từng có follow nào = 0 follow).
  - Đưa nick non vào cày follow thì ở bất kỳ ca nào/máy nào cũng sẽ bị TikTok chặn tương tác.
* **Chỉ 6% – 10% là lây nhiễm IP thực sự:**
  - Xảy ra khi một nick cựu binh khỏe chạy vào một IP vừa có máy partner hoặc row trước dính `FOLLOW_FAILED`.
* **Kỷ luật điều phối:**
  - CẤM cấp full budget (8–12 follow) cho Row 3–8 khi chưa đủ 15 video và chưa qua nấc dò đường 3–5 follow/ca.
  - Khi nick chiều tối dính nhả, phải kiểm tra ngay lịch sử follow và video count của nick đó trước khi kết luận lỗi do IP hay do máy.
  - Ngược lại, nếu sáng nick chạy sạch và chiều tối nick là acc có trust (như M16, M21 Row 3), máy và IP **hoàn toàn chạy được cả ca chiều tối sạch sẽ** (đã chứng minh qua dữ liệu thực tế).
