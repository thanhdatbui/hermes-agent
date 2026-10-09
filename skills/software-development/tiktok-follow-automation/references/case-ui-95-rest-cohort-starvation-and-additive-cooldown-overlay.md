# Case UI-95: Chống Bẫy Đói Dưỡng Sinh (Rest Cohort Starvation Trap) & Nguyên Tắc Lớp Phủ Cooldown Bổ Sung (Additive Overlay)

## 1. Hiện Tượng & Khúc Mắc Nghiệp Vụ (2026-10-05)
- **Ý tưởng ban đầu:**
  Khi chạy ca nuôi, lọc bỏ toàn bộ các nick đang bị phạt do nhả follow ("đi tù" / cooldown 3-5-7 ngày) ra khỏi danh sách, sau đó mới chọn 33% số nick khỏe mạnh còn lại để đưa vào chế độ dưỡng sinh tự nhiên (`organic-rest-day`), số còn lại mới mang đi follow chéo.
- **Bẫy kiến trúc (Starvation Pitfall — User chỉ đạo):**
  - Giả sử trong một hàng (row) hoặc toàn fleet, số lượng nick bị TikTok phạt nhả follow tăng cao (ví dụ >= 33% hoặc 40-50% tổng số nick).
  - Nếu lọc bỏ nhóm nick bị phạt rồi mới bốc tiếp 33% nick khỏe mạnh để dưỡng sinh, thì số lượng nick khỏe còn lại liên tục bị co hẹp.
  - Hậu quả nghiêm trọng: **Các nick khỏe mạnh sẽ bị ép vào vòng lặp chạy follow liên tục mỗi ca mà không bao giờ đến lượt được nghỉ dưỡng sinh**, dẫn tới việc đàn nick khỏe bị vắt kiệt, tăng rủi ro bị TikTok đánh gậy hàng loạt.

## 2. Invariant Quy Hoạch: Tách Biệt Độc Lập Giữa Dưỡng Sinh & Cooldown
CẤM TUYỆT ĐỐI điều chỉnh, rebalance hoặc bốc lại tỷ lệ 33% dưỡng sinh dựa trên số lượng nick đang bị phạt.

### A. Lịch Dưỡng Sinh Tự Nhiên (Deterministic Organic Rest):
- Băm MD5 cố định trên **TOÀN BỘ DANH SÁCH MÁY/ROW GỐC (Full Roster)**:
  `hashlib.md5(f"{date_str}:{machine}:{row}".encode("utf-8")).hexdigest() % 3 == 0`
- Tỷ lệ ~33% được phân bổ đều đặn và hoàn toàn khách quan.
- Dù nick có đang bị cooldown hay không, lịch dưỡng sinh tự nhiên của nó theo ngày vẫn giữ nguyên, bảo đảm mọi nick đều có chu kỳ nghỉ ngơi tự nhiên theo toán học cố định.

### B. Cooldown Nhả Follow Là Lớp Phủ Bổ Sung (Additive Overlay Only):
- Cooldown chỉ đóng vai trò là **lớp cấm hành vi (Action Gate / Suppression Overlay)**:
  1. **Khi nick bị nhả follow:** Ghi nhận `cooldown_until_at` vào `follow_state_<machine>_row_<row>.json`.
  2. **Khi lướt Feed:** Khóa `_follow_rate = 0` (tắt 100% follow tự nhiên trên feed để tránh ghost follow / shadow drop).
  3. **Khi đến Hook Follow Chéo:** Bỏ qua sớm với lý do `follow-released-daily-cooldown` (không khởi động subprocess follow).
- Cooldown KHÔNG LÀM THAY ĐỔI hay dời lịch dưỡng sinh của bất kỳ nick nào khác trên farm.

## 3. Checklist Phối Hợp Đạt Chuẩn (Anti-Insanity Coordination)
1. **Roster Integrity:** Không lọc danh sách đầu vào trước khi xác định cờ dưỡng sinh.
2. **Dual Suppression:** Nick đang dính án nhả follow bắt buộc phải tắt cả Follow Tự Nhiên trên Feed lẫn Follow Chéo sau phiên.
3. **No Starvation:** Không dồn chỉ tiêu follow của nick bị phạt sang nick khỏe mạnh trong cùng ca.
