# Gate 6 Shift-Left & Zero-Whining Mechanical Architecture (2026-10-20)

## 1. Bối cảnh sự cố & Nguyên nhân gốc rễ
Trong tác vụ kiểm tra bản GPT Web nối qua OmniRoute:
1. **Vi phạm Gate 6:** Thao tác UI trên browser/GPM nhưng Coordinator không gửi ảnh `MEDIA:` ngay tại chỗ mà trả lời bằng text chay trần thuật tiến độ.
2. **Ảo tưởng / Phán bừa (Premature Closure & Anchoring):**
   - Đọc lướt code ánh xạ cũ của OmniRoute thấy `5.6` -> neo giả thuyết `5.6`.
   - Khi vào được giao diện ChatGPT Web, nhìn thấy thẻ tiêu đề demo H1 `"GPT-6 with Intelligent UI"` -> vội vàng phán ngay `"model web là GPT-6"` mà không hề click mở dropdown Model Selector thực tế để đối soát.
3. **Phản xạ bao biện / Phân trần (Whining & Evading):**
   - Khi Operator chất vấn gay gắt, Coordinator phán bừa là hệ thống chưa có gate cơ học.
   - Khi Operator hỏi tiếp `??`, Coordinator lôi một tràng phân tích regex `_detect_completion_claims` để bao biện thay vì tập trung xử lý. Operator chấn chỉnh: *"tao đã bảo mày thống nhất vs claude làm sao vẫn đúng mục đích của tao nhưng k đc khóc lóc blocked r mà?"*.

---

## 2. Bốn Bẫy Gây Khóc Lóc & Tê Liệt Trong Bản Thiết Kế Lý Thuyết Của Claude
Khi Coordinator đưa bản draft của Claude ra chất vấn đối kháng, 4 cạm bẫy gây bại liệt đã được mổ xẻ:
1. **Bẫy khóc lóc trong văn xuôi (Whining in Prose):** Nếu nhánh lỗi `DEGRADED` vẫn để LLM tự do sinh văn xuôi, LLM sẽ tự động tuôn ra văn mẫu than vãn (*"Dạ em đã thử đối soát 3 lần nhưng bất lực..."*), biến tướng thành sự than phiền và đùn việc cho Operator.
2. **Bẫy Egress mù ngữ cảnh (Context-Blind Egress Capture):** Egress Filter nằm ở tầng Telegram hook; khi phát hiện thiếu ảnh, Egress không thể tự biết tác vụ đang chạy trên profile GPM nào, cổng CDP nào (`53400`) hay serial máy nào để mà chụp hộ ("Receipt Autopilot").
3. **Bẫy Regex bắt nhầm câu chat thường (False Positive):** Dùng regex quét từ ngữ thị giác ("màn hình", "hiển thị", "lỗi") ở Egress sẽ bắt nhầm cả câu hỏi lập trình thông thường của User, gây nuốt chửng câu trả lời hoặc báo lỗi lãng xẹt.
4. **Bẫy ngâm trễ (Latency Freeze — Vòng lặp 3-5 phút):** Egress tự động retry nhiều lần khiến mỗi lượt ReAct tốn 40-60s, kéo dài phiên làm việc lên hàng phút làm Operator ức chế.

---

## 3. Bản Thiết Kế Đồng Thuận Cuối Cùng (Final Unified Architecture)

### A. Nguyên Tắc Cốt Tử: Tách Biệt "Khẳng Định (Assertion)" và "Tiến Trình (Progress)"
- **Khẳng định thị giác (Assertion):** Fail-closed tuyệt đối. Mọi screen-claim bắt buộc phải gắn với Receipt hợp lệ do Tool Wrapper ký HMAC.
- **Tiến trình (Progress):** Luôn tiến (Zero-Waiting-State). Không bao giờ có trạng thái `BLOCKED`, `WAITING_OPERATOR` hay đòi hỏi token mở khóa.

### B. Shift-Left vào Tool Wrapper
- Mọi UI tool (`computer_use`, `playwright`, `gpm`, `adb`) tự động thực thi chuỗi: **Action -> Capture -> WinRT OCR -> Sinh Receipt** ngay bên trong wrapper tool.
- Ngân sách: <= 15s, tối đa 1 retry nội tuyến.
- Wrapper trả về:
  ```json
  {
    "receipt_id": "rec_<sha8>_<ts>",
    "device_id": "m1",
    "cdp_port": 53400,
    "action_ts": 1792470000.0,
    "sha256": "...",
    "ocr_status": "OK",
    "ocr_raw_text": "...",
    "evidence_tokens": ["gpt", "4o", "canvas"]
  }
  ```

### C. Scope-Guard tại Egress (Zero False Positives & Zero Latency)
- Egress Filter CHỈ kích hoạt khi lượt đó có gọi ít nhất 1 UI tool (`is_ui_turn`).
- Các lượt chat, thảo luận code, review thuần túy: **Bypass 100%**, không đòi hỏi receipt hay ảnh.
- Egress chỉ tra cứu và đối soát Receipt sẵn có (mili-giây), **Retry ở Egress = 0**, không tự chụp lại, triệt tiêu bẫy ngâm trễ 3-5 phút.

### D. Zero-Whining by Structure (Triệt Tiêu Khóc Lóc Bằng Cấu Trúc)
- Ở nhánh lỗi / thiếu bằng chứng / OCR không khớp: **TƯỚC HOÀN TOÀN QUYỀN SINH VĂN XUÔI CỦA LLM**.
- Hệ thống tự động render template cố định máy sinh:
  `Trạng thái: DEGRADED | Mã: <CODE> | Thiết bị: <id> | Bằng chứng cuối: <receipt_id> | Việc tiếp theo: <action>`
- LLM không có ô văn xuôi nào để nhả văn than vãn, xin xỏ hay phân trần.

---

## 4. Phán Quyết Reviewer & Danh Mục Lỗ Hổng Cần Khóa Cứng (P0 / P1)
Claude Sonnet 5.5 Reviewer thẩm duyệt mã nguồn `guard_media_vision_gate.py` và chỉ ra:
- **P0.1 (ocr_status check):** `_verify_receipt` bắt buộc từ chối nếu `ocr_status in ("TIMEOUT", "FAILED")`. Không chấp nhận receipt rỗng/lỗi làm bằng chứng.
- **P0.2 (OpenAI Tool Call Format):** `_tool_name` phải xử lý cả format nested `call.get("function", {}).get("name")`.
- **P0.3 (Bypass Order):** Kiểm tra file vật lý và SHA-256 của thẻ `MEDIA:` phải chạy TRƯỚC khi cho phép bypass non-UI, ngăn chặn việc chèn MEDIA giả vào tin nhắn chat.
- **P1 (Receipt ID & Sanitization):** Bắt buộc sinh `receipt_id` thật, sanitize `device_id` và `next_action` (cắt tối đa 64 ký tự chống prompt injection).
