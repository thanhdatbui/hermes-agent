# Fleet Follow Graduated Probation Ladder & Health-Tiered Reporting

## 1. Bản Chất Kỹ Thuật: Cơ Chế Bậc Thang Thử Thách (Graduated Probation)

### Tại sao nick ra tù hay bị dính nhả lại?
1. **Lỗi spike quota ngay sau khi ra tù:**
   - Khi hết hạn cooldown, tài khoản ra tù vẫn đang nằm trong danh sách giám sát (probation) của TikTok server.
   - Nếu vừa chạy xong 1 phiên nhẹ (3-5 lượt) mà hệ thống xóa ngay `fail_streak = 0` thì phiên kế tiếp trong ngày hoặc ngày hôm sau sẽ cấp ngay Full Budget (10-20 lượt/phiên, tức 20-30+ lượt/ngày).
   - TikTok server phát hiện đột biến follow từ nick vừa ra tù -> Đập gậy trừng phạt và tăng mức phạt lên các streak cao hơn (3, 5, 7, 15 ngày).
2. **Ngưỡng tải thực tế (Trust Ceiling):**
   - Mức **1 - 3 follow/ngày:** Dành cho nick vừa dứt cữ phạt (ra tù).
   - Mức **7 - 10 follow/ngày:** Vùng an toàn cao nhất (~90% an toàn theo số liệu thực tế farm).
   - Mức **12 - 15+ follow/ngày:** Bắt đầu chạm ngưỡng đỏ của TikTok đối với các nick chưa tích lũy đủ trust. Chỉ nhóm nick nòng cốt (>215 ngày, >25 video, có tương tác tự nhiên) mới chịu được mức này an toàn.

---

## 2. Quy Chuẩn 3 Nấc Thang Thử Thách (Graduated Probation Ladder)

### Nhóm 1: Nick Khỏe / Nòng Cốt (Đã tốt nghiệp: `>= 15` follows an toàn HOẶC `graduated == True`, `fail_streak == 0`)
- Giữ nguyên 100% budget hiện tại: 10 - 20 follows/phiên (theo config máy).
- Tuyệt đối không tự ý hạ trần vô lý của nhóm này làm giảm hiệu suất chung của farm.

### Nhóm 2: Tân Binh & Nick Có Tiền Án (Bắt buộc đi qua lộ trình 3 nấc)
- **Quy tắc Tân Binh (USER INVARIANT):** Nick mới đủ Dual Gate (`age >= 30d`, `video >= 10`) nhưng chưa từng đi follow hoặc chưa tích lũy đủ follow an toàn (`< 15` follows, chưa có cờ `graduated`) **CẤM TUYỆT ĐỐI nhảy cóc lên Full Quota**. Tân binh bắt buộc phải đi từ `Hồi phục 1` -> `Hồi phục 2` rồi mới được thăng hạng lên Full Quota.
- **Quy tắc Nick Ra Tù:** Nick vừa hết hạn cooldown quay lại thử thách.

Áp dụng lộ trình 3 nấc thang tính theo số ngày chạy sạch (`probation_clean_days`):

* **HỒI PHỤC 1 (Probation Tier 1 - Tân binh khởi động & Nick mới ra tù, `clean_days < 3`):**
  - **Đặt tên chuẩn ngắn gọn:** Gọi là `Hồi phục 1` (tránh đặt dài dòng như `Nấc 1 Thử Thách` gây chật chội trên mobile và Telegram).
  - **Quota:** 3 – 5 follows / ngày.
  - **Tiến độ thực tế:** Cần 3 ngày chạy sạch. Do lịch chạy đảo Parity (chẵn/lẻ) và tỷ lệ dưỡng sinh (1/3), trung bình mỗi nick chạy 1 lần/2.3 ngày. Do đó, Hồi phục 1 kéo dài **~7 ngày (1 tuần)** ngoài đời thực.

* **HỒI PHỤC 2 (Probation Tier 2 - Tăng tải an toàn, `3 <= clean_days < 6`):**
  - **Đặt tên chuẩn ngắn gọn:** Gọi là `Hồi phục 2` (ngắn gọn, trực quan, thay vì `Nấc 2 Thử Thách`).
  - **Quota:** 7 – 9 follows / ngày (vùng an toàn 90%).
  - **Tiến độ thực tế:** Cần thêm 3 ngày chạy sạch tiếp theo mà không bị phạt -> Kéo dài thêm **~7 ngày (thêm 1 tuần)** ngoài đời thực.

* **NẤC 3 (Tốt nghiệp - Graduation, `clean_days >= 6`):**
  - Sau tổng cộng 6 ngày chạy sạch (~14 - 15 ngày, tức nửa tháng dưỡng acc liên tục).
  - Hệ thống chính thức tốt nghiệp (`graduated = True`, `fail_streak = 0`, xóa `probation_clean_days`), thăng hạng lên Nhóm Nick Khỏe (Full Budget 10 - 20 lượt).

* **CHỐT AN TOÀN FAIL-CLOSED:**
  - Nếu ở bất kỳ nấc nào (`Hồi phục 1` hay `Hồi phục 2`) mà bị TikTok nhả follow (`set_follow_failed()`):
  - Lập tức xóa `probation_clean_days = 0`, tăng `fail_streak`, đưa vào cooldown theo progressive backoff.
  - Khi ra tù, bắt buộc quay lại từ vạch xuất phát `Hồi phục 1`.

---

## 3. Quy Chuẩn Đồng Bộ Múi Giờ & Báo Cáo Sức Khỏe (Health-Tiered Reporting)

### A. Bắt buộc đồng bộ múi giờ Việt Nam (GMT+7 / Asia/Ho_Chi_Minh):
- Timestamp trong file state JSON lưu dạng ISO UTC (`...Z` hoặc `+00:00`).
- Mọi thống kê, phân nhóm ngày, so sánh lịch chẵn/lẻ **BẮT BUỘC PHẢI convert sang Asia/Ho_Chi_Minh** trước khi tính toán.
- Tuyệt đối cấm lấy substring `ts[:10]` trực tiếp từ chuỗi UTC, tránh nhầm lẫn tai hại (ví dụ 06:30 sáng VN ngày 3 bị đọc nhầm thành 23:30 đêm ngày 2).

### B. Format báo cáo sức khỏe follow theo tầng (Ghi range lượt nhóm, %, và Danh Sách Máy trong ngoặc):
- **QUY TẮC CỐT LÕI (USER CORRECTION):**
  - Trong báo cáo Telegram theo nhóm, **BẮT BUỘC ghi rõ range lượt của nhóm** (ví dụ `(10+ lượt)`, `(5 - 9 lượt)`, `(1 - 4 lượt)`, `(0 lượt)`) kèm **tỷ lệ %** và **danh sách máy đặt trong ngoặc đơn `(M1, M2...)`**.
  - **TUYỆT ĐỐI CẤM ghi chi tiết số lượt của từng máy riêng lẻ `(M1 (4 lượt), M2 (17 lượt))`** gây rườm rà, rối mắt.
- **Cấu trúc chuẩn:**
  ```markdown
  • Follow chéo (35 lượt follow) [Module 2 (Anchor): 28 | Module 1 (Bù): 7]:
    + Thành công (7 máy | 70.0%):
      💪 Nhóm Khỏe (10+ lượt | 28.6%): (M2, M39)
      🌱 Hồi phục 2 (5 - 9 lượt | 28.6%): (M18, M28)
      🌱 Hồi phục 1 (1 - 4 lượt | 42.8%): (M1, M52, M16)
    + Nhả follow (3 máy | 30.0%):
      - Nhả liền (0 lượt | 66.7%): (M26, M32)
      - Nhả ở Hồi phục 1 (1 - 4 lượt | 33.3%): (M4)
  ```

---

## 4. Tích Hợp Web Dashboard (`D:/Taadaa/tools/tiktok_dashboard.py` :1905)
- **Module tính toán:** `D:/Taadaa/tools/follow_health_helper.py` trích xuất nhanh O(1) từ 411 file `runs/state/follow_state_*.json` và database `tiktok_tracker.db` (`daily_account_actions`).
- **Endpoint API:** `/api/follow-health` cung cấp cấu trúc JSON gồm:
  - `summary`: Tổng nick theo dõi, số lượng & tỷ lệ % cho 4 tầng (Khỏe, Nấc 2, Nấc 1, Cooldown kèm phân tách Streak 1 / Streak 2-3 / Streak 4+).
  - `weekly_stats` & `daily_stats`: Thống kê tổng lượt follow và số nick hoạt động theo từng tuần / ngày.
  - `accounts` & `grouped`: Danh sách chi tiết ánh xạ Máy, Row, Username, Tier, số ngày sạch, và ngày hết hạn Cooldown, kèm theo phân nhóm sẵn theo từng danh mục.
- **Quy tắc hiển thị Dashboard (Chống đổ tràng dài 400 dòng trên mobile & Tối ưu UI/UX tương tác):**
  - **CẤM TUYỆT ĐỐI render bảng cuộn 400 dòng lẫn lộn một tràng từ trên xuống dưới:** Khiến trên điện thoại bung thành hàng trăm card dọc dài vô tận, không thể nắm bắt được tình hình.
  - **Dùng 4 thẻ KPI lớn làm nút chọn nhóm chính (Interactive KPI Filter Cards — thay thế hàng nút dư thừa):**
    * 4 thẻ KPI trên cùng (`💪 Khỏe`, `🌱 Hồi phục 1`, `🌱 Hồi phục 2`, `⚠️ Đang Cooldown`) là các thẻ bấm được (`.fleet-kpi.clickable`).
    * BẮT BUỘC hiển thị cả **số lượng máy + tỷ lệ %** ngay trong thẻ: ví dụ `20 máy (4.9%)`, `29 máy (7.1%)`.
    * **Hiệu ứng bấm thẻ trực quan (Micro-interaction & Active Feedback):**
      - Thẻ KPI khi hover/click phải có hiệu ứng tương tác như các thẻ KPI khác (`:hover { transform: translateY(-3px); box-shadow: ... }`, `:active { transform: translateY(-1px); }`).
      - Thẻ được chọn BẮT BUỘC có class `.active` với background gradient highlight, viền rực màu neon accent, và hiệu ứng chấm tròn active (`::after`) để người dùng nhận biết ngay thẻ nào đang kích hoạt.
    * **CẤM tạo thêm hàng nút chọn nhóm lặp lại ở phía dưới (loại bỏ redundancy):** Khi 4 thẻ KPI đã có đủ chức năng và số liệu, việc tạo thêm một hàng nút chọn nhóm phía dưới là dư thừa và làm rối mắt. Xóa bỏ hàng nút dưới, chỉ giữ lại thanh tìm kiếm `🔍 Tìm máy hoặc username...` và tiêu đề danh sách rõ ràng.
    * Bấm vào thẻ KPI nào là lập tức kích hoạt lọc và **tự động cuộn mượt (`scrollIntoView`)** xuống thẳng danh sách máy của nhóm đó, không bắt người dùng phải kéo tay tìm kiếm.
    * Có highlight trực quan (`.active`) trên thẻ KPI đang được chọn.
  - Mặc định khi mở tab phải chọn ngay nhóm **`[💪 Khỏe]`** để hiển thị ngay dàn nick nòng cốt sạch đẹp.
  - Hiển thị danh sách dạng **Lưới thẻ gọn gàng (Compact Cards Grid)**: Mỗi thẻ ghi rõ Máy & Row (`M1 (Row 1)`), `@username`, Trạng thái sức khỏe, và Hạn ra tù / Ngày sạch.
  - **Link trực tiếp đến profile TikTok (USER INVARIANT):** Trên mỗi thẻ nick, `@username` BẮT BUỘC phải là link `<a>` (`href="https://www.tiktok.com/@username" target="_blank"`) kèm icon `↗` và `📈` để người dùng chạm vào là bung ngay ra trang cá nhân của nick đó trên TikTok, giống như ngoài Dashboard chính. Tuyệt đối cấm để username dạng text tĩnh không click được.
  - Tích hợp ô tìm kiếm nhanh (theo số máy `m1`, `18` hoặc `username`).
  - **Deduplication:** Tự động lọc bỏ các file state legacy không có `_row_` (như `follow_state_1.json`) để không bị duplicate dòng hiển thị trên Dashboard.
