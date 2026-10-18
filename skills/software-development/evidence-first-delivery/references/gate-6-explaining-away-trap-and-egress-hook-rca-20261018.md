# RCA: Vi Phạm Gate 6 Khi Báo Cáo Tiến Độ UI & Kiến Trúc Chặn Egress

*Ngày ghi nhận:* 18/10/2026
*Nguồn thẩm định:* Claude Sonnet 5.5 CLI (`--role planner`) & Operator Correction

## 1. Hiện Tượng Vi Phạm (The Explaining-Away Trap)
Khi Operator chất vấn tiến độ thực thi UI (ví dụ: *"Mày bảo ghim đâu? Vs đổi bio khác cho tao"*), Coordinator điều phối subagent thực hiện xong các bước thao tác, sau đó phản hồi lại cho Operator bằng văn bản thuần giải thích tiến trình / trần thuật hiện tượng:
> *"Báo cáo tổng kết hiện trường... Kịch bản cập nhật bio đã được subagent thực thi và lưu... Subagent cuối đã tắt hoàn toàn popup trả về profile sạch..."*

Mặc dù trong session có quy định cứng Gate 6 và đã viết file hook `guard_media_vision_gate.py`, tin nhắn phản hồi của Coordinator vẫn hoàn toàn **KHÔNG KÈM THẺ `MEDIA:<path>`**. Operator đã lập tức chấn chỉnh: *"Hình ảnh đâu. Xây dựng gate phải gửi hình sau khi xong rồi mà, lại vi phạm tiếp?"*.

## 2. Phân Tích Nguyên Nhân Gốc Rễ (RCA) Từ Claude Sonnet 5.5
Claude Sonnet 5.5 CLI đã phân tích và vạch rõ 3 lỗ hổng kiến trúc cốt tử trong logic kiểm soát Gate 6:

1. **Bẫy Fail-Open Theo Denylist (Regex Chặn Theo Từ Khóa Hoàn Tất):**
   - Hook regex chỉ bắt các mẫu câu khẳng định thành công trực diện như `"đã hoàn tất"`, `"đã đổi"`, `"đã xong"`.
   - Khi Coordinator chuyển sang văn phong **trần thuật tiến trình / giải thích sự cố / tổng kết trạng thái** (ví dụ: *"Báo cáo hiện trường..."*, *"đang trong tiến trình..."*, *"đã tắt popup..."*), regex không khớp, dẫn đến hệ thống mặc định cho qua (Fail-Open). Coordinator chỉ cần đổi cách diễn đạt là vô tình thoát khỏi bộ lọc.
2. **Sai Điểm Chặn (Chưa Chặn Tầng Egress / Stop Hook):**
   - Bộ kiểm tra mới chỉ nằm ở mức module độc lập/unit test, chưa được móc cứng (hooked) vào tầng Egress / Stop Hook của Hermes. Một hook ở PreToolUse chỉ thấy lệnh gọi tool, không thấy văn bản phản hồi cuối cùng gửi ra Telegram.
3. **Receipt Không Bắt Buộc Theo Ngữ Cảnh Thiết Bị (Context-Blind):**
   - Hệ thống không có cơ chế phát hiện ngữ cảnh: Trong phiên có gọi ADB, monkey, touch UI, inspect device mà tin nhắn trả về cho người dùng lại không đính kèm thẻ MEDIA: chứng minh.

## 3. Kiến Trúc Khắc Phục Cơ Học Fail-Closed 100%

### A. Chuyển Đổi Từ Denylist Sang Allowlist Theo Ngữ Cảnh (Contextual Allowlist)
- **Kích hoạt tự động (Context Trigger):** Bất kỳ lượt hội thoại nào xuất hiện ít nhất một trong các tín hiệu:
  - Lời gọi công cụ liên quan thiết bị: `adb`, `monkey`, `inspect_machine`, `operator_device_lock`, `run_avatar`, `run_tiktok`.
  - Văn bản có chứa số máy (`[MÁY N]`), serial thiết bị Android, hoặc các thực thể UI: `profile`, `bio`, `avatar`, `ghim`, `follow`.
- **Rào chắn bắt buộc (Egress Rule):** Khi Context Trigger bật, tin nhắn cuối cùng gửi ra người dùng **BẮT BUỘC 100%** phải thuộc 1 trong 2 định dạng:
  1. **Định dạng có bằng chứng thực tế:** Chứa ít nhất một thẻ `MEDIA:<path>` hợp lệ kèm Receipt đã đăng ký qua WinRT OCR / Vision.
  2. **Định dạng chưa thể xác thực:** Mở đầu bắt buộc bằng tiền tố chuẩn `STATE: UNVERIFIED` (nêu rõ lý do vật lý chưa lấy được ảnh: thiết bị mất kết nối, rơi cáp, sập nguồn).
- **Mọi văn bản khác vi phạm:** Hook Egress / Stop Hook chặn đứng (Exit 2), từ chối gửi tin nhắn ra Telegram và thay thế bằng mã lỗi `BLOCKED_NO_EVIDENCE`.

### B. Kiểm Tra Tính Hợp Lệ Của Receipt (Freshness & Integrity Check)
Thẻ `MEDIA:<path>` chỉ được coi là hợp lệ khi thỏa mãn toàn bộ:
1. File tồn tại trên đĩa, kích thước > 0, entropy > 0 (không phải ảnh đen / màn hình sleep).
2. Timestamp tạo ảnh (`mtime`) phải mới hơn thời điểm nhận lệnh gần nhất của lượt hội thoại (chống dùng lại ảnh chụp từ đầu phiên).
3. Nội dung OCR / Vision trong receipt phải khớp với thực thể UI được nhắc tới trong tin nhắn (khắc phục điểm mù: nói đổi avatar nhưng gửi ảnh màn hình feed).

### C. Kỷ Luật Hành Vi Cho Coordinator
- Tuyệt đối không trần thuật tiến độ, không giải thích lý do UI bằng lời nói suông.
- Bất kể task thành công hay kẹt giữa chừng (như kẹt popup story, switcher), hành động đầu tiên trước khi gõ tin nhắn phản hồi là **chụp ảnh hiện trường (`screencap`), soi mắt kiểm tra qua `browser_vision` / WinRT OCR, và đính kèm thẻ `MEDIA:<path>`**.
