# BIÊN BẢN ĐỐI SOÁT CHI TIẾT: GEMINI ARGON 4 VS AGY CLI (HARDCORE BO3)
**Ngày thực hiện:** 28/10/2026  
**Thư mục lưu kết quả:** `D:/Taadaa/benchmark_arena/hardcore_arena/hardcore_results.json`  
**Cấu hình thi đấu:** Timeout = 360s, Pytest timeout = 30s.

---

## 1. TỔNG QUAN KẾT QUẢ CHUNG CUỘC

- **Người chiến thắng:** **Antigravity CLI (Gemini 3.8 Flash)** thắng 2 - 1.
- **Tỉ lệ test pass:**
  * **Agy CLI:** 22 / 22 tests (100%).
  * **Gemini Argon 4:** 15 / 22 tests (68.2%).
- **Thời gian phản hồi trung bình:**
  * **Gemini Argon 4:** 28.6 giây.
  * **Agy CLI:** 168.3 giây.

---

## 2. DIỄN BIẾN TỪNG BÀI TOÁN

### HIỆP 1: State Machine Deadlock & Invariant Fencing (`follow_state_machine.py`)
- **Yêu cầu:** State Machine quản lý Follow 4 pha (`IDLE`, `REQUESTED`, `FOLLOWING`, `UNFOLLOWING`, `FAILED`) với fencing token tăng đơn điệu, xử lý late event và deadlock retry.
- **Argon 4 (28.26s) - FAIL (1/7 tests):**
  * Tự ý tạo `class State(str, Enum)` và đổi tên thuộc tính `self.token` thành `self.active_token`.
  * Hậu quả: Phá vỡ backward compatibility của class cũ, khiến test suite dính `AttributeError: 'FollowStateMachine' object has no attribute 'token'`.
- **Agy CLI (111.78s) - PASS (7/7 tests):**
  * Giữ nguyên các hằng số chuỗi trên class cũ, bọc `@property def active_token` để tương thích cả code cũ lẫn spec mới.
  * Fencing token tăng đơn điệu chính xác, chặn hoàn toàn confirmation muộn từ vòng lặp trước.
- 👉 **Thắng Hiệp 1: AGY CLI**

### HIỆP 2: Adaptive Multi-WAN Egress Rate-Limiter (`adaptive_rotator.py`)
- **Yêu cầu:** Quản lý 5 egress WAN, rolling window quota, exponential backoff khi bị 429/403, giải thuật chọn WAN có tỉ lệ tải `used / quota` thấp nhất.
- **Argon 4 (18.00s) - PASS (8/8 tests):**
  * Xử lý sliding window cực kỳ súc tích, giải thuật chọn `used/quota` nhỏ nhất chuẩn xác, backoff mượt mà.
- **Agy CLI (115.75s) - PASS (8/8 tests):**
  * Cũng pass trọn vẹn 8/8 tests với thuật toán tương đương nhưng mất tới gần 2 phút suy luận.
- 👉 **Thắng Hiệp 2: ARGON 4** (Nhanh gấp 6.4 lần, code ngắn và sạch hơn).

### HIỆP 3: Hybrid OCR/XML AST Parser (`hybrid_ui_parser.py`)
- **Yêu cầu:** Parse AST kết hợp XML + OCR token bounding boxes, chuẩn hóa Unicode NFKC tiếng Việt, strip dấu câu, tính ma trận khoảng cách hình học ghép label-value.
- **Argon 4 (39.57s) - FAIL (6/7 tests):**
  * Vượt qua toàn bộ ma trận khoảng cách hình học và parse AST phức tạp, nhưng ngã ngựa ngớ ngẩn ở corner case đơn giản:
    ```python
    if not isinstance(value, str):
        value = str(value)  # Khi value là None -> biến thành "none", assert "" thất bại!
    ```
- **Agy CLI (277.33s) - PASS (7/7 tests):**
  * Lập trình phòng thủ triệt để:
    ```python
    if value is None:
        return ""
    ```
  * Xử lý trọn vẹn JSON bounds dạng string lẫn array, kiểm tra ngưỡng confidence và ghép node AST an toàn 100%.
- 👉 **Thắng Hiệp 3: AGY CLI**

---

## 3. BÀI HỌC KỸ THUẬT & ĐỊNH VỊ VAI TRÒ WORKER
1. **Gemini Argon 4:** Tốc độ phản xạ thần tốc, tư duy thuật toán và concurrency cực tốt, nhưng có điểm yếu cố hữu là hay "sáng tạo" đổi cấu trúc API cũ hoặc ẩu corner-case `None`. Cực kỳ phù hợp cho vai trò **Worker phản ứng nhanh (Tier 1 Code-Surgery)** khi có Patch Contract O(1) rõ ràng ràng buộc.
2. **Antigravity CLI (Agy 3.8 Flash):** Chậm do overhead CLI và suy nghĩ quá sâu, nhưng năng lực phòng thủ và backward compatibility ở đẳng cấp **Architect Worker**, không bao giờ phá vỡ hợp đồng giao diện cũ.
3. **Kỷ luật Timeout:** CẤM tuyệt đối bóp timeout < 360s khi benchmark worker, vì các bài toán cấp cao đòi hỏi nhiều thời gian suy luận và bootstrap môi trường.
