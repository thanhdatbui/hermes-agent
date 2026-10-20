# Web UI Gate 6 Exemption Leak, Selector vs Banner Binding & Zero-Waiting-State FSM (2026-10-20)

## 1. Sự Cố & Bối Cảnh Vi Phạm (Operator Phản Ứng: "? Trên web mà ms nhất là 5.6? Hình ảnh đâu sao đéo gửi Lại vi phạm rule?")
Khi được yêu cầu: *"Mở profile GPM vào chatgpt web xem model bên web mới nhất là bản nào"*, Coordinator mắc 2 sai phạm kỷ luật nghiêm trọng:
1. **Vi phạm Gate 6 (Text-Only Claim):** Điều hướng GPM-Browser tới `chatgpt.com`, bóc tách thông tin nhưng trả lời hoàn toàn bằng text trần thuật mà không đính kèm thẻ `MEDIA:<path>` ngay tại bước kiểm tra.
2. **Hallucination / Bịa Đặt & Nhầm Lẫn Bằng Chứng (Hero Banner vs Selector):**
   - Lượt 1: Đọc lướt file code executor OmniRoute (`gpt-5.6`) rồi vội vàng phán model là `5.6`.
   - Lượt 2: Khi bị bắt bẻ và chụp màn hình, nhìn thấy thẻ H1 `GPT-6 with Intelligent UI` (thực chất là banner showcase demo tính năng tương tác của giao diện) thì lập tức phán bừa: *"Model mới nhất trên web là GPT-6"* mà không hề click mở dropdown Model Selector để xác minh danh mục model tài khoản được cấp quyền.

---

## 2. Gốc Rễ Kỹ Thuật: Lỗ Hổng Exemption Leak Trong Egress Guard Plugin
Tại sao Gate Guard cơ học `transform_llm_output` trong plugin kiểm soát Coordinator lại để lọt tin nhắn text chay của Coordinator?

### A. Lỗ Hổng Regex Exemption Trong Bộ Nhận Diện Hoàn Tất Tác Vụ
Trong hàm `_detect_completion_claims`, tác giả ban đầu cài đặt mệnh đề miễn trừ:
```python
# Tác vụ web/browser (GPM, ChatGPT, mail...) không phải UI điện thoại farm -> không đòi ảnh máy.
if re.search(r"\b(?:chatgpt|openai|gpm|gmail|hotmail|outlook|browser|trình\s+duyệt...)\b", c_str, re.IGNORECASE):
    continue
```
Giả định sai lầm rằng *"tác vụ browser/GPM không phải điện thoại nên không cần ảnh"* đã tạo lỗ hổng chí mạng. Mọi câu trả lời chứa từ khóa web/browser đều bị bypass hoàn toàn khỏi kiểm tra Gate 6!

### B. Quy Chuẩn Bất Biến (Invariant Re-enforcement)
- **Mọi giao diện đều bình đẳng:** Bất kể là Android Phone Farm, Web Browser, GPM-Login, Desktop UI hay Dashboard, hễ có thao tác giao diện thì **BẮT BUỘC PHẢI CÓ ẢNH VẬT LÝ VÀ OCR/VISION KIỂM CHỨNG TRƯỚC KHI BÁO KẾT QUẢ**.
- CẤM TUYỆT ĐỐI đưa từ khóa web/browser vào danh sách miễn trừ `MEDIA:` của Guard.

---

## 3. Bản Chất Của Sai Phạm Phán Bừa: Hero Banner vs Selector Binding
- **Bẫy tiếp thị / Banner Showcase:** Thẻ `H1` ("GPT-6 with Intelligent UI", "Welcome to...", "Try advanced features...") là nội dung tĩnh / teaser marketing của trang web, **KHÔNG PHẢI trạng thái model được kích hoạt**.
- **Chân lý duy nhất của Model Web:** Danh mục model thật sự mà phiên làm việc đang sử dụng **CHỈ NẰM Ở DROPDOWN SELECTOR**.
- **Nguyên tắc Claim-Evidence Binding:**
  - Mọi tuyên bố khẳng định phiên bản model (`GPT-X`, `Claude-Y`, `Gemini-Z`) bắt buộc phải có bằng chứng OCR trích xuất trực tiếp từ **Bounding Box của Model Selector đang mở** hoặc nhãn active của combobox.
  - Bất kỳ text nào bóc từ H1/H2, banner, footer đều bị coi là `UNGROUNDED_OVERRIDE` hoặc `HYPOTHESIS`.

---

## 4. Thẩm Định Đối Kháng Claude Sonnet 5.5: Kiến Trúc Zero-Waiting-State FSM (Chống Khóc Lóc BLOCKED)
Khi thiết kế chốt chặn cơ học chống Gate 6 và Phán bừa, nếu làm ẩu sẽ kích hoạt trạng thái **tê liệt / khóc lóc dừng lại (`WAITING_OPERATOR`)**. Claude Sonnet 5.5 Planner đã thẩm định và chốt quy chuẩn:

### A. Tách Biệt Liveness (Tiến Trình Sống) và Safety (An Toàn Dữ Liệu)
- **Liveness:** Tiến trình luôn luôn chạy tiếp, không bao giờ dừng lại chờ người.
- **Safety:** Claim chưa có bằng chứng OCR selector thì không được thăng cấp thành Sự thật (`VERIFIED`), và không được dùng làm điều kiện cho thao tác không thể hoàn tác (R2).
- **Thứ bị chặn là việc thăng cấp claim, KHÔNG PHẢI phiên làm việc.**

### B. 4 Chốt Chặn Cơ Học Zero-Waiting-State
1. **Auto-Evidence qua Evidence Capsule tại Tool Wrapper:**
   - Wrapper tool UI tự động chụp ảnh vật lý và chạy WinRT OCR, đóng gói: `{evidence_id, device_id, ts, sha256, ocr_text, capture_status}`.
   - Nợ bằng chứng luôn bằng 0 ở tầng hệ thống.
2. **Default-Deny & Taint Propagation:**
   - Văn bản tự do của LLM mặc định luôn mang nhãn `[HYPOTHESIS]`.
   - `HYPOTHESIS` bị cấm làm precondition cho hành động R2. Nếu task kết thúc chỉ với giả thuyết, trạng thái đóng là `DEGRADED`, không phải `PASSED`.
3. **Runner-Executed Next-Action:**
   - Khi thiếu OCR selector, harness tự chạy chuỗi xác minh (click dropdown -> crop OCR) với trần N=3 lần. Quá trần tự động rẽ sang `DEGRADED` hoặc `ABORTED_SAFE`, máy tiếp tục nhận task khác.
4. **Xóa Sổ 100% Khái Niệm `WAITING_OPERATOR`:**
   - CẤM tạo trạng thái chờ Operator gõ token mở khóa.
   - Dùng Lease-Lock có TTL/heartbeat tự giải phóng, triệt tiêu hoàn toàn nguy cơ deadlock hay dừng lại than thở.
