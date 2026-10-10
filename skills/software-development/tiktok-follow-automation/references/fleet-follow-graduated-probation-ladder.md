# Fleet Follow Graduated Probation Ladder & Health-Tiered Reporting

## 1. Bản Chất Kỹ Thuật: Cơ Chế Bậc Thang Thử Thách (Graduated Probation)

### Đơn vị vòng đời cốt lõi: (Máy, Row) là Account độc lập
- **CẤM TUYỆT ĐỐI GỘP QUOTA THEO MÁY:** Mỗi máy chạy nhiều ca (ví dụ ca sáng Row 1, ca chiều Row 2...). Mỗi `(máy, row)` là một nick độc lập có state, lịch sử và trust score riêng. Không bao giờ cộng dồn quota theo máy hoặc đặt trần ngày theo máy.

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

### Nhóm 2: Tân Binh & Nick Có Tiền Án (Bắt buộc đi qua lộ trình 3 nấc accelerated)
- **Quy tắc Tân Binh (USER INVARIANT):** Nick mới đủ Dual Gate (`age >= 21d`, `video >= 6`) nhưng chưa từng đi follow hoặc chưa tích lũy đủ follow an toàn (`< 15` follows, chưa có cờ `graduated`) đi dò với Quota 1–2 lượt. Bị nhả chỉ phạt cá nhân (tăng fail_streak, cooldown 3-14 ngày dưỡng sinh), **CẤM TUYỆT ĐỐI GIẬT CẦU DAO IP** (xem chi tiết `references/tier-aware-circuit-breaker-and-accelerated-probation.md`).
- **Quy tắc Nick Ra Tù:** Nick vừa hết hạn cooldown quay lại thử thách với Quota 1–2 lượt.

Áp dụng lộ trình 3 nấc thang tính theo số ngày chạy sạch (`probation_clean_days` - 2 ngày sạch / nấc):

* **HỒI PHỤC 1 (Probation Tier 1 - Tân binh khởi động & Nick mới ra tù, `clean_days < 2`):**
  - **Quota:** 1 – 2 follows / ca (đồng nhất cho cả tân binh và nick ra tù).
  - **Tiến độ thực tế:** Cần 2 ngày chạy sạch (~3 – 4 ngày ngoài đời thực).

* **HỒI PHỤC 2 (Probation Tier 2 - Tăng tải an toàn, `2 <= clean_days < 4`):**
  - **Quota:** 5 – 8 follows / ca.
  - **Tiến độ thực tế:** Cần thêm 2 ngày chạy sạch tiếp theo (~3 – 4 ngày ngoài đời thực).

* **NẤC 3 (Tốt nghiệp - Graduation, `clean_days >= 4`):**
  - Sau tổng cộng 4 ngày chạy sạch (~8 – 9 ngày ngoài đời thực).
  - Hệ thống chính thức tốt nghiệp (`graduated = True`, `fail_streak = 0`, xóa `probation_clean_days`), thăng hạng lên Nhóm Nick Khỏe (Full Budget 10 - 20 lượt).
  - **Cầu Dao IP:** CHỈ KHI NICK ĐÃ TỐT NGHIỆP NÀY BỊ NHẢ mới kích hoạt ngắt Cầu dao IP 48h.

* **CHỐT AN TOÀN FAIL-CLOSED & PROGRESSIVE BACKOFF STREAK:**
  - Nếu ở bất kỳ nấc nào (`Hồi phục 1` hay `Hồi phục 2`) mà bị TikTok nhả follow (`set_follow_failed()`) hoặc không follow được:
  - Lập tức xóa `probation_clean_days = 0`, tăng `fail_streak` (Streak 1 -> Streak 2 -> Streak 3+).
  - Đưa vào Cooldown theo Progressive Backoff:
    * `fail_streak = 1`: Giam 3 ngày (quota = 0).
    * `fail_streak = 2`: Giam 7 ngày (quota = 0).
    * `fail_streak >= 3`: Giam 15 ngày (quota = 0).
  - Khi mãn hạn Cooldown: Bắt buộc quay lại từ vạch xuất phát `Hồi phục 1` (1 - 2 lượt/ca). Nếu chạy sạch 2 ngày -> lên `Hồi phục 2` (5 - 8 lượt/ca) -> chạy sạch thêm 2 ngày -> tốt nghiệp lên `Khỏe` (10 - 20 lượt/ca). Nếu tại bất kỳ nấc nào bị nhả tiếp thì tiếp tục tăng `fail_streak` và quay lại Cooldown dài hơn.
  - **Chống bẫy thống kê Simpson:** Thống kê tỷ lệ giữ follow phải phân tầng độc lập (tỷ lệ của riêng Hồi phục 1, Hồi phục 2, Khỏe), CẤM gộp phẳng toàn farm khiến mức 15+ của nick Khỏe bị hiểu nhầm là an toàn nhất trong khi mức 1-4 của nick sau phạt bị kéo tụt tỷ lệ.

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

---

## 5. Đối Soát Số Liệu Dashboard: Phân Biệt "Đã Follow (Delta)" vs "🔗 Nội Bộ"

### A. Bản chất kỹ thuật của 2 chỉ số:
- **`ĐÃ FOLLOW: X (+Y)` (`delta_following`):**
  - Số liệu thực tế cào từ profile công khai TikTok qua snapshot mới nhất.
  - Hiệu số `+Y` phản ánh **tổng biến động thực tế** của following trên TikTok giữa 2 lần quét: `delta_following = following_hien_tai - following_snapshot_truoc`.
  - Bao gồm TẤT CẢ các hành vi follow: follow chéo nội bộ, follow tự nhiên khi lướt feed, follow kênh idol / kênh niche theo kịch bản nuôi.
- **`🔗 Nội bộ: +Z` (`internal_followed`):**
  - Số liệu telemetry ghi nhận từ các script kịch bản (`feed_session_watchdog` / `run_follow`) được lưu vào bảng `session_account_actions` và tổng hợp ở `daily_account_actions` trong `tiktok_tracker.db`.
  - Chỉ đếm các lượt **follow chéo giữa các tài khoản nội bộ farm** theo `target_date = max_dt`.

### B. Giải mã hiện tượng Following tăng (+12, +2...) nhưng "🔗 Nội bộ: +0":
1. **Follow tự nhiên ngoài luồng chéo (Natural / Niche Follows):**
   - Khi chạy ca lướt nuôi nick (`feed_session`), kịch bản bấm follow các video/kênh hot hoặc tài khoản gợi ý bên ngoài để tăng trust account và định hình niche.
   - Các lượt này làm tăng số Following trên TikTok (`delta_following` dương), nhưng không thuộc danh sách đối soát follow chéo chùm nick nội bộ farm.
2. **Lệch mốc thời gian / Chưa có phiên chéo trong ngày:**
   - Dashboard lấy `internal_follows` theo ngày của snapshot mới nhất (`target_date = max_dt`).
   - Nếu ngày đó mới chỉ chạy ca lướt đêm/sáng sớm (`internal_follows = 0`), hoặc nick không thuộc danh sách phân bổ chạy follow chéo của ngày (ví dụ ca follow chia theo ngày chẵn/lẻ hoặc chỉ phân bổ cho 1 nhóm máy nhất định), hệ thống trả về giá trị mặc định `+0`.
   - Kết luận: Khi thấy Following tăng mà Nội bộ +0, tài khoản hoàn toàn khỏe mạnh và đang tăng follow tự nhiên ngoài luồng chéo, không phải lỗi hệ thống hay nhả follow.
