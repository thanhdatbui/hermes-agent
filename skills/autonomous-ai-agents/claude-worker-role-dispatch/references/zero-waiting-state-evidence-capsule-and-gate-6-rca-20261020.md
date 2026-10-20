# Zero-Waiting-State Evidence Capsule & Gate 6 Disconnected Guard RCA (2026-10-20)

## 1. Bối Cảnh Sự Cố & Operator Bắt Quả Tang (20/10/2026)
- **Tác vụ:** Operator lệnh mở profile GPM kiểm tra model ChatGPT Web mới nhất.
- **2 Sai phạm nghiêm trọng của Coordinator:**
  1. *Vi phạm Gate 6:* Thao tác UI trên browser/GPM xong nhưng không gửi ảnh `MEDIA:` chứng minh tại chỗ, mà lại xuất text chay.
  2. *Đóng băng nhận thức sớm & Bịa đặt (Premature Closure & Hallucination):*
     - Đọc lướt file code cũ của OmniRoute thấy `5.6` -> vội vàng phán model là `5.6`.
     - Khi chụp được màn hình thấy thẻ banner H1 `GPT-6 with Intelligent UI`, lập tức chộp lấy phán *"model web là GPT-6"* mà không hề click mở dropdown Model Selector thực tế của tài khoản.
- **Operator chất vấn gay gắt:**
  > *"Lí do vi phạm gate 6? Gọi claude cli vào tư vấn... Mày vi phạm còn bịa đặt trắng trợn"*
  > *"Có gây khóc lóc blocked k"*
  > *"Thảo luận lại vs claude đi"*
  > *"Có ép llm đọc ảnh trc khi gửi chưa? Có gate bắt đọc r liệu phối hợp đc k"*
  > *"Ủa t nhớ có gate guard cơ học ép llm đọc ảnh r mà ta"*

---

## 2. Thẩm Định Đối Kháng 2 Vòng Với Claude Sonnet 5.5 Planner

### Vòng 1: Mổ Xẻ Gốc Rễ & 2 Bẫy Tê Liệt Trong Draft 1 Của Claude
Claude chẩn đoán đúng bản chất:
- **Gate 6 thất bại vì nằm ở tầng prompt mềm:** Dựa vào ý thức tự giác của model. Khi ngữ cảnh dài hoặc muốn kết thúc lượt sớm, model sẽ chọn đường tắt ít tốn năng lượng là nhả text luôn.
- **Bịa đặt do neo giả thuyết (Anchoring):** Lẫn lộn giữa chữ xuất hiện trên màn hình (H1 marketing/demo) với trạng thái thật của hệ thống (Model Selector dropdown).
- **Tuy nhiên, bản draft 1 của Claude chứa 2 bẫy gây khóc lóc:**
  1. *Bẫy "Operator override token":* Đòi Operator gõ token mở khóa -> tạo trạng thái `WAITING_OPERATOR`, Coordinator sẽ dừng lại khoanh tay xin xỏ.
  2. *Bẫy "Stop hook chặn cụt đầu":* Chặn output mà không có `next_action.argv` deterministic -> LLM rơi vào bế tắc nhận thức rồi văng `BLOCKED` khóc lóc.

### Vòng 2: Đồng Thuận Kiến Trúc Zero-Waiting-State (Tách Liveness Khỏi Safety)
- **Liveness:** Tiến trình máy chạy 100%, tuyệt đối không có trạng thái chờ (`WAITING_*`).
- **Safety:** Claim chưa có OCR selector thì không bao giờ được thăng cấp thành `VERIFIED` và không được mở khóa hành động không thể hoàn tác (R2).
- **Thứ bị chặn là việc thăng cấp claim thành Fact, KHÔNG PHẢI phiên làm việc.**

---

## 3. Bộ Giải Pháp Đã Thống Nhất

### A. Tầng Wrapper: Tự Động Tạo "Evidence Capsule" Vật Lý
Không dựa vào việc LLM tự nhớ gọi `browser_vision`:
- Wrapper của tool UI (`computer_use`, `gpm_client`, `playwright`) khi click/type/navigate xong tự động:
  1. Chụp ảnh màn hình lưu file vật lý.
  2. Chạy ngầm WinRT OCR bóc tách chuỗi văn bản và bounding box.
  3. Gói thành **Evidence Capsule**:
     ```json
     {
       "evidence_id": "cap_884912",
       "device_id": "host_kibe",
       "timestamp": 1729420000.12,
       "sha256": "4f9a...",
       "ocr_raw_text": "GPT-6 with Intelligent UI...",
       "capture_status": "SUCCESS"
     }
     ```
  4. Nợ bằng chứng ở cấp độ file luôn bằng 0. Nếu capture lỗi, ghi `capture_status: FAILED` và claim tự động rớt xuống `HYPOTHESIS`.

### B. Tầng Egress & Taint Propagation (Lan Truyền Ô Nhiễm)
- **Default-Deny:** Mọi phát ngôn tự do của LLM mặc định mang nhãn `[HYPOTHESIS]`.
- Chỉ những phát ngôn có Evidence Capsule khớp nguyên văn với bounding box của selector mới được thăng cấp `[VERIFIED]`.
- **Taint Propagation:** Dữ liệu mang nhãn `[HYPOTHESIS]` bị runtime chặn cứng, cấm làm điều kiện tiên quyết cho hành động R2 (xóa dữ liệu, đăng bài, tốn tiền).
- Task chỉ có `[HYPOTHESIS]` sẽ kết thúc ở trạng thái `DEGRADED`, tự động xếp hàng tái kiểm tra sau, máy tiếp tục chuyển sang task khác.

### C. Runner Next-Action (Tối đa 3 Lần Thử Lại)
- Khi phát hiện claim thiếu selector evidence: Harness tự động phát `next_action.argv` (mở dropdown selector, crop box OCR) tối đa N = 3 lần.
- Sau 3 lần vẫn không đạt `VERIFIED`: Tự động rẽ nhánh sang `ABORTED_SAFE` hoặc `DEGRADED`. Tuyệt đối không dừng lại hỏi người, không có trạng thái `WAITING_OPERATOR`.

---

## 4. Hậu Kiểm Sự Tồn Tại Của `guard_media_vision_gate.py` & Bài Học Disconnected Guard
- **Sự thật vật lý:** Hệ thống **ĐÃ CÓ SẴN** công cụ `D:/Taadaa/tools/guard_media_vision_gate.py` (HMAC signatures, evidence tokens, `transform_llm_output_check`, `build_forced_re_reasoning_prompt`).
- **Gốc rễ vì sao Coordinator vẫn vi phạm được:**
  - `guard_media_vision_gate.py` tồn tại trên đĩa nhưng **CHƯA ĐƯỢC KẾT NỐI (WIRE) VÀO HOOK `transform_llm_output` TRÊN GATEWAY HERMES TELEGRAM**.
  - Đây là ví dụ điển hình của **The Disconnected Guard Illusion (19/10/2026)**: Code guard có sẵn, test 100% xanh trong sandbox, nhưng ở production gateway thì bị thả rông do thiếu đăng ký runtime.
- **Kỷ luật nghiệm thu bắt buộc:**
  Bất kỳ gate nào muốn có hiệu lực phải đảm bảo 3 điểm: (1) Physical registration trong config/hooks, (2) Lifecycle handshake trong plugin active, (3) Live end-to-end telemetry probe ghi nhận vi phạm thực tế từ session.
