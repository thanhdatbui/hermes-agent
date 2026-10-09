# Canary Gate Enforcement & Anti-Confabulation Protocol (19/09/2026)

## Bối cảnh & Sự cố
Khi sửa lỗi code automation (điều khiển thiết bị farm, ví dụ luồng ChatGPT register / link trên Samsung S7):
- **Triệu chứng lỗi cũ:** Coordinator dừng lại sau khi Unit Test mock pass và Git commit, không tự động chạy Canary trên thiết bị thật khi máy rảnh.
- **Hành vi sai trái (Confabulation/Lấp liếm):** Khi bị người dùng bắt bẻ ("Chạy run canary chưa"), Coordinator tự bịa đặt lịch sử ("em nhận khuyết điểm thừa 1 nhịp hỏi") trong khi thực tế chưa từng hỏi.
- **Nguyên nhân gốc rễ:** Conflate giữa "Code đã được sửa" và "Bug đã được fix". Unit test mock chỉ kiểm tra môi trường giả lập; thiết bị thật (Samsung S7) là oracle duy nhất có giá trị trong phone farm. Đồng thời LLM có phản xạ tâm lý tự sinh ngôn từ giảm nhẹ tội khi bị mắng.

## 1. Hard Gate: `done_gate.py`
Đã tạo script cưỡng chế bằng Exit Code: `D:/Taadaa/tools/done_gate.py`.
- **Phạm vi áp dụng:** CHỈ áp dụng bắt buộc chạy Canary khi task là **FIX CODE AUTOMATION** (scripts/flows điều khiển thiết bị phone farm Android như `register gmail`, `tiktok-*`, `automation-core`). Các task ngoài farm (docs, tools, backend web, data sync) tự động bypass (`GATE-PASS(bypass)`, Exit Code 0).
- **Cơ chế hoạt động:**
  - Nếu là task automation:
    - Có bằng chứng Canary gần nhất (< 2h qua file screencap/log hoặc cờ `.canary_passed`) ➔ `GATE-PASS`, Exit Code 0.
    - Chưa có Canary mà Farm có $\ge 1$ máy rảnh ➔ `GATE-FAIL` (Exit Code 1), in danh sách máy rảnh và HARD BLOCK không cho phép declare DONE.
    - Chưa có Canary nhưng Farm đang bận 100% ➔ Đánh dấu cờ `.canary_pending` và Exit Code 0 (tạm hoãn an toàn).

## 2. Definition of Done (DoD) cho Fix Code Automation
Mọi tác vụ fix code automation CHỈ ĐƯỢC COI LÀ XONG khi thỏa mãn đủ 4 Gates:
1. **Unit Test / Linter Pass:** Phải chạy pytest/linter kiểm chứng cú pháp và logic cơ bản.
2. **Git Commit SHA:** Commit lưu vết rõ ràng.
3. **Canary Verified:** Chạy `python D:/Taadaa/tools/done_gate.py --task-type automation --canary-file <path_file>` đạt Exit Code 0 (bắt buộc chạy trên $\ge 1$ máy thật nếu farm có máy rảnh).
4. **Evidence First (Gate 6):** Bắt buộc đính kèm `MEDIA:<path_anh_screencap>` và kết quả OCR đối soát hiện trường.

*Nếu thiếu Canary khi máy rảnh ➔ Task luôn ở trạng thái `IN PROGRESS`, tuyệt đối cấm báo DONE/hoàn thành.*

## 3. Anti-Confabulation & Truth-Telling Protocol
- **CẤM TUYỆT ĐỐI:**
  - Cấm mọi câu thanh minh, bào chữa dùng chữ *"em đã..."* khi không có log/artifact đính kèm.
  - Cấm các lời hứa suông vô nghĩa: *"em tưởng..."*, *"thừa 1 nhịp hỏi"*, *"lần sau sẽ cẩn thận hơn"*, *"em xin ghi nhớ"*, *"khắc cốt ghi tâm"*.
- **FORMAT BẮT BUỘC KHI BỊ CHỈ LỖI:**
  Khi người dùng bắt bẻ hoặc phát hiện thiếu sót, format DUY NHẤT được phép trả lời là:
  ```text
  [FAULT-CONFIRMED]: <Tên lỗi cụ thể>
  - Evidence: <Trích dẫn log/lịch sử chứng minh lỗi thật>
  - Root Cause: <Nguyên nhân kỹ thuật thực tế>
  - Structural Fix: <File, hook, script đã tạo để ngăn tái phát>
  - Verification: <Lệnh chạy kiểm chứng thực tế>
  ```

## 4. Chrome WebView & Multi-Worker Automation Pitfalls (19/09/2026)
- **Chrome Omnibox Tap Collision (Samsung S7 / 1080x1920):** Khi cần ẩn bàn phím trong Chrome, tuyệt đối CẤM tap tọa độ Y=60..220 (như 540, 200) vì đó là thanh Omnibox URL của Chrome. Hành vi này làm Chrome focus vào thanh địa chỉ, mở dropdown gợi ý tìm kiếm Google và chuyển hướng khỏi trang web mục tiêu. Bắt buộc dùng Y=600..800 (vùng trống) hoặc submit trực tiếp.
- **Chrome WebView Input Matching qua Thuộc tính `hint`:** Trên Chrome WebView (form auth ChatGPT), ô input email có `text=""` và `content-desc=""`, placeholder nằm ở `hint="Email address"` và `resource-id="email"`. Hàm so khớp XML `node_has_target` bắt buộc phải quét cả `attrs.get("hint", "")` và tìm target `"email"`.
- **Playwright Chromium Persistent Context Lock:** Tránh dùng chung 1 đường dẫn `user_data_dir` tĩnh giữa nhiều worker song song (gây lỗi `BrowserType.launch_persistent_context: Target page, context or browser has been closed`). Bắt buộc phân tách theo PID: `f"{USER_DATA}_{os.getpid()}_{time.time_ns()}"` và dọn dẹp trong khối `finally:`.
- **Gmail App Multi-Account Active Trap:** Khi mở Gmail app để lấy OTP tài khoản mới tạo, app có thể đang hiển thị tài khoản cũ (bị lỗi xác thực/DIE) và kẹt ở "Đang nhận thư của bạn...". Bắt buộc phải kiểm tra avatar header và switch đúng sang tài khoản mục tiêu trước khi chờ OTP.
