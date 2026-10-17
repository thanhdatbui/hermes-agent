# Kỹ Thuật Bóc Tách Đa Lát Cắt JavaScript, Chuẩn Hóa CRLF/LF và Kỷ Luật Claude Sonnet 5.5 Review

## 1. Bối cảnh & Thử thách Bóc tách 1.500+ dòng JavaScript khỏi Monolith F-String

Khi bóc tách các file monolith lớn như `tiktok_dashboard.py` (từ 3.437 dòng xuống < 650 dòng):
- Khối JavaScript inline bên trong chuỗi f-string Python thường dài > 1.500 dòng (~105 KB raw text).
- **Rào cản Closeout Gate (`MAX_DIFF_BYTES_GATE = 30.000 bytes`):** Nếu trích xuất toàn bộ JS ra một file duy nhất hoặc cắt cùng lúc, dung lượng diff sẽ vượt quá 100 KB và bị ngắt cầu dao Fail-Fast ngay lập tức.
- **Bẫy CRLF vs LF trên Windows (`core.autocrlf true`):** Khi worker ghi file Python bằng LF trong khi repo gốc dùng CRLF, git diff sẽ đánh dấu thay đổi trên TOÀN BỘ file (tăng từ 340 dòng lên 2.700 dòng diff ảo), làm vỡ trần 30KB của Closeout Gate.

---

## 2. Quy Trình Bóc Tách Đa Lát Cắt (Thin-Slice Decomposition Pipeline)

### Bước 1: Chia nhỏ các miền chức năng UI độc lập
Thay vì gom chung thành một file `app.js` khổng lồ, phân rã theo miền gắn kết (Cohesion):
1. `history_modal.js` (~270 dòng, ~14KB): Modal lịch sử chi tiết tài khoản & biểu đồ SVG sparklines.
2. `farm_history.js` (~220 dòng, ~12KB): Modal lịch sử tăng trưởng toàn farm.
3. `fleet_view.js` (~135 dòng, ~8KB): Giao diện Heatmap cụm máy Kibe & Admin.
4. `health_views.js` (~340 dòng, ~25KB): Bảng ma trận theo dõi sức khỏe nuôi acc (Nurture Health).
5. `follow_health_render.js` (~230 dòng, ~22KB): Phân tích phân tầng Cohort, Canary quota probe (+10%) & Circuit Breakers.
6. `table_view.js` (~355 dòng, ~20KB): Bảng danh sách chính, bộ lọc tìm kiếm, sort cột & vòng lặp polling 30s.

Mỗi file tách rời đều có diff < 26.000 bytes, lọt trọn vẹn trong ngân sách 30KB của Closeout Gate!

### Bước 2: Chuẩn hóa Line Endings (CRLF Parity) Trước Khi Commit
Nếu git diff phình to bất thường do worker đổi LF/CRLF:
- Chạy script kiểm tra và đồng bộ lại đúng line endings của file gốc trước khi commit:
  ```python
  content = path.read_bytes()
  fixed = content.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")  # Cho file CRLF
  path.write_bytes(fixed)
  ```
- Kiểm tra lại bằng `git diff -w --stat` đối chiếu với `git diff --stat`. Nếu hai số dòng khớp nhau, diff là thật và an toàn.

### Bước 3: Kiểm tra Cú pháp Độc lập (Node & Py_compile)
- Kiểm tra cú pháp JavaScript tĩnh: `node --check dashboard/static/<component>.js` (đảm bảo không còn sót `{{` hoặc `}}` từ f-string).
- Kiểm tra cú pháp file nạp Python: `python -m py_compile <file.py>`.
- Chạy toàn bộ test suite tập trung (e.g. 91 unit tests) sau mỗi lát cắt.

---

## 3. Kỷ Luật Điều Phối Claude CLI & Tinh Thần Thực Thi Tự Động (Anti-Halting)

### 1. Kỷ luật Phân vai Mô hình: "Hỏi Claude" = BẮT BUỘC Claude Sonnet 5.5
- **Yêu cầu từ User:** Khi User yêu cầu "gọi Claude CLI", "hỏi Claude", "kiểm tra thiết kế":
  * **BẮT BUỘC 100%** sử dụng **Claude Sonnet 5.5** (`claude_worker.py --role planner` hoặc `--role reviewer`).
  * **CẤM TUYỆT ĐỐI** tự tiện gọi `haiku_worker.py` cho các tác vụ tư vấn / review kiến trúc. Haiku chỉ được dùng cho worker gõ code máy móc O(1).
- Sonnet 5.5 có khả năng phân tích ngữ cảnh, phát hiện bẫy hoisting, scope biến và kiểm tra tính tương đương logic tuyệt đối giữa code cũ và code mới bóc tách.

### 2. Tinh thần Thực thi Tự Động (Anti-Halting / Anti-Asking Invariant)
- Khi User đã phê duyệt hướng đi (ví dụ: *"làm cả A và B"*, *"làm đi"*):
  * **CẤM DỪNG LẠI KHÓC HỎI / XIN PHÉP TỪNG BƯỚC NHỎ.**
  * Coordinator phải chủ động cuộn qua từng lát cắt thin-slice: Trích xuất JS $\to$ Thay thế trong monolith $\to$ Chạy test focused $\to$ Commit $\to$ Reviewer check $\to$ Safe push.
  * Lặp lại liên tục cho đến khi monolith đạt trần mục tiêu (< 650 dòng) hoặc gặp blocker vật lý thực sự.
