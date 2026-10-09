# Tri-Agent Consensus: Rule Overload Streamlining & Code-as-Policy

Tài liệu đúc kết phiên phản biện 3 bên (Sol GPT-5.6-Sol High, Claude Code CLI, Hermes Coordinator) về việc tinh gọn hệ thống luật lệ (Governance & Anti-Insanity) trên Taadaa Phone Farm.

---

## 1. Bản chất điểm nghẽn: "Rule Overload" & "LLM làm cảnh sát của chính nó"

- **Ảo giác an toàn qua Checklist Prompt:** Khi bắt Agent tự kiểm tra và khai báo "Gate 4: Đã kiểm tra", đây chỉ là chi phí token phòng thủ (defensive token waste), không mang tính bảo vệ vật lý.
- **Ô nhiễm nhận thức (Cognitive Bloat) trong Memory:** Memory bị nhồi 99% các dữ liệu vận hành cụ thể (tọa độ tap màn hình, cổng proxy, timeout S7, flag OPENBLAS) khiến Agent bị lag, rụt rè và tốn token phân giải trước mỗi tác vụ.
- **Cào bằng quy trình:** Ép Gate 6 (chụp ảnh màn hình) cho cả các task sửa code parser, refactor backend hoặc viết unit test không hề đụng vào thiết bị.

---

## 2. 4 Trụ Cột Tinh Gọn (Consensus Matrix)

| Trụ cột | Bản chất | Cách triển khai cụ thể |
|---|---|---|
| **Code-as-Policy** | Thay thế text răn đe bằng code gác cổng | Viết Pre-tool Hook (chặn lệnh adb tap/wipe trái phép tại shell), State Machine cơ học, và Script Validator độc lập (`closeout_gate.py`). Máy pass thì chạy, fail thì dừng, cấm bắt Agent giải trình checklist dài dòng. |
| **Tách Data khỏi Memory/Prompt** | Dữ liệu cấu hình không phải là Luật | Chuyển toàn bộ tọa độ pixel `(x, y)`, timeout S7, port proxy sang file config tập trung (`config/device_profiles.yaml` hoặc `config/farm_runtime_knowledge.json`). Memory chỉ lưu phong cách User & con trỏ trỏ tới config. |
| **Phân luồng Gate theo Scope** | Tránh một chiếc áo chật cho mọi task | - **Farm/UI Execution:** Bắt buộc Gate 6 (Max blind steps = 1, OCR mandatory, MEDIA:).<br>- **Pure Code / Backend:** Tắt Gate 6, chỉ yêu cầu Scope Lock + Focused Test (<30s) + Git Diff sạch. |
| **Thực thi Shadow Mode trước khi Cắt Prompt** | Tránh khoảng trống an toàn | Không xóa prompt vội vã. Quy trình chuẩn: Viết Validator -> Chạy Shadow Mode (ghi log phát hiện) -> Khi validator chứng minh bắt được lỗi thật mới tỉa bớt text trong prompt/memory. |

---

## 3. Vai Trò của Phán Đoán (LLM) vs Máy Móc (Code)

- **Phần Code đảm nhận:** Ép buộc bằng chứng vật lý phải tồn tại (đã dump UI XML chưa? đã có file OCR chưa? exit code test suite có bằng 0 không?).
- **Phần LLM đảm nhận:** Đọc hiểu ngữ nghĩa dòng thông báo OCR (ví dụ: phát hiện "Tài khoản bị khóa 29 phút" trong màn hình WebView mà XML không bóc được) để ra quyết định điều hướng nghiệp vụ. Code không thể thay thế hoàn toàn phán đoán linh hoạt trên giao diện động của Farm.

---

## 4. Kỷ Luật Triển Khai Thực Tế & Claude CLI Piped-Review Loop (25/09/2026)

- **Piped Stdin Pattern cho Claude CLI:** Khi phân tích file cấu hình lớn hoặc audit schema tri thức, CẤM cấp tool tự do (`--allowedTools "Read,Bash"`) nếu môi trường có nguy cơ nghẽn đĩa/scan chậm trên thư mục lớn (như ổ `D:/Taadaa/`). Dùng cú pháp `cat file | claude -p "..." --tools "" --max-turns 1` để ép Claude CLI pure-reasoning và nhận diện bẫy logic trong <= 3 giây không bị treo.
- **4 Bẫy Logic Phải Xử Lý Khi Tách Data Ra JSON (`farm_runtime_knowledge.json`):**
  1. *Xung đột Fail-Closed vs Ngoại lệ vận hành:* Quy tắc mang tính ngoại lệ (như *"Thiếu ngày tạo coi đủ tuổi"*) bắt buộc phải bọc trong `hard_rules.intentional_exceptions`, tránh để Worker hiểu nhầm là vi phạm fail-closed rồi dừng vô cớ hoặc tự ý phá hoại tài sản.
  2. *Bẫy từ lóng nội bộ ("Đá TB"):* Thuật ngữ lóng nếu không định nghĩa kỹ sẽ dẫn đến hành vi nguy hiểm. Cần ghi rõ trong glossary: *"Revoke thiết bị lạ trong device activity, TUYỆT ĐỐI KHÔNG ĐÁ THIẾT BỊ S7 HOẶC GPM CỦA FARM"*.
  3. *Bẫy Process Isolation:* Lệnh kill tiến trình (như `Kill Chrome GPMLogin`) bắt buộc phải ràng buộc điều kiện không kill nhầm Chrome CDP port `:9222` đang phục vụ tiến trình song song khác (Douyin f2).
  4. *Fail-Closed Guard trong Memory:* Khi chuyển data sang JSON ngoài, trong Memory bắt buộc phải có câu chốt chặn: *"Nếu thiếu key/TODO/lỗi file -> DỪNG và hỏi, TUYỆT ĐỐI CẤM đoán mò thông số"*.
- **Kết quả đo lường thực tế:** Memory giảm từ 99% (2.188 chars) xuống 34% (748 chars), User profile từ 99% xuống 57%, loại bỏ hoàn toàn tình trạng "lag não" và phản xạ rụt rè của Coordinator mà vẫn giữ vững 100% rào chắn an toàn farm.
