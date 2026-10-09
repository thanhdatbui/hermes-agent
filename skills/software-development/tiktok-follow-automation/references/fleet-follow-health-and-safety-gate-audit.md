# Quy Trình Kiểm Tra & Báo Cáo Sức Khỏe Follow Chéo Toàn Farm (Fleet Follow Health & Safety Gate Audit)

> **Mục đích:** Quy trình chuẩn giúp Coordinator/Worker kiểm tra, đối soát và báo cáo tình hình chạy Follow Chéo trên đàn máy Farm (80 máy Kibe, 80 máy Admin) một cách nhanh chóng, chuẩn xác O(1), không quét đĩa diện rộng, và phân loại chính xác các tầng bảo vệ an toàn.

---

## 1. Bản Đồ 4 Tầng Bảo Vệ Của Hệ Thống Follow Chéo

Khi kiểm tra tình hình follow chéo của bất kỳ ca/phiên nào, BẮT BUỘC phân biệt rõ 4 trạng thái máy:

| Tầng / Trạng thái | Mã định danh trong log (`follow_result.json` / `follow_state.json`) | Ý nghĩa nghiệp vụ | Đánh giá an toàn |
| :--- | :--- | :--- | :--- |
| **1. Thành công** | `status: "success"`, `followed_count > 0` | Nick đã tìm kiếm (M1) hoặc vào follower của Anchor (M2) và bấm follow thành công. Trải qua Path B / verify profile không bị nhả. | ✅ Nick khỏe, trust score tốt, đang tích lũy follow đều. |
| **2. Bị nhả (Action Block / Drop)** | `status: "FOLLOW_FAILED"`, `reason: "FOLLOW_FAILED: ... bị nhả ..."` | Server TikTok âm thầm nhả nút follow (hoặc nhả nick Anchor). Hệ thống kích hoạt **Fail-Closed dừng phiên ngay lập tức** và đẩy nick vào **Progressive Cooldown** (Lần 1: 3 ngày, Lần 2: 5 ngày, Lần 3: 7 ngày). | 🛑 Cơ chế an toàn hoạt động đúng: Không bấm cố để tránh chết nick. Phiên sau trong ngày sẽ tự động skip với `follow-released-daily-cooldown`. |
| **3. Bỏ qua an toàn (Safe Skip)** | • `under-30-days-follow-disabled`<br>• `under-10-videos-follow-disabled`<br>• `follow-released-daily-cooldown`<br>• Organic Rest (`fl_rest` ~33%) | • **Dual Gate (Cập nhật 2026-10-06):** Nick < 30 ngày tuổi hoặc < 10 clip trên kênh bị chặn cứng (`budget = 0`), tuyệt đối không chạy follow để chống silent drop.<br>• **Daily Cooldown:** Nick đã bị nhả ở phiên trước, phiên này tự động nghỉ.<br>• **Dưỡng sinh:** ~1/3 đàn máy ngẫu nhiên nghỉ follow mỗi phiên. | 🛡️ **BẢO VỆ NICK THEO THIẾT KẾ:** Tuyệt đối KHÔNG ĐƯỢC báo là lỗi script hay lỗi hệ thống! |
| **4. Lỗi script / Hạ tầng** | • `preflight device-lock/VPN fail-closed`<br>• `device offline or ADB/USB disconnected`<br>• `follow-timeout` | Mất kết nối USB ADB, rớt mạng VPN/tun0, hoặc runner bị kẹt quá thời gian timeout quy định. | ⚠️ Lỗi cần xử lý kỹ thuật: kiểm tra dây cáp, cổng USB, gán proxy hoặc khởi động lại adb server. |

---

## 2. Quy Trình Trích Xuất Hiện Trường O(1) Không Quét Đĩa

CẤM TUYỆT ĐỐI dùng `find`, `os.walk`, `glob(recursive=True)` để tìm kiếm log follow trên diện rộng ổ đĩa `D:/Taadaa`.

### Các vị trí đọc dữ liệu chuẩn hóa:
1. **State máy & Cooldown:**
   - Đường dẫn: `D:/Taadaa/tiktok-follow/runs/state/follow_state_<machine>_row_<row>.json`
   - Chỉ số cần đọc:
     * `last_budget_decision`: `{budget, video_count, account_age_days, mode}`
     * `follow_failed`: `true/false`
     * `cooldown_until_date`: ngày hết hạn cooldown (ví dụ: `2026-10-06`)
     * `last_failed_at`: thời điểm bị nhả gần nhất.

2. **Kết quả phiên của từng máy tại runtime:**
   - Đường dẫn: `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/<row_session>/<run_timestamp>/machines/machine_<machine>/<run_timestamp>/follow_result.json`
   - Chỉ số cần đọc:
     * `status`: `success` | `FOLLOW_FAILED` | `skipped`
     * `reason`: nguyên nhân cụ thể (ví dụ: `under-21-days-follow-disabled`, `anchor @... bị nhả sau vuốt`)
     * `followed_count`: số lượt bấm được trước khi dừng.

3. **Lịch sử tổng hợp các ca đã chốt:**
   - Database: `D:/Taadaa/data/tiktok_tracker.db`
   - Bảng `session_action_stats`: Thống kê tổng hợp số lượt follow nội bộ (`internal_fl`), follow tự nhiên (`natural_fl`), tim (`likes`), lượt lướt (`swipes`) theo từng `session_key`.
   - Bảng `daily_account_actions`: Tổng lượt follow nội bộ của từng tài khoản trong ngày.

---

## 3. Cấu Trúc Báo Cáo Chuẩn Khi User Yêu Cầu Kiểm Tra

Báo cáo cho User hoặc Farm Operator phải tuân thủ nghiêm ngặt kỷ luật truyền thông:
- **CẤM dùng từ "Lũy kế"** (gây hiểu nhầm cộng dồn nhiều ngày hoặc nhiều hàng nick).
- **Phân tách rành mạch theo từng Ca / Hàng Nick (Row 1 đến Row 8):**
  1. **Tổng quan bảng kết quả:** Ca chạy, số lượt follow, số máy nhả, trạng thái an toàn.
  2. **Bóc tách hiện trường 3 nhóm tài khoản:**
     - *Nhóm nick già (Row 1-2):* Tỷ lệ thành công và các máy chủ lực kéo follow.
     - *Nhóm nick tầm trung (Row 3-6):* Tình hình siết nhả của TikTok, số máy bị nhả, cơ chế dừng session và thang Cooldown 3 ngày bảo vệ nick.
     - *Nhóm nick non (Row 7-8):* Bảo vệ tuyệt đối qua Dual Gate (`age >= 30d` & `video >= 10`), các lý do skip an toàn.
  3. **Kết luận & Đề xuất hành động:** Giữ vững kỷ luật an toàn, tôn trọng thời gian nghỉ dưỡng sinh và cooldown của nick, không cố ép tăng budget khi server TikTok đang siết.

---

## 4. Hiện Tượng Lệch Danh Hiệu "Nick Khỏe" Trên Dashboard vs Thực Tế Không Follow (Dual Gate vs Health Tier)

### A. Nick Hiện "🟢 Khỏe" Trên Dashboard Nhưng Không Bao Giờ Thấy Đi Follow (`budget = 0`):
- **Cơ chế phân tầng Dashboard (`follow_health_helper.py`):**
  * Dashboard chỉ phân loại trạng thái kỷ luật/tiền án dựa trên `fail_streak` và `cooldown_until_date` trong `follow_state_*.json`.
  * Nếu nick **chưa từng bị TikTok phạt gậy nhả follow** (`fail_streak == 0`), Dashboard tự động gắn nhãn **`🟢 Khỏe` (Full Quota)**.
- **Cơ chế chặn cứng Dual Gate của Runner (`follow_state.py`):**
  * Runner yêu cầu bắt buộc: `account_age_days >= 30` VÀ `video_count >= 10`.
  * Nếu nick có `video_count < 10` (ví dụ: mới có 5–7 video) hoặc `account_age_days < 30`, runner trả về **`budget = 0` (bị chặn hoàn toàn)**.
  * **Hệ quả đối soát:** Nick "sạch án tích" nên được Dashboard ghi nhận là Khỏe, nhưng thực chất chưa đủ điều kiện mở khóa hành động. Cần đăng đủ $\ge 10$ video để nick thực sự bắt đầu chạy follow.

### B. Lệch Giữa Số Đếm Profile (Following Count) Và Danh Sách Thực Tế:
- **Cache tĩnh của TikTok:** Số hiển thị ngoài Profile (ví dụ: `2` Đã follow) là số đếm cached từ database TikTok.
- **Lọc Real-time trong danh sách:** Khi người dùng mở chi tiết danh sách Đang Follow, server TikTok truy vấn real-time và tự động ẩn/loại bỏ các tài khoản đã bị khóa, xóa hoặc đình chỉ. Do đó số tài khoản hiển thị trong danh sách có thể ít hơn số đếm ngoài profile (ví dụ hiển thị 1 thay vì 2).
- **Silent Drop:** Nick chưa đủ 10 video khi cố follow nick khác thường bị TikTok silent-drop ngay lập tức, số follow trên profile không tăng.
