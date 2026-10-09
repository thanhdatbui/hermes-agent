# Smart Comment Peek & Feed Swipe Unit Testing

## Testing Pitfalls & Verification Guidelines

1. **File Size & Collection Guard:**
   - `flows/feed_swipe_smoke.py` có kích thước rất lớn (>23k lines).
   - Trước khi chạy `pytest` cho các test logic mới (ví dụ `python_runner/tests/test_comment_peek_logic.py`), luôn kiểm tra cú pháp nhanh bằng:
     ```bash
     python -m py_compile flows/feed_swipe_smoke.py
     ```
   - Điều này giúp bắt ngay `IndentationError` hoặc `SyntaxError` cục bộ trước khi pytest collection bị abort toàn bộ.

2. **Required Helpers for Comment Peek:**
   - `_parse_comment_count(text: str) -> int | None`: Xử lý regex cho các định dạng số comment (k, m, số nguyên, text tiếng Việt "Bình luận: X", tiếng Anh "X comments").
   - `_feed_action_counts(table: list[dict]) -> dict`: Tổng hợp metric `comment_peeks` và đếm chi tiết theo feed type (`for-you`, `following`, `friends`).
