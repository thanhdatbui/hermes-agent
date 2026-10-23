# Kỷ Luật Khóa Cứng 100% On-Demand Cho Advisor Sol & Triệt Tiêu Hoàn Toàn Tự Động Chen Ngang

## 1. Bài học từ phản hồi và bức xúc thực tế của Operator (2026-10-24)
- **Hiện tượng:** Operator phàn nàn gay gắt: *"Tại sao cứ tự gọi advisor sol v t fix mấy lần đéo cho gọi mặc định nx r mà chỉ có t yêu cầu ms đc gọi mà. Tắt advisor mặc định đi. Chỉ đc on demand thôi. Mà vì sao phải xoá từng từ nhỉ sao k xoá luôn cái gate mặc định gọi advisor ấy. Chỉ giữ lại khi nào t yêu cầu gọi advisor gọi sol ms đc gọi kiểu kiểu v"*.
- **Nguyên nhân gốc rễ (Lỗi vá nửa vời):**
  - Mặc dù quy tắc trong prompt và tài liệu ghi là "On-Demand", nhưng trong code lõi `agent/conversation_loop.py`, hàm `_is_advice_request()` vẫn lưu giữ danh sách các từ ngữ suy đoán:
    `"tư vấn"`, `"lời khuyên"`, `"có nên"`, `"theo mày"`, `"đánh giá"`, `"phân tích giúp"`, ...
  - Nguy hiểm hơn, code vẫn giữ nhánh logic regex kiểm tra từ `"nên"` kết hợp với dấu hỏi `"?"`:
    `if has_phrase("nên") and ("?" in text or ...)`
  - Khi Operator gửi các câu hỏi kỹ thuật thông thường (ví dụ: *"Ý là canary xem cron có fix đc k ?"*), hệ thống bắt nhầm dấu hỏi và từ ngữ, tự ý kích hoạt ngầm Advisor Sol và chèn khối `--- Advisor (Sol / review) ---` vào Telegram, làm loãng hội thoại và chậm tiến độ.
  - Sai lầm trước đây: Cố gắng ngồi lọc từng từ đen (blacklist). Tiếng Việt rất đa dạng, lọc từ này thì câu hỏi khác vẫn dính dấu hỏi `?`.

## 2. Kỷ luật kiến trúc bất biến (Authoritative Invariant)
1. **XÓA BỎ HOÀN TOÀN CƠ CHẾ ĐOÁN Ý & DẤU HỎI `?`:**
   - CẤM TUYỆT ĐỐI kiểm tra dấu hỏi `?` hay `？`.
   - CẤM TUYỆT ĐỐI kiểm tra các từ ngữ suy đoán thông thường (`nên`, `có nên`, `tư vấn`, `đánh giá`, `theo mày`, `phân tích giúp`).
2. **KHÓA CỨNG CÔNG TẮC ON-DEMAND DUY NHẤT BẰNG LỆNH ĐÍCH DANH:**
   - Cổng `_is_advice_request(message)` chỉ được phép mở (trả về `True`) khi và chỉ khi tin nhắn chứa một trong các cụm từ chỉ định rõ ràng:
     ```python
     _ADVISOR_EXPLICIT_TRIGGERS = (
         "gọi advisor",
         "hỏi sol",
         "gọi sol",
         "sol thấy sao",
         "nhờ sol review",
         "sol lên plan",
     )
     ```
   - Mọi câu hỏi khác của Operator (dù có từ "nên", "tư vấn" hay dấu hỏi chấm): Cổng trả về `False` ngay lập tức $\rightarrow$ Coordinator trực tiếp trả lời dứt khoát, không delay, không ngắt lời.
