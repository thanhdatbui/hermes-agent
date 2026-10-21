# Follow Cycle Audit, Jail Classification, and IP Breaker Invariants

## 1. Định nghĩa chuẩn xác: Tù Nặng vs Cooldown (User Correction Invariant)

- **🔴 Tù nặng (fl=0 liên tiếp streak ≥ 2):**
  - Chỉ tính những nick tham gia ca chạy trong chu kỳ nhưng **hoàn toàn không follow được lượt nào (`follows == 0`) VÀ đã có án tích tích lũy liên tiếp (`fail_streak >= 2`)**.
  - Đây là nhóm tài khoản bị TikTok gắn cờ hạn chế hành vi (Action Blocked) kinh niên, cần thời gian cooldown dài hoặc quy trình nuôi dưỡng/phục hồi đặc biệt.
- **🟡 Cooldown (fl=0, streak = 1):**
  - Là những nick tham gia ca nhưng bị nhả ngay phát đầu (`follows == 0`), tuy nhiên **mới chỉ vấp lần đầu trong kỳ hiện tại (`fail_streak <= 1`)**.
  - Đây là hiện tượng vấp phiên bình thường, chỉ cần nghỉ cooldown ngắn 1-3 ngày để xả cache/reset phiên.
- **CẤM TUYỆT ĐỐI GỘP CHUNG:**
  - Tuyệt đối cấm gộp 2 nhóm này thành các nhãn lai căng như "Số nick tù nặng / non bị nhả ngay lần đầu".
  - Việc gộp chung làm sai lệch bản chất số liệu (ví dụ 213 nick fl=0 thực chất chỉ có 95 nick tù nặng và 118 nick cooldown thông thường), khiến người vận hành đánh giá sai mức độ tê liệt của farm.
  - Trên Dashboard (`follow_detail_component.py`) và mọi báo cáo bắt buộc tách thành 2 chỉ số độc lập:
    1. `🔴 Tù nặng (fl=0 liên tiếp streak ≥2)`
    2. `🟡 Cooldown (fl=0)`

## 2. Phân định bản chất: Account Ceiling vs IP Subnet Block

- **Hiện tượng Ăn Nhả Đuôi (`used > 0`):**
  - Nick đã follow thành công $\ge 1$ lượt (ví dụ 5, 8, 12 lượt) rồi mới bị nhả ở lượt cuối.
  - **Bản chất kỹ thuật:** 100% là do **Account Session Rolling Limit (Trần bảo vệ phiên của TikTok áp lên cá nhân tài khoản)** khi bot ép budget vượt quá độ ấm của nick.
  - **Trạng thái IP:** Đường truyền IP Proxy bên dưới **hoàn toàn SẠCH 100%**. Dữ liệu đối soát chứng minh các nick khác trên cùng máy hoặc máy partner dùng chung proxy vẫn follow thành công 15-33 lượt bình thường.
  - **Kỷ luật xử lý:**
    - Tuyệt đối **KHÔNG tăng `fail_streak`** lũy tiến.
    - Chỉ gán cooldown ngắn **1 ngày** xả cache.
    - Ghi nhận `last_failed_ceiling = max(1, used + 1)` để phiên sau bóp trần an toàn né mốc gãy.
    - **TUYỆT ĐỐI CẤM NGẮT CẦU DAO IP BREAKER:** Việc giật sập IP 48h khi nick ăn nhả đuôi là sai lầm nghiêm trọng, kéo sập các máy anh em (partner machines) dùng chung proxy (bài học lịch sử M18 làm sập M56, M17 làm sập M55).

## 3. Chính sách Cầu Dao IP Breaker: Chế độ Quan sát Tích lũy (Phương Án 1)

- **Nguyên tắc vận hành (Phương án 1):**
  - Không tự động ngắt IP Breaker khi có lỗi follow đơn lẻ.
  - Chuyển sang chế độ **Monitor-Only (Quan sát tích lũy)** để bảo vệ tuyệt đối sự liên tục của các máy partner.
- **Công cụ đối soát & Kho dữ liệu tích lũy:**
  - Script: `D:/Taadaa/tools/ip_risk_audit.py`
  - Kho dữ liệu: `D:/Taadaa/data/ip_risk_audit_log.json`
- **Tiêu chuẩn phát hiện IP bẩn thực sự (Khi nào mới nghi vấn):**
  - Chỉ khi có **$\ge 2$ tài khoản Cựu Binh (Veteran)** trên cùng một cổng proxy bị **nhả ngay phát đầu tiên (`fl = 0`) trong cùng một ngày**, hệ thống mới đánh dấu proxy đó là `CRITICAL`.
  - Khi người vận hành yêu cầu `"kiểm tra report ip"` hoặc `"đối soát ip"`, chạy `python D:/Taadaa/tools/ip_risk_audit.py` để trích xuất báo cáo đối soát nhiều chu kỳ.

## 4. Giải mã Hiện tượng 176 Nick Tù Nặng: Bẫy "Anchor Check" ở Slot phụ (Row 2 & Row 4)

- **Đặc điểm chung của 176 nick tù nặng (Streak ≥ 2, max Streak 6):**
  - **Số lượng video & tuổi nick:** 100% nick ĐÃ ĐẠT CHUẨN Dual Gate (trung bình 15.6 video, min 11, max 20; 80% tạo tháng 7–9/2026, tuổi 60–90 ngày). Không phải do thiếu video hay nick quá non.
  - **Phân bổ vị trí:** ~57% tập trung ở **Row 4 (56 nick)** và **Row 2 (44 nick)** — các slot phụ thường chạy ở ca trưa/tối sau khi Row 1 (Cựu Binh) đã chạy xong.
  - **Thống kê follow lịch sử:** 80% (140/176 nick) có `lifetime_follows == 0` (chưa từng follow thành công được 1 ai trong đời).
- **Căn nguyên kỹ thuật (The Anchor Check Trap):**
  - Trong `mode2_follow_followers.py` (`_ensure_anchor_followed`), trước khi bot vào danh sách cào follow, bot kiểm tra tài khoản mồi (Anchor).
  - Nếu nút follow trên profile Anchor bị TikTok silent-drop (bật ngược lại về `not_followed`), hàm lập tức kích hoạt `engine.state.set_follow_failed()` và **dừng toàn bộ session ngay tại giây thứ 30**.
  - **Hệ quả dây chuyền:** Tài khoản chưa hề được thử follow danh sách thật, nhưng đã bị tính là 1 lần thất bại. Cứ mỗi chu kỳ 4 ngày bot gọi lại, nick lại vấp đúng bẫy Anchor này $\rightarrow$ Streak bị cộng dồn liên tiếp từ 1 lên 2, 3, 4, 6, kéo theo cooldown 15 ngày liên tục!
- **Kỷ luật vận hành:**
  - Khi rà soát nick tù nặng `lifetime_follows == 0`, không kết luận ngay là nick chết hay proxy hỏng.
  - Cần kiểm tra log `_ensure_anchor_followed` để tách biệt giữa: (1) Nick bị hạn chế tương tác thật vs (2) Vấp bẫy Anchor đối chứng bị TikTok ghim cờ.
  - **Sự thật về `failed: {}` rỗng:** Hầu hết nick Streak 6 có dict `failed: {}` rỗng 100% (chưa từng bấm trượt follow ai ngoài đời). Nguyên nhân thực sự gồm: (a) Kẹt nick ma trong `priority_targets.txt` (`bangtam2311` không tồn tại), (b) Đứt mạng/sập proxy giữa chừng (như M4 ngày 10/10), (c) Bị gọi dậy khi chưa hết hạn cooldown.
  - **Bác bỏ ngụy biện "Follow làm ấm tự nhiên":** Khi tài khoản đã bị TikTok silent-drop nút follow, bấm follow chéo hay follow tự nhiên ngoài feed đều bật ngược lại y hệt nhau. Không đưa ra giải pháp "làm ấm bằng follow tự nhiên" viển vông.

## 5. Quy trình Đối Soát & Tích Lũy Báo Cáo IP Risk (Audit Workflow)

- **Nguyên tắc tích lũy:** Giữ nguyên Phương án 1 (không tự động ngắt IP Breaker để tránh sập máy partner), nhưng âm thầm tích lũy số liệu vào `D:/Taadaa/data/ip_risk_audit_log.json` qua `D:/Taadaa/tools/ip_risk_audit.py`.
- **Kích hoạt theo yêu cầu người vận hành:**
  - Khi User nhắn: `"kiểm tra report ip"` hoặc `"đối soát ip"`.
  - Chạy `python D:/Taadaa/tools/ip_risk_audit.py` trích xuất báo cáo:
    1. Kiểm tra bao nhiêu cụm proxy đạt mức `CRITICAL` (≥2 cựu binh cùng `fl=0`).
    2. Bóc tách tỷ lệ ăn nhả đuôi cá nhân (`used > 0`, IP sạch) vs bẩn IP thực sự.
    3. Đưa ra khuyến nghị dựa trên số liệu lịch sử tích lũy để User xác nhận trước khi chuyển đổi chính sách.

