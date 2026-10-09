# Dual-Channel Advisor & Conversational Intent Routing

## 1. Bối cảnh & Yêu cầu cốt lõi từ Người dùng (05/10/2026)

Người dùng chỉ thị rõ ràng:
1. **Cả 2 đối tượng đều cần Advisor**: Advisor không chỉ đóng vai trò trợ lý ngầm cho Coordinator khi gặp ngã rẽ khó, mà còn phải **tư vấn trực tiếp cho Người dùng** khi người dùng đặt câu hỏi/xin tư vấn.
2. **Loại bỏ thao tác chat thủ công với Sol**: Thay vì Người dùng phải tự mở chat riêng gọi Sol Web High để hỏi ý kiến thứ hai, Hermes Agent bắt buộc phải tự động cung cấp **câu trả lời của Model chính (Gemini) kèm góc nhìn của Advisor (Sol High qua combo `review` :20129)** trong cùng một lượt phản hồi.
3. **Phân biệt rạch ròi Lệnh thi công vs Câu hỏi tư vấn**: Tuyệt đối không gọi Advisor cho các câu lệnh vận hành thường ngày để tránh chậm trễ (15–30s latency overhead).

---

## 2. Mô hình Cố vấn 2 Kênh (Dual-Channel Architecture)

```text
                           [User Input]
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
[Mệnh lệnh vận hành / code]                    [Câu hỏi / Xin tư vấn]
("chạy script", "sửa file", ...)               ("nên làm gì?", "tư vấn giúp", ...)
        │                                               │
        ▼                                               ▼
[Coordinator - Gemini]                         [Coordinator - Gemini]
(T0/T1 tự làm, T2 giao Worker)                 (Tự suy luận câu trả lời chính)
        │                                               │
(Gặp decision point khó: lock,                          ▼
 cookie, conflict evidence)                    [Auto-Invoke Advisor Hook]
        │                                      (Trích xuất câu hỏi + primary answer)
        │                                               │
        ▼                                               ▼
[Tool: advisor_consult]                        [Combo `review` trên :20129]
(Kênh 1: In-Loop Copilot)                      (Sol Web High -> Terra Codex)
        │                                               │
        ▼                                               ▼
(Nhận advice ngầm, Coordinator                 [Kênh 2: Dual-Perspective Response]
 tiếp tục trajectory & thi công)               "Primary Answer
                                                --- Advisor (Sol / review) ---
                                                <Góc nhìn kiến trúc của Sol>"
```

---

## 3. Quy chuẩn Phân loại Ý định (Intent Classification Contract)

Trong `agent/conversation_loop.py`:

### A. Non-Advice Markers (Mệnh lệnh thi công / Vận hành -> FALSE)
- Các động từ hành động dứt khoát: `chạy script`, `sửa file`, `kiểm tra log`, `đăng ký`, `upload`, `restart`, `làm đi`, `chốt phiên`, `commit`, `push`.
- Tin nhắn rỗng hoặc chỉ chứa tham số / code block / JSON.
- **Hành vi**: Coordinator xử lý bình thường, **0 gọi Advisor**.

### B. Advice Markers (Câu hỏi / Tư vấn -> TRUE)
- Dấu hỏi: `?`, `？`.
- Từ khóa tư vấn tiếng Việt: `tư vấn`, `lời khuyên`, `nên`, `có nên`, `theo mày`, `đánh giá`, `phân tích giúp`, `ý kiến`.
- Từ khóa tiếng Anh: `what should`, `should i`, `advise me`, `how do you recommend`.
- **Hành vi**: Kích hoạt bộ ghép nối câu trả lời kép (Dual Composition).

---

## 4. Ranh giới Ghép nối An toàn (Safety & Boundary Invariants)

1. **One-Call Cap per Turn**:
   - Biến cờ `advisor_consulted = True` được khởi tạo đầu turn và sống suốt vòng lặp. Bắt buộc chỉ gọi Advisor **đúng 1 lần duy nhất** tại biên `final_response` trước khi trả kết quả ra ngoài.
   - Tuyệt đối không gọi trong các vòng lặp công cụ trung gian (intermediate tool iterations) hay synthetic continuations.
2. **Preserve Primary Answer**:
   - Nếu Advisor trả về `status: "ok"`: Ghép nối rõ ràng:
     ```text
     <Câu trả lời của Model chính>

     --- Advisor (Sol / review) ---
     <Khuyến nghị & phân tích kiến trúc của Sol>
     ```
   - Nếu Advisor timeout (>30s) hoặc lỗi mạng: Giữ nguyên câu trả lời chính và ghi chú súc tích:
     ```text
     <Câu trả lời của Model chính>

     Advisor: unavailable (primary answer shown)
     ```
   - CẤM làm hỏng hoặc xóa câu trả lời của Model chính vì lỗi từ phía Advisor.
3. **No Approval / Read-Only**:
   - Lời khuyên của Advisor mang tính tham khảo (recommendation), không phải là hành động hay phê duyệt (approval). Coordinator và User toàn quyền quyết định.
4. **Sanitization Trước Khi Gửi**:
   - Lọc sạch toàn bộ secrets, passwords, cookies, tokens (`sk-`, `ghp-`, `xox-`, `Bearer`) trước khi chuyển tới endpoint `:20129`.

---

## 5. Bài học Kiểm định Canary (Canary Gate Lesson)

- **Cạm bẫy**: Chỉ import và chạy trực tiếp hàm adapter `advisor_consult()` bằng Python script độc lập là **CHƯA ĐỦ** để kết luận Canary Pass. Cách đó chỉ chứng minh kết nối mạng tới endpoint `:20129`, chưa chứng minh Hermes runtime đang chạy đã nạp tool và cơ chế agent loop đã hoạt động.
- **Quy chuẩn Canary bắt buộc**:
  1. Phải kiểm tra qua Tool Dispatcher của Hermes: `model_tools.handle_function_call("advisor_consult", ...)` để chứng minh registry nhận diện được tool và dispatch đúng.
  2. Phải kiểm tra qua luồng tổng thể `conversation_loop.py` với câu lệnh kiểm tra intent thật (Command -> False, Advice -> True).
  3. Bắt buộc đối soát log thật và latency thật từ OmniRoute.
