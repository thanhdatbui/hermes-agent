# Mechanical Dual-Answer Enforcement & Stream Deadline Audit (2026-10-10)

## 1. Bài học Chấn chỉnh & Căn nguyên Lỗi Bỏ sót Advisor
Coordinator LLM thường mắc phải 3 thiên kiến nghiêm trọng dẫn đến việc bỏ sót Advisor khi User đặt câu hỏi đánh giá / chiến lược:
1. **Thiên kiến trả lời trực tiếp (Immediate-response bias):** Khi thấy câu hỏi chiến lược, Coordinator lao vào trả lời solo bằng giọng chính mà không phân loại intent.
2. **Né tránh Timeout Waterfall:** Endpoint review Sol Web High (`:20129`) đôi khi bị dính web-pool rate limit hoặc waterfall latency (25–45s). Coordinator "sợ treo phiên" nên tự tiện trả lời một mình mà không kích hoạt fallback tốc độ cao.
3. **Phụ thuộc vào Prompt thay vì Chốt chặn Cơ học (Mechanical Gate):** Nhắc nhở trong prompt luôn bị suy hao theo độ dài context. Muốn triệt tiêu 100% bỏ sót thì phải có chốt chặn code thực thi trước khi gửi câu trả lời cuối.

---

## 2. Tiêu chuẩn Phân loại Ý định (Intent Classification Matrix)

### Phân loại Đúng (Positive - Advice Intent)
- **Câu hỏi nguyên nhân / đánh giá:** `sao nhìn lệch v`, `tại sao không chạy ca tối`, `là sao cứ lệch hoài thế`, `có nên đổi proxy cho máy 62 không`, `đánh giá kiến trúc này giúp tao`, `plan thế nào để xử lý triệt để`.
- **Câu hỏi chiến lược / tương quan:** `theo mày nên dùng cách nào`, `nhìn avatar thế nào có hợp không`, `liệu làm vậy có bị ban nick ko nhỉ?`, `hay là do MikroTik bị rớt mạng?`.
- **Câu hỗn hợp (Compound Intent - Mệnh lệnh + Tư vấn):**
  * `chạy batch rồi cho tao biết nên làm gì` (Có mệnh lệnh ở đầu nhưng vế sau hỏi phương án `nên làm gì` $\rightarrow$ **TRUE**).
  * `git log xem có gì lạ không` (Yêu cầu đánh giá bất thường $\rightarrow$ **TRUE**).
  * `kiểm tra log và phân tích xem nguyên nhân là do đâu` ($\rightarrow$ **TRUE**).

### Loại trừ Nghiêm ngặt (Negative - Imperative & Status)
- **Mệnh lệnh thuần túy:** `chạy batch máy 2`, `sửa file path_resolver.py`, `fix đi đm đừng có lệch nữa`, `làm đi`, `triển khai đi`, `restart gateway`, `upload avatar máy 62`.
- **Hỏi tiến độ / trạng thái hiện trường:** `kiểm tra xem avatar máy 62 sao rồi`, `tiến trình chạy ra sao rồi` (từ khóa `sao rồi`, `sao r` hỏi trạng thái, KHÔNG phải hỏi ý kiến kiến trúc $\rightarrow$ **FALSE**).
- **Phó từ phương thức:** `sửa cái này sao cho nhanh` (`sao cho` là phó từ, không phải hỏi nguyên nhân $\rightarrow$ **FALSE**).
- **Xin phép thực thi mệnh lệnh:** `Đăng ký bù, được không?` (xác nhận lệnh, không phải hỏi lời khuyên $\rightarrow$ **FALSE**).

---

## 3. Kiến trúc Client & Quản lý Thời gian (Deadline Discipline)

### Phân bổ Ngân sách Thời gian (Tổng budget ~35s)
- **Tầng 1 (Sol Web High `:20129 review`):** 18s timeout.
- **Tầng 2 (Sol Fast Fallback `:20129 antigravity/gemini-3.7-flash-high`):** 10s timeout.
- **Tầng 3 (9Router Port `:20128 ag/gemini-2.5-flash`):** 7s timeout.
- **Fail-Safe:** Khi cả 3 tầng timeout/lỗi, trả về `Advisor: unavailable (upstream timeout / pool limits; primary answer shown)`.

### Xử lý Stream & An toàn Dữ liệu
1. **Wall-clock Deadline Abort:**
   Vòng đọc SSE `for line in resp:` bắt buộc kiểm tra `time.time() - t_start > timeout_sec`. Khi vượt hạn, BẮT BUỘC trả về `False, "Wall-clock deadline exceeded"` để kích hoạt fallback sang tầng kế tiếp. **TUYỆT ĐỐI KHÔNG** trả text cụt dở dang coi như thành công.
2. **Lọc Pseudo-200 Usage Limits:**
   Đồng bộ kiểm tra `full_text.startswith("[Error:")` hoặc `"You've hit your limit"` trên **CẢ 3 TẦNG**. Không để thông báo lỗi quota của web pool bị nuốt thành lời khuyên hợp lệ.
3. **Che giấu Dữ liệu Nhạy cảm (Secret Redaction):**
   Trước khi gửi context ra external LLM, tự động lọc sạch API key (`sk-...`), Bearer token, password và credentials bằng hàm `redact_secrets()`.
4. **Giới hạn Độ dài:** Khóa cứng text advice $\le 2500$ ký tự, `tools: []`, `tool_choice: "none"`.

---

## 4. Chốt chặn Cơ học (Mechanical Enforcement Gate)

Sử dụng helper `ensure_dual_answer(message, primary_response, context)`:
```python
def ensure_dual_answer(message: str, response: str, context: str = "") -> str:
    if not classify_advice_intent(message):
        return response
    if "--- Advisor (" in response or "--- Advisor ---" in response:
        return response
    # Tự động kích hoạt Advisor và gắn vào cuối phản hồi
    adv_res = consult_advisor(message, context)
    return f"{response.rstrip()}\n\n{adv_res['formatted']}"
```
Coordinator trước khi phát ngôn cuối turn nếu nhận diện message là Advice Intent thì bắt buộc đảm bảo khối `--- Advisor (` có mặt. Nếu chưa có, `ensure_dual_answer` sẽ tự động kích hoạt truy vấn và gắn khối kết quả vào, loại bỏ hoàn toàn khả năng bỏ sót.
