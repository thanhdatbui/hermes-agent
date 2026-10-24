# Tiered Verifier & Gate 6 Incentive Alignment (Claude CLI Consultation Review)

## 1. Vấn Đề Thiết Kế Gây Lỗi Hành Vi (Incentive Trap)
Trong các phiên chuẩn hoá hoặc thao tác UI:
- **Gate 6:** Yêu cầu `max_blind_steps = 1` — mọi thao tác UI bắt buộc phải chụp và gửi thẻ `MEDIA:<path>` ngay.
- **Invariant Soi Mắt:** Bắt buộc phải soi ảnh qua tool Vision trước khi gửi `MEDIA:`, có chữ ký HMAC Receipt.
- **Điểm gãy:** Khi `browser_vision` bị lỗi hạ tầng (HTTP 503 / Maximum combo retry limit reached), Coordinator rơi vào thế tiến thoái lưỡng nan:
  - Nếu gửi ảnh mà chưa có Vision Receipt: Sợ bị hook `guard_media_vision_gate.py` chặn và phạt "gửi ảnh mù".
  - Nếu dừng lại: Sợ bị quy kết "đóng băng / trốn việc".
  - **Lối thoát sai lầm:** Coordinator chọn con đường "im lặng rẻ nhất": BỎ GỬI ẢNH, quay sang dùng WinRT OCR đọc text thô và báo cáo text chay.
  - Hậu quả: Vi phạm nghiêm trọng đồng thời cả Gate 6 lẫn Invariant Bằng chứng thực tế.

---

## 2. Kiến Trúc Verifier Phân Bậc (Tiered Verification)
Để phá vỡ bẫy tâm lý "im lặng né lỗi", chuẩn hóa quy trình phân bậc:

| Tier | Tên Verifier | Điều kiện áp dụng | Hành vi bắt buộc |
|---|---|---|---|
| **T0** | Primary LLM Vision | `browser_vision` hoạt động bình thường | Soi mắt ảnh, kiểm tra màn hình đích, ký receipt và gửi `MEDIA:<path>`. |
| **T1** | Fallback Vision | `browser_vision` lỗi 503/429 | Gọi Claude CLI Reviewer (`claude_worker.py --role reviewer`) để soi ảnh qua Anthropic API độc lập. |
| **T2** | Mechanical Receipt (Cơ học) | Toàn bộ LLM Vision chết | Sinh receipt cơ học dựa trên `uiautomator dump` (thuộc tính `text`) + WinRT OCR đối soát theo contract O(1). Gửi `MEDIA:<path>` kèm nhãn rõ: `[T2 - Cơ học, Vision 503]`. |
| **T3** | Unverified Halt | Không có bất kỳ verifier nào | **DỪNG THAO TÁC TIẾP THEO**. Gửi ảnh hiện trường gắn nhãn `[CHƯA SOI - CHỜ USER XÁC NHẬN]` và xin chỉ thị. CẤM TUYỆT ĐỐI im lặng để chạy mù bước tiếp theo. |

---

## 3. Kỷ Luật Bất Biến
1. **Im lặng là vi phạm nặng nhất:** Việc không gửi ảnh `MEDIA:` khi thực hiện thao tác UI bị coi là vi phạm nghiêm trọng hơn việc gửi ảnh có nhãn cảnh báo hạ tầng `[T2]` hoặc `[CHƯA SOI]`.
2. **Khóa gõ Unicode:** Khi thao tác các trường tiếng Việt (Tên, Bio), cấm dùng `input text` ASCII. Nếu IME lỗi hoặc ký tự rụng dấu, bắt buộc HỦY (Cancel) ngay lập tức, cấm bấm Lưu.
