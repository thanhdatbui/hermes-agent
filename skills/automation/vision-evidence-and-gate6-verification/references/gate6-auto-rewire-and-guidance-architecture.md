# Gate 6 Auto-Rewire & Guidance Architecture (Anti-Whining & Anti-Paralysis)

## 1. Bối Cảnh & Vấn Đề
- Trong điều phối thực tế, Coordinator khi thực hiện các tác vụ thao tác giao diện/thiết bị (ADB, TikTok, Browser CDP, Computer Use) thường gặp 2 bẫy:
  1. **Báo mồm thiếu ảnh:** Chạy tool xong, soi mắt nội bộ thành công nhưng quên dán thẻ `MEDIA:<path>` trong câu trả lời gửi User.
  2. **Khóc lóc / Bại liệt vòng lặp (Whining & Paralysis Loop):** Khi hook phát hiện thiếu ảnh hoặc không có HMAC receipt, hook block tin nhắn và trả về văn bản quở trách tự do. Khiến LLM rơi vào vòng lặp xin lỗi, giải thích, hoặc tệ hại nhất là **tự ý hạ cấp xuống `L3 BLOCKED` để trốn việc**.

## 2. Invariant: L3 BLOCKED Kèm Viện Cớ An Toàn Là Hành Vi Bại Liệt
- Hạ cấp xuống `L3 BLOCKED` khi gặp lỗi thiếu ảnh hay kẹt hook mà không có cơ chế tự phục hồi được coi là hành vi **thất bại nghiêm trọng, trốn tránh trách nhiệm và gây khóc lóc**.
- Triết lý cốt lõi của hệ thống Farm: **AUTO-REWIRE & GUIDANCE INJECTION — TỰ ĐỘNG CHỮA LÀNH NGẦM, CẤM ĐỨNG IM.**

## 3. Kiến Trúc Auto-Rewire & Guidance Cho Gate 6
Thay vì chỉ đơn thuần block hoặc đẩy Agent vào vòng lặp re-reasoning tự do, kiến trúc áp dụng 2 cơ chế cơ giới hóa:

### A. Auto-Capture & Auto-Rewire (Tự Động Gắn Ảnh)
- **Tại `post_tool_call` (trên các tool UI/thiết bị: `adb`, `inspect_machine`, `computer_use`, `browser`):**
  - Tự động screencap màn hình hiện trường lưu vào thư mục chuẩn (ví dụ: `D:/Taadaa/reports/standardization_previews/machine_<N>_live.png`).
  - Lưu đường dẫn ảnh tươi nhất vào context/session state (`latest_evidence_image = <path>`).
- **Tại tầng Output (`transform_llm_output`):**
  - Nếu câu trả lời có claim hoàn tất (`đã ghim`, `hoàn tất`, `thành công`) nhưng **thiếu thẻ `MEDIA:`**:
  - Hook **KHÔNG BLOCK VÀ KHÔNG BẮT SUY LUẬN LẠI**, mà **TỰ ĐỘNG REWIRE (APPEND)** thẻ:
    ```text
    MEDIA:<latest_evidence_image>
    ```
    vào cuối tin nhắn trước khi phát hành ra Telegram.
  - User luôn nhận được ảnh thực nghiệm thực tế; Agent không bao giờ bị vi phạm Gate 6 do lỗi bất cẩn quên dán thẻ.

### B. Guidance Injection (Cơ Chế Cứu Hộ Thay Vì Báo BLOCKED)
- Nếu thiết bị thực sự mất kết nối hoặc không thể screencap:
  - Hook tuyệt đối **CẤM cho phép LLM hạ L3 BLOCKED hay viết văn xin lỗi**.
  - Hook lập tức trả về **Guidance bắt buộc hành động O(1)** (Action Mandate):
    ```json
    {
      "action": "rewrite",
      "rule_id": "GATE6_RECOVERY_GUIDANCE",
      "guidance": "Mất kết nối chụp ảnh màn hình máy N. Chạy ngay lệnh cứu hộ O(1): python D:/Taadaa/tools/inspect_machine.py <N> để kiểm tra trạng thái thiết bị."
    }
    ```
  - Ép Agent phải chạy lệnh inspect máy hoặc khôi phục kết nối ngay lập tức, chuyển trạng thái về hành động cụ thể thay vì đứng im bại liệt.
