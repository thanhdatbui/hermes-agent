# Gate 6 Mechanical Hook Architecture & Anti-Whining Invariants

## 1. Bối Cảnh Sự Cố & Vấn Đề Cốt Lõi
- **Sự cố:** Coordinator thực hiện pin video trên máy thật, chụp màn hình, gọi `browser_vision` soi mắt nội bộ thành công nhưng khi xuất câu trả lời cho User lại QUÊN đính kèm thẻ `MEDIA:<path>`, chỉ báo mồm "đã pin xong 8.856 view".
- **Hệ quả:** Vi phạm nghiêm trọng Gate 6 (Visual Evidence Invariant) — User nhận câu trả lời không có bằng chứng trực quan thực tế.
- **Rào cản thiết kế cũ:** Trong codebase có sẵn `guard_media_vision_gate.py` với logic `transform_llm_output_check()` nhưng là dead-code (chưa bao giờ được wire vào runtime). Nếu wire nguyên bản, logic này đòi hỏi chữ ký HMAC trong `vision_receipts.jsonl` và throw câu mắng tự do, khiến Agent bị kẹt vào vòng lặp xin lỗi / phân trần / bại liệt (whining loop).

## 2. Giới Hạn Kiến Trúc Hook Của Hermes Agent
- Hermes Agent **chỉ hỗ trợ 2 loại Shell Hook**:
  1. `pre_tool_call` (chạy trước khi gọi tool)
  2. `post_tool_call` (chạy ngay sau khi tool thực thi)
- **Hermes KHÔNG CÓ hook chặn free-text message cuối cùng** (không có event `Stop` hay `on_message` như Claude Code).
- Do đó, nếu Coordinator chỉ gõ text gửi User mà không gọi thêm tool nào, hook runtime không thể bắt được nội dung text đó để chặn trực tiếp.

## 3. Kiến Trúc Hai Điểm Chốt Chặn Kép (Dual-Point Enforcer)
Để giải quyết triệt để vấn đề báo mồm mà không phụ thuộc vào ý thức tự giác của LLM:

### Điểm A: Tự Động Ký Receipt Tại `post_tool_call` (Automatic Evidence Capture)
- **Matcher:** `computer_use|adb|gpm|inspect_machine|browser`
- **Cơ chế:** Ngay khi một lệnh thao tác UI hoặc lệnh ADB/browser kết thúc:
  1. Hook tự động kích hoạt chụp màn hình screencap (nếu tool chưa chụp).
  2. Tự động chạy WinRT OCR đối soát và tạo HMAC-signed receipt vào `D:/Taadaa/runtime/audit_logs/vision_receipts.jsonl`.
  3. Ghi nhận trạng thái `UNVERIFIED` hoặc `VERIFIED_SUCCESS` vào ledger `gate6_state.jsonl`.

### Điểm B: Chốt Chặn Hành Động Tiếp Theo Tại `pre_tool_call` (Downstream Barrier)
- **Matcher:** `terminal|clarify`
- **Cơ chế:** Trước khi cho phép Coordinator chạy các lệnh chốt phiên (`git push`, `closeout_gate.py`) hoặc gọi `clarify` để lảng tránh:
  1. Hook đọc ledger `gate6_state.jsonl`.
  2. NẾU turn trước có thao tác UI mà trạng thái receipt chưa đạt `VERIFIED_SUCCESS` hoặc thiếu file ảnh hợp lệ trên đĩa:
     👉 **FAIL-CLOSED CHẶN ĐỨNG TOOL NGAY LẬP TỨC**.

### Điểm C: Watchdog Hậu Kiểm Tự Động (Asynchronous Compliance Watchdog)
- Tích hợp vào `gate_compliance_watchdog.py` (chạy cron định kỳ mỗi 6 giờ).
- Tự động quét log tin nhắn Telegram gần nhất và đối soát với `vision_receipts.jsonl`. Nếu phát hiện câu claim hoàn tất mà không có thẻ `MEDIA:` hợp lệ, ghi lỗi vi phạm vào `gate_audit.jsonl` và khóa quyền chốt phiên tiếp theo.

## 4. Invariants Chống Khóc Lóc & Chống Bại Liệt (Anti-Whining & Anti-Paralysis Rules)

| Tình Huống | Cơ Chế Cũ (Gây Bại Liệt) | Cơ Chế Chuẩn Mới (Chống Khóc Lóc) |
|---|---|---|
| **Thông báo lỗi khi bị chặn** | Ném câu mắng tự do: *"Your previous message was blocked... Re-reason..."* khiến LLM phân trần, xin lỗi. | **Template cố định 1 dòng (`render_degraded_template`):**<br>`Trạng thái: DEGRADED \| Mã: MISSING_MEDIA \| Thiết bị: M<N> \| Bằng chứng: None \| Việc tiếp theo: DROP_CLAIM hoặc RECAPTURE` |
| **Giới hạn số lần thử lại** | Vòng lặp vô hạn nếu không tìm được ảnh | **Hard Bound $O(1)$:** `attempt >= 3` hoặc `elapsed > 30s` $\to$ Cưỡng chế chuyển sang **`ESCALATE_L3_BLOCKED`**, dừng vòng lặp ngay lập tức. |
| **Tiêu chí kiểm tra ảnh** | Bắt bẻ cấu trúc token phức tạp, dễ false positive | **Tiêu chuẩn cơ học thuần túy:**<br>1. File vật lý tồn tại, size $\ge 1\text{KB}$, đúng định dạng PNG/JPG/WEBP.<br>2. WinRT OCR quét không dính veto keywords (`Error`, `Failed`, `Thất bại`, `Màn hình đen`, `Launcher`).<br>3. Khớp từ khóa thành công (nhãn Ghim, tên mới...). |
| **Hành vi Agent khi bị từ chối** | Viết văn giải thích dài dòng | **Hành động cơ học tức thì:** CẤM xin lỗi. Chỉ được chọn 1 trong 2: (A) Bỏ câu khẳng định chưa chứng minh, hoặc (B) Thực hiện lệnh screencap/pull ảnh để lấy bằng chứng thật rồi mới báo cáo. |
