# Tri-Advisor Governance & Mechanical Prompt Protocol (2026-11-03)

## 1. Cơ Chế Triệu Tập Đầy Đủ Hội Đồng 3 Cố Vấn (Tri-Advisor Mandate)
- Khi User yêu cầu Advisor tham vấn sự cố, kiến trúc hoặc review hậu thi công, Coordinator BẮT BUỘC triệu tập đầy đủ **3 Cố vấn**:
  1. **Sol Web** (`gpt-5.6-sol-high` qua `:20129`) — reasoning effort: **`extended`** (tương đương `high`).
  2. **Gemini Web** (`gemini-web-argon-pool` qua `:20129`) — giao thức Protobuf `StreamGenerate`, reasoning slot `[17] = [[2]]` (**`standard` / `medium`**).
  3. **Claude CLI** (Sonnet / Antigravity CLI) — reasoning effort: **`high`** (Devil's Advocate độc lập).
- Lệnh gọi tiêu chuẩn độc lập:
  ```bash
  python D:/Taadaa/tools/consult_advisor.py -a all -q "<nội dung>" -c "<bối cảnh>"
  ```

---

## 2. Kỷ Luật Chống Over-Engineering & Chống Bại Liệt / Khóc Lóc
- **Invariant Prompting:** Mọi prompt gửi Hội Đồng Cố Vấn BẮT BUỘC phải mở đầu bằng câu lệnh khóa kỷ luật:
  `"KỶ LUẬT BẮT BUỘC: KHÔNG over-engineer, KHÔNG gây bại liệt, KHÔNG khóc lóc/phàn nàn. Tập trung giải pháp O(1) thực dụng."`
- **Mục đích:** Ngăn chặn việc Advisor lan man lý thuyết, đẻ thêm cờ hay module rác, hoặc phàn nàn đổ lỗi cho hạ tầng mà không đưa ra exact diff $O(1)$.

---

## 3. Bản Chất Sự Cố Gemini Web Ngậm Token Trên OmniRoute
- **Hiện tượng:** Cổng `gemini-web-argon-pool` bị rớt phản hồi hoặc ngậm connection kéo dài (>90s) khiến ThreadPool client timeout.
- **Nguyên nhân cốt lõi trong OmniRoute (`openai-to-gemini.ts`):**
  - Khi client không truyền `reasoning_effort` hoặc truyền `"auto"`, translator của OmniRoute tự động inject `defaultThinkingBudget: 8192` hoặc `24576` vào payload gửi lên Google.
  - Google backend bị ép số token suy luận cố định, model không co giãn linh hoạt mà ngậm socket sinh chuỗi reasoning dài, dẫn đến timeout ở client.
- **Giải pháp:** Trong `consult_advisor.py`, luồng gọi Gemini Web cần bọc timeout độc lập và xử lý fallback cleanly, không làm nghẽn 2 cố vấn còn lại.

---

## 4. Bẫy Deferred Emission Gate 6 & Chốt Chặn Cơ Học O(1)
- **Bẫy dồn lô (Deferred Aggregation):** Chụp ảnh lưu đĩa nhưng dồn thẻ `MEDIA:<path>` về cuối lượt -> Chạm trần `Tool-calling iterations limit reached` -> Platform ép tóm tắt khẩn cấp -> Mất thẻ `MEDIA:` -> Vi phạm Gate 6.
- **Khắc phục:**
  1. Thao tác UI nào sinh ảnh thì ngay turn đó xuất thẻ `MEDIA:` kèm WinRT OCR.
  2. Khóa cứng budget Canary `<= 5 tool calls`, cấm mở rộng scope sang máy khác ngoài target.

---

## 5. Kỷ Luật Thi Công Code & Review Thẩm Định (Anti-Code-Golf)
- **Cấm Code-Golfing:** Khi giảm line count để lọt qua Architecture Gate (ví dụ `<= 1650` dòng), cấm nén `if-else` thành ternary expression >250 ký tự gây dead-code và gọi hàm trùng lặp.
- **Tương thích Python 3.11:** Dùng dấu nháy kép ngoài, nháy đơn trong cho f-string để tránh lỗi `SyntaxError` trên Python 3.11.15 của Farm.
- **Ưu tiên Clean Code:** Cắt bỏ dòng trống thừa hoặc rút gọn comment thừa trước khi can thiệp vào logic điều kiện.
