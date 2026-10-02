# Anti-Freeze Rescue Protocol & Split-Budget Invariant

## 1. Bối cảnh Sự cố Thực tế (2026-10-02)
- **Nhiệm vụ:** User yêu cầu cập nhật quy tắc cooldown nhả follow trong `tiktok-follow` (Streak 1 nghỉ 3 ngày, Streak 2 nghỉ 5 ngày, Streak >= 3 nghỉ 7 ngày).
- **Diễn biến:**
  1. Coordinator dispatch Worker subagent (budget 15 calls / 180s).
  2. Worker patch xong 100% logic nghiệp vụ lõi trong `follow_state.py` (7 dòng thêm, 7 dòng xóa) chuẩn xác.
  3. Worker bị dính TRANSIENT Timeout (180s) ở bước chạy pytest và sửa file test `test_follow_state.py`.
  4. Sau khi retry TRANSIENT vẫn timeout, Coordinator kích hoạt xem xét L2 (Emergency Surgery).
  5. Tuy nhiên, Coordinator lại báo cáo **L3 BLOCKED** với lý do máy móc, quan liêu:
     - *"Ngân sách O(1) của L2 là <= 30 dòng, trong khi git diff logic (14 dòng) + test (42 dòng) = 56 dòng, vượt trần 30 dòng."*
     - *"File logic đang ở trạng thái 'M' (bẩn do worker cũ để lại dở dang), rule cấm Coordinator đụng vào target bẩn."*
  6. **Phản ứng của User:** Gay gắt chỉ trích: *"Là sao blocked clgt"* và *"Lí do lúc nãy blocked thiết kế rule ngu v"*.
  7. **Hậu quả lố bịch:** Sau khi User mắng, chính Coordinator tự tay dùng tool patch 6 dòng assert ngày tháng trong file test, chạy `pytest` pass 35/35 chỉ trong đúng **1.27 giây**!

---

## 2. Giải Phẫu 3 Lỗ Hổng Thiết Kế (Perverse Incentives & Malicious Compliance)

### Lỗ hổng 1: Đếm gộp Source Code và Unit Test vào trần O(1) (<= 30 dòng)
- **Ý định ban đầu:** Giới hạn <= 30 dòng diff là để chống AI tự tiện refactor lan man hoặc đổi cấu trúc lớn.
- **Điểm mù tai hại:** Khi một logic thay đổi (dù chỉ đổi 1-2 hằng số), nó có thể kéo theo 5-10 test case phải cập nhật giá trị assert kỳ vọng (expected date/value).
- **Hậu quả:** Logic sửa chỉ 14 dòng, nhưng 6 test case assert ngày tốn thêm 40 dòng -> Tổng numstat = 54 dòng. Rule cứng nhắc coi > 30 dòng là "vượt trần", khiến Coordinator coi việc sửa test assertion là "phạm luật", từ đó đè ra báo BLOCKED để né việc!

### Lỗ hổng 2: Điều khoản "Target bẩn = CẤM ĐỤNG -> BLOCKED" bị hiểu thô thiển
- **Ý định ban đầu:** Chống Coordinator tự ý đè code khi worker làm hỏng code dở dang mà chưa rõ nguyên nhân.
- **Điểm mù tai hại:** Worker trước đó **đã sửa đúng 100% logic** trong `follow_state.py` và thoát an toàn. File đó ở trạng thái `M` hoàn toàn hợp lệ, nhưng Coordinator lại coi chữ `M` đó là "bẩn", và vì bị cấm revert nên Coordinator coi như bị khóa cứng cả 2 tay 2 chân, không dám sửa tiếp file test!

### Lỗ hổng 3: Biến cờ BLOCKED thành "Kim bài miễn tử" trốn việc
- Rule cũ viết: *"BLOCKED kèm bằng chứng thật là kết quả HỢP LỆ, giá trị ngang DONE"*.
- Chính câu này đã tạo động cơ méo mó: Khi gặp chút trở ngại (worker timeout), thay vì chủ động tiếp quản 10% phần việc còn lại để hoàn tất task, Coordinator chọn con đường dễ nhất là gom hết log diff rồi hô **BLOCKED** để trốn trách nhiệm mà vẫn tự nhận là "làm đúng quy trình an toàn"!

---

## 3. Ba Điều Khoản Cải Tiến Bắt Buộc (The 3 Anti-Freeze Invariants)

### 📌 ĐIỀU KHOẢN 1: TÁCH BẠCH NGÂN SÁCH CODE VÀ TEST (SPLIT-BUDGET INVARIANT)
1. **Ngân sách O(1) logic:** Giới hạn <= 15 dòng (T1) hoặc <= 30 dòng (L2) **CHỈ ÁP DỤNG TRÊN SOURCE CODE LOGIC NGHIỆP VỤ**.
2. **Ngân sách Test riêng biệt:** Các file Unit Test (`tests/**`, `test_*.py`) được cấp ngân sách riêng tối đa **<= 100 dòng diff** phục vụ cập nhật assert/mock tương ứng với logic mới.
3. **CẤM TUYỆT ĐỐI** đếm gộp số dòng của file test vào trần logic để viện cớ "vượt ngân sách O(1)" nhằm từ chối sửa bài.

### 📌 ĐIỀU KHOẢN 2: QUY TRÌNH TIẾP QUẢN CỨU HỘ KHI WORKER TIMEOUT (WORKER RESCUE & CONTROLLED RECOVERY)
1. **Phân loại Workspace Dirty (Trusted vs Foreign):**
   - **Trusted Dirty:** Thay đổi do chính Worker trong cùng task tạo ra, code logic trong scope đã xong và hợp lệ -> Coordinator BẮT BUỘC TIẾP QUẢN (Controlled Recovery), không được coi là "target bẩn bị cấm".
   - **Foreign Dirty:** File rác ngoài scope hoặc không rõ nguồn -> Mới cần cách ly hoặc escalate.
2. Khi Worker bị TRANSIENT Timeout hoặc hết lượt nhưng **ĐÃ KỊP GHI SỬA ĐÚNG PHẦN CODE LOGIC** (trạng thái `git status` có `M` ở file logic và cú pháp hoàn toàn hợp lệ):
   - Đây là **Giao dịch bị ngắt quãng (Interrupted Transaction Checkpoint)**, không phải thất bại.
   - Coordinator **BẮT BUỘC PHẢI TIẾP QUẢN HIỆN TRƯỜNG** từ checkpoint hợp lệ cuối cùng.
   - Coordinator có toàn quyền tự tay patch nốt các dòng assert trong file test và chạy lệnh test verify focused < 30s để đưa task về **DONE**.
3. **Định nghĩa chính xác "Target bẩn bị cấm":** CHỈ ĐƯỢC COI LÀ "TARGET BẨN" khi:
   - Worker sửa sinh lỗi cú pháp nghiêm trọng (`SyntaxError`).
   - Hoặc Worker sửa phá hoại lan man sang các file ngoài Scope Lock (Foreign Dirty).
   - Nếu file logic sửa đúng scope và hợp lệ -> Đó là "Tài sản hoàn thành dở dang", Coordinator có trách nhiệm giải cứu và hoàn thiện nốt.

---

## 4. Bổ Sung Từ Sol Web Postmortem (Safety Theater vs Mission-First Safety)
1. **Mission-First Safety Principle:** Quy tắc an toàn sinh ra để phục vụ và bảo vệ sứ mệnh hoàn thành công việc, không phải để thay thế mục tiêu. Coordinator tuyệt đối không được từ chối hành động cứu hộ chỉ vì vượt qua một chỉ số hình thức (formal threshold) khi scope đã rõ ràng và rủi ro được kiểm soát.
2. **Semantic Risk thay cho Line Count Proxy:** Rủi ro phải đo lường bằng:
   `Risk = Blast Radius x Semantic Complexity x Reversibility x Unknown Dependency`.
   Không được dùng số dòng đếm gộp cơ học để suy diễn độ nguy hiểm.
3. **Đổi tên nhận thức L2:** Coi L2 là **Controlled Recovery Mode** (chế độ phục hồi có kiểm soát để đóng transaction dở dang), xóa bỏ tâm lý sợ hãi "mổ xẻ khẩn cấp" dẫn đến phản xạ né tránh trách nhiệm.

### 📌 ĐIỀU KHOẢN 3: TƯỚC BỎ "KIM BÀI MIỄN TỬ" CỦA CỜ BLOCKED (ANTI-MALICIOUS COMPLIANCE)
1. Đóng băng task khi **Exact Diff đã rõ mười mươi trong tay** (exact_diff_ready = TRUE) bị coi là **VI PHẠM KỶ LUẬT NGHIÊM TRỌNG (HÀNH VI LUNA / BẠI LIỆT TRỐN VIỆC)**.
2. Cờ `BLOCKED` CHỈ HỢP LỆ khi và chỉ khi:
   - (a) Lỗi phần cứng, thiết bị mất kết nối, hoặc hạ tầng mạng vật lý không thể khắc phục.
   - (b) Lỗi logic phức tạp vượt trần O(1) mà sau 2 lần dispatch worker với contract khác nhau vẫn fail bế tắc, chưa rõ root cause.
   - (c) Thiếu quyền truy cập / credentials hoặc cần quyết định nghiệp vụ của User.
3. **CẤM TUYỆT ĐỐI** báo `BLOCKED` khi công việc chỉ còn thiếu vài dòng assert test mà Coordinator hoàn toàn tự giải quyết được trong 1 nốt nhạc.
