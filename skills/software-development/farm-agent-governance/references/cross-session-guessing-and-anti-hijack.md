# Anti-Blind Session Guessing & Cross-Session Hijack Prevention

## 1. Bản chất sự cố (Root Cause)

Trong môi trường điều phối đa luồng / đa phiên (Telegram forum topics, multi-session gateway):
- Người dùng thường xuyên chuyển qua lại giữa các topic khác nhau (ví dụ: topic "Sổ tay bệnh án", topic "Tiến độ đăng video", topic "Lưu trữ Google Drive").
- Khi người dùng gửi một tin nhắn ngắn, mơ hồ hoặc thể hiện thắc mắc/bức xúc (ví dụ: `??? Clmm`, `sao v`, `ủa`, `làm chưa`):
  * **Cạm bẫy:** Agent Coordinator tự tiện chạy `session_search(limit=3)` hoặc `session_search(sort="newest")` để quét các session hoạt động gần nhất trong database.
  * **Hậu quả:** Agent bốc trúng tiêu đề hoặc nội dung của một session CŨ ở topic khác vừa chạy cách đó vài phút/vài tiếng (ví dụ: lấy chuyện Google Drive bỏ vào topic Sổ tay bệnh án).
  * Agent bắt đầu tự hăng hái phân tích, tư vấn kiến trúc, thậm chí chuẩn bị chạy script can thiệp vào chủ đề cũ đó.
  * Người dùng bị dắt đi một vòng, bực bội vì "ông nói gà bà nói vịt": *"Clmm ngáo chó vl session này t hỏi cái khác mà"*.

---

## 2. Quy tắc phòng chống tuyệt đối (Anti-Blind Guessing Invariant)

1. **CẤM TỰ ĐOÁN CHỦ ĐỀ TỪ SESSION KHÁC:**
   - Khi nhận tin nhắn ngắn (< 10 từ) hoặc câu hỏi mơ hồ không nêu rõ danh từ/đối tượng kỹ thuật (`???`, `ủa`, `sao v`, `chưa hiểu`):
   - **TUYỆT ĐỐI CẤM** dùng `session_search` để lấy chủ đề của session khác đắp vào session hiện tại.
   - Session hiện tại chỉ có thẩm quyền trên lịch sử hội thoại nội tại của CHÍNH NÓ (`thread_id` / context hiện hành).

2. **HÀNH ĐỘNG CHUẨN KHI THIẾU NGỮ CẢNH:**
   - Hỏi lại trực diện, ngắn gọn trong 1-2 câu:
     *"Em chưa rõ ý anh ở tin nhắn này, anh đang muốn xử lý / kiểm tra hạng mục nào ạ?"*
   - Không tự suy diễn, không tự dựng bối cảnh giả lập từ session cũ.

3. **SESSION_SEARCH CHỈ DÙNG KHI CÓ TỪ KHÓA RÕ RÀNG:**
   - `session_search` chỉ được phép kích hoạt khi người dùng CÓ NHẮC TỚI một từ khóa, sự kiện hoặc mốc thời gian cụ thể trong quá khứ (ví dụ: *"hôm qua fix bug Wi-Fi máy 7 thế nào"*, *"lần trước trần follow máy 8 là bao nhiêu"*).
   - Tuyệt đối cấm chạy discovery rỗng (`session_search()`) rồi tự ý bốc session đầu tiên làm mục tiêu hành động.
