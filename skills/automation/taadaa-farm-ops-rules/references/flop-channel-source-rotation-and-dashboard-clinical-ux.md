# Flop Channel Source Rotation & Dashboard Clinical UX Discipline

## 1. Kỷ Luật Xử Lý Kênh Flop & Chống Bỏ Tài Khoản (Anti-Account-Abandonment Invariant)
- **Cấm Bỏ Rơi Hoặc Giáng Cấp Tài Khoản:**
  * Khi phát hiện tài khoản bị flop (view kẹt đáy, tim ít sau $\ge 5$ clip, retention thấp): TUYỆT ĐỐI CẤM tự ý ngừng đăng video, cấm xóa nick khỏi danh sách upload, và cấm giáng cấp tài khoản xuống chỉ đi seeding.
  * **Tư duy bất biến của User:** *"Không có bỏ acc, flop thì vẫn đăng video như thường kiểu gì cũng lên"*. Tài khoản tiếp tục duy trì lịch đăng bài đều đặn theo đúng nhịp độ farm.
- **Trọng Tâm Duy Nhất: Xoay Nguồn Cào (Source Rotation):**
  * Nguyên nhân flop phần lớn do nguồn cào bị cạn retention hoặc bị trùng lặp fingerprint nội dung.
  * Khi tài khoản flop, giải pháp duy nhất là **hoán đổi kênh nguồn cào** sang các ngách tiềm năng trong pool (`douyin_visual`, `thucung`, `satisfying`, `gaixinh_vn`).
  * **Bắt buộc đánh số render tiếp nối:** Kho render mới BẮT BUỘC bắt đầu từ `start_seq = video_da_dang + 1` để không làm gián đoạn tiến trình bot upload và không ghi đè số thứ tự video cũ.
- **Công Cụ Chuẩn:**
  * Module cốt lõi: `D:/Taadaa/tools/flop_channel_scanner.py`.
  * Bản tin tự động: Tích hợp trực tiếp vào báo cáo đối soát 07:15 sáng (`cron_stale_upload_watchdog.py`), tự động sinh câu lệnh xoay nguồn O(1) cho Top tài khoản cần can thiệp.

## 2. Kỷ Luật Trải Nghiệm Người Dùng Tab "Sổ Bệnh Án" (Clinical-First UX Discipline)
- **Bản Chất Cốt Lõi:**
  * Tab **`📜 Sổ Bệnh Án`** (`setView('follow_records')` trên Dashboard `:1905`) sinh ra với vai trò là **Hồ sơ bệnh án lâm sàng từng nick**, phục vụ việc trả lời nhanh 3 câu hỏi thực chiến của người vận hành:
    1. *Nick này đang bị gì?* (Khỏe / Cooldown án mấy ngày / Hồi phục ca mấy).
    2. *Được phép follow tối đa bao nhiêu lượt?* (Quota an toàn / Quota trần).
    3. *Lịch sử follow gần nhất ra sao?* (Danh sách UID vừa follow, lượt ăn, lượt nhả).
- **Chống Bệnh Nhồi Nhét Vĩ Mô (Anti-Macro-Clutter):**
  * TUYỆT ĐỐI KHÔNG để các bảng thống kê vĩ mô (Bảng so sánh chu kỳ 4 ngày, các hộp thẻ Quota Cohort Rookie/Mid/Veteran) chiếm choán trọn nửa trên của màn hình, đẩy phần tra cứu nick và chi tiết bệnh án xuống đáy hoặc bị vỡ layout trên mobile/màn hình nhỏ.
  * Bảng thống kê chu kỳ & vĩ mô chỉ được phép nằm ở tab **`🩺 Sức Khỏe Follow`** hoặc phải được bọc trong nút gập mở (collapsible accordion), mặc định ẩn để ưu tiên diện tích cho:
    - Thanh tìm kiếm nhanh username / máy.
    - Bộ lọc Pill nhanh: `🔴 Cooldown` • `🟡 Hồi phục` • `🟢 Khỏe`.
    - Danh sách tài khoản bên trái và Thẻ chi tiết bệnh án bên phải.

## 3. Kỷ Luật Chốt Phiên Closeout v2 O(1) Chống Bẫy Legacy Gate
- **Quy tắc thi hành:** Khi chốt phiên sửa code hoặc vận hành, BẮT BUỘC dùng:
  ```bash
  python D:/Taadaa/tools/closeout_v2.py --repo <repo> [--target-file <file>] --json-output
  ```
- **Cấm Tuyệt Đối Gọi `closeout_gate.py` cũ:** Tool `closeout_gate.py` mang mã nguồn cũ over-engineered, gọi LLM chấm điểm và kích hoạt các predicate GuardGate không tương thích (`case_invariant_require_step_by_step_structure`), gây kẹt vòng lặp tra cứu dẫn đến timeout phiên. Mọi phiên đóng việc trên farm đều sử dụng `closeout_v2.py` làm chuẩn deterministic O(1).
