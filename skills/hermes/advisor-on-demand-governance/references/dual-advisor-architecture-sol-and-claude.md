# Kiến Trúc Hội Đồng Cố Vấn (Dual Advisor: Sol + Claude)

## 1. Bối cảnh & Lý do hình thành
- Trước đây, "gọi advisor" chỉ truy vấn duy nhất Advisor Sol (GPT-5.6 / review qua cổng :20129).
- Khi có các tình huống nghi ngờ Coordinator thiên vị nội bộ ("nịnh hót", so sánh không khách quan giữa Hermes và các framework ngoài như OpenMausBot), hoặc cần thẩm định kiến trúc chuyên sâu:
  - Sol rất mạnh về ngữ cảnh farm, luật prompt và DAL SQLite, nhưng đôi khi có xu hướng đồng thuận với luồng nội bộ.
  - Claude Code CLI (`claude -p` / Sonnet) là thực thể hoàn toàn độc lập, cực kỳ khắt khe trong việc bắt các lỗi kiến trúc, fail-open, bypass guard và receipt rỗng.
- **Quyết định kiến trúc**: Gộp chung khi User phát lệnh "gọi advisor", hệ thống tự động triệu hồi song song **CẢ HAI** để tạo thành một Hội Đồng Cố Vấn hoàn chỉnh.

## 2. Cơ chế thực thi kỹ thuật (`consult_advisor.py`)
- **Đa luồng song song**: Sử dụng `concurrent.futures.ThreadPoolExecutor(max_workers=2)`.
  - Luồng 1: `_consult_sol_inner` stream HTTP SSE qua `http://127.0.0.1:20129/v1/chat/completions` (model: `review` / `gpt-web-sol`).
  - Luồng 2: `_consult_claude_inner` gọi trực tiếp binary `claude -p` qua subprocess (timeout 60s), lọc sạch các warning model catalog.
- **Tổng thời gian đáp ứng**: Không cộng dồn độ trễ (`latency_total = max(latency_sol, latency_claude)`), chỉ mất ~3 đến 5 giây trên môi trường thực tế.
- **Khả năng tự phục hồi (Resilience / Failover)**:
  - Nếu cả hai thành công ➔ Render khối Markdown Hội Đồng Cố Vấn với 2 section màu xanh lá (Sol) và tím (Claude).
  - Nếu Sol lỗi/timeout ➔ Render kết quả của Claude kèm nhãn cảnh báo.
  - Nếu Claude lỗi/timeout ➔ Render kết quả của Sol kèm nhãn cảnh báo.
  - Cả hai fail ➔ Trả về fallback `unavailable`, không làm sập luồng điều phối chính.

## 3. Cú pháp & Tùy chọn CLI
```bash
# Gọi cả hai (mặc định)
python D:/Taadaa/tools/consult_advisor.py -q "Câu hỏi kiến trúc"

# Chỉ gọi Sol
python D:/Taadaa/tools/consult_advisor.py -q "Câu hỏi" -a sol

# Chỉ gọi Claude
python D:/Taadaa/tools/consult_advisor.py -q "Câu hỏi" -a claude
```
