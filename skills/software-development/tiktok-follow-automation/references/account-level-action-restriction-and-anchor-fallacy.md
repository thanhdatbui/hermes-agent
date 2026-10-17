# Phân Tích Hiện Tượng Nhả Follow Cấp Tài Khoản vs Kịch Bản Anchor

## 1. Bản chất: Action Restriction ở Cấp Tài Khoản (Account-Level Restriction)

- **Hiện tượng:**
  Khi một tài khoản TikTok bị máy chủ hạn chế tính năng Follow (Action Block / Silent Drop):
  - Bấm nút Follow tài khoản Anchor: Nhả.
  - Bấm tài khoản con trong danh sách Following: Nhả.
  - Bấm tài khoản ngẫu nhiên ngoài For You Feed: Nhả.
  - Bấm bằng tay trực tiếp trên điện thoại: Vẫn nhả (sau 1-2s icon đổi lại trạng thái chưa follow).

- **Sai lầm nhận thức:**
  Nghĩ rằng "Anchor có following lớn nên bị nhả, nếu bỏ qua Anchor nhảy thẳng vào danh sách con thì sẽ follow được". Đây là nhận thức hoàn toàn sai về cơ chế an ninh mạng của TikTok. Anchor chẳng qua là mục tiêu đầu tiên kịch bản chạm vào nên bị nhả đầu tiên; nếu né Anchor bấm mục tiêu khác thì mục tiêu đó cũng bị nhả ngay lập tức ở phát bấm đầu tiên (bằng chứng từ máy M27, M42 ngày 16/10/2026).

---

## 2. Nguyên tắc Thiết kế & Kỷ luật Điều hành

1. **CẤM VIẾT CODE NÉ ANCHOR DỰA TRÊN QUY MÔ NICK:**
   - Tuyệt đối không tạo logic "Rookie cohort skip anchor follow" hay né tránh tài khoản Anchor lớn. Kịch bản Mode 2 giữ nguyên luồng chuẩn người dùng tự nhiên cho mọi tài khoản:
     `Vào Profile Anchor -> Xem video + Like -> Follow Anchor -> Mở danh sách Following -> Follow nick con`.

2. **ĐIỀU KIỆN TIÊN QUYẾT: CHƯA ĐỦ KHỎE THÌ CẤM CÀY FOLLOW:**
   - Nick bị nhả follow là do tài khoản **chưa đủ trust / chưa đủ độ ấm (cold account) hoặc đang bị phạt**:
     - Nick có `Following < 10` hoặc `Tuổi < 30 ngày` hoặc `Video < 10`: CẤM cày follow chéo.
     - Cấp `session_budget = 0 ("blocked")`.
     - Chỉ cho phép chạy chế độ **Dưỡng sinh thuần (Feed Session)**: Lướt FYP, xem video đủ dwell time, thả tim tự nhiên để mở trust trước.
   - Khi nick đã đủ khỏe và đủ trust, mới cho phép vào ca chạy Follow theo đúng khung Quota của Cohort.

3. **PHÂN ĐỊNH OBSERVABILITY (BÁO CÁO TELEGRAM vs DATABASE/DASHBOARD):**
   - **Telegram:** Giữ vai trò Tháp điều khiển (Control Tower), chỉ báo KPI cấp cao và liệt kê danh sách các máy bất thường (dính nhả, mất mạng, máy lệch). Tuyệt đối không biến Telegram thành database xả chi tiết từng UID con làm loãng và trôi tin nhắn.
   - **SQLite & Dashboard (:1905):** Lưu trữ toàn bộ dữ liệu chi tiết sâu (Forensics), từng UID con kèm timestamp, lịch sử thăng tiến trần quota (`proven_safe_ceiling`, `active_ceiling`, `last_failed_ceiling`) để mở ra tra cứu khi cần.

---

## 4. Đặc Tả Endpoint & Thiết Kế Giao Diện Sổ Tay Bệnh Án (Follow Forensics trên Dashboard 1905)

### A. API Endpoint
Khi Operator cần kiểm tra sâu về từng nick trên Dashboard (không phải chỉ xem biểu đồ tăng trưởng số lượng follower/tim):
- **API Endpoint:** `/api/follow-detail?machine=<M>&row=<R>`
  - Đọc trực tiếp từ file state `runs/state/follow_state_<M>_row_<R>.json` (hoặc `follow_state_<M>.json` nếu row 1).
  - Trả về JSON có cấu trúc:
    ```json
    {
      "machine": 10,
      "row": 1,
      "username": "hadang0725",
      "cohort": "mid",
      "proven_safe_ceiling": 20,
      "active_ceiling": 22,
      "last_failed_ceiling": "-",
      "fail_streak": 0,
      "probation_clean_days": 2,
      "graduated": true,
      "follow_failed": false,
      "cooldown_until_date": "-",
      "total_followed": 93,
      "followed_list": [
        {"uid": "tooanh2604", "timestamp": "2026-09-03T02:53:52+00:00"}
      ]
    }
    ```

### B. Kỷ Luật UX Giao Diện (Chống Ép Popup Nhỏ Gây Khó Đọc)
- **Anti-Pattern (BỊ CẤM TUYỆT ĐỐI):** Nhét thông số bệnh án, thẻ trần quota và bảng lịch sử UID vào modal popup nhỏ hẹp (`max-width: 680px`, khung cuộn mini 300px). Người vận hành phải nheo mắt đọc chữ nhỏ, thao tác cuộn bí bách ("làm nhỏ khó đọc vc").
- **Chuẩn Thiết Kế Dedicated View / Master-Detail (Bắt Buộc):**
  1. **Phân nhóm sức khỏe trực quan & Đưa Nick Yếu Lên Đầu:** BẮT BUỘC nhóm danh sách tài khoản theo các phân tầng rõ rệt kèm số lượng đếm tức thì:
     - 🔴 **Yếu / Vào Tù (Cooldown):** Ưu tiên xếp lên đầu danh sách để can thiệp kịp thời (hiển thị rõ fail streak, lý do dính nhả, ngày mãn hạn).
     - 🟠 **Hồi Phục 1 (Probation T1):** Dò bậc thang 3-5 lượt/ca.
     - 🟡 **Hồi Phục 2 (Probation T2):** Dò bậc thang 7-9 lượt/ca.
     - 🟢 **Khỏe Mạnh / Nòng Cốt (Full Quota):** Đã tốt nghiệp, chạy full quota theo cohort.
  2. **Bố cục Master-Detail Thoáng Đạt (Toàn Màn Hình):**
     - **Cột Trái (Danh Sách Tài Khoản - ~350px):** Cuộn dọc danh sách thẻ nick. Mỗi thẻ hiển thị: Máy, Row, Cổng proxy (🔗 đối tác cùng IP), Username, huy hiệu sức khỏe màu sắc, tổng follow, max safe. Bấm vào thẻ thì viền sáng neon và nạp ngay sang Cột Phải.
     - **Cột Phải (Sổ Bệnh Án Chi Tiết - Full Width):**
       + Header nick: `@username` (link mở TikTok) • Máy X • Row Y.
       + 4 Thẻ Quota lớn: Nhóm Cohort (`Veteran / Mid / Rookie`), Trần Đã Chứng Minh (`proven_safe_ceiling`), Trần Dò Ca Tới (`active_ceiling`), Mức Gãy Gần Nhất (`last_failed_ceiling`).
       + Banner kỷ luật: Lộ trình (`⚡ Ưu tiên / Fast Track` hay `🎯 Tiêu chuẩn / Cautious`), số ca sạch tích lũy, thời hạn cooldown.
       + Bảng Lịch Sử UID Đã Follow: Rộng rãi, chữ to rõ ràng, link mở profile TikTok `@uid`, ngày giờ chi tiết đến giây và ô lọc nhanh UID con.
  3. **Tương Thích Mobile (<= 768px):** Không ép 2 cột co cụm trên điện thoại. Hiển thị danh sách nick full-width; khi chạm vào 1 nick thì chuyển sang màn chi tiết toàn màn hình kèm nút `← Quay lại danh sách nick`.
  4. **Liên Kết Giữa Các Tab (Cross-View Navigation):** Bấm nút kính lúp / sổ tay (`🔍` / `📋`) tại bất kỳ tab nào (Toàn Bộ Farm, BXH Following, Sức Khỏe Máy) phải tự động chuyển ngay sang Tab Bệnh Án và chọn đúng nick đó, không bật modal popup che màn hình.
