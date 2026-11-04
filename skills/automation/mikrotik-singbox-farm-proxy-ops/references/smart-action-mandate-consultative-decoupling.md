# Smart Action Mandate & Consultative Intent Decoupling

## 1. Nỗi Đau Vận Hành (The Lexical Mandate Trap)
Trong `agent/conversation_loop.py`, cơ chế `Mechanical Guidance Action Mandate` ban đầu dùng bộ quét chuỗi đàm thoại thô sơ:
- Quét các cụm từ: `'đang cho '`, `'đang kiểm tra'`, `'sẽ báo cáo'`, `'để em '`, `'em sẽ '` trong 300 ký tự cuối.
- Nếu thấy cụm từ mà lượt đó bot chưa gọi tool -> tự động ngắt câu trả lời (`final_response = None`), tiêm thông điệp cưỡng chế `[MECHANICAL GUIDANCE ACTION MANDATE (N/3): ...]`.

### Hậu Quả Tai Hại:
- Khi User đặt câu hỏi mang tính **Tư vấn / Thảo luận / Chất vấn kiến trúc** (`"Là sao?"`, `"Tại sao?"`, `"Có nặng CPU không?"`), bot định giải thích lý lẽ bằng lời văn thì bị Gate coi là "hứa hão".
- Bot bị chặn họng đến 3 lần, sinh ra phản xạ thích nghi máy móc: **gọi bừa các lệnh đo kiểm vô hại (ping dashboard, probe proxy) để làm "vé mở cổng"**.
- Kết quả: Câu trả lời thực tế bị băm nát, User chỉ nhận được các dòng log telemetry rác rưởi gây ức chế tột độ.

## 2. Phân Tách Kiến Trúc O(1) (Consultative Decoupling)
Không được cắt sạch Gate (vì vẫn cần Guard để chống hứa suông không làm thật). Thay vào đó, áp dụng giải pháp phân định Intent $O(1)$ nhẹ như lông hồng:

```python
# 1. Tập dấu hiệu tư vấn / hỏi ý kiến / đối thoại với User (Bypass)
CONSULTATIVE_MARKERS = {
    'sếp', 'anh', 'tùy', 'nếu', 'có nên', 'thế nào', 'sao',
    'hỏi', 'tư vấn', 'giải thích', 'tóm lại', 'nghĩ sao', 'thấy sao',
    'đúng không', 'đúng ko', 'đúng k',
}

# 2. Tập từ khóa thi công thực sự (Execution Signals)
EXECUTION_SIGNALS = {
    'đang tiến hành ', 'i will deploy', 'i will execute', 'i am deploying',
    'đang deploy', 'đang cài đặt',
}

# 3. Phân định O(1)
_tail = (final_response or '').strip().lower()[-300:]
_is_consultative = _tail.endswith('?') or any(k in _tail for k in CONSULTATIVE_MARKERS)

# Chỉ bắt action khi thực sự là lời hứa thi công VÀ KHÔNG PHẢI là lượt đàm thoại tư vấn
_matched_action = None if _is_consultative else next((p for p in _action_phrases if p in _tail), None)
```

## 3. Quy Chuẩn Vận Hành
- Khi User hỏi ý kiến / chất vấn: Bot trả lời thẳng bằng câu chữ, kết thúc bằng câu hỏi hoặc lời xưng hô đàm thoại -> Bypass tự nhiên.
- Khi User ra lệnh thi công (`Fix`, `Deploy`, `Chạy`): Bot bắt buộc phải xách tool ra làm thật hoặc trích xuất bằng chứng, nếu nói mồm `"đang tiến hành..."` mà không gọi tool -> Gate chặn đứng 100%.
