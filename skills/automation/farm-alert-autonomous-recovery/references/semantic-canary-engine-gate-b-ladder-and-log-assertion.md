# Semantic Canary Engine: Kiến Trúc & Kỷ Luật Kiểm Chứng Nhánh Sửa

## 1. Bản Chất Vấn Đề (Anti-Performative Canary)
- **Căn bệnh "Canary hình thức":** Trước đây, `canary_matrix.json` chỉ map theo pattern file tĩnh (`**/flows/feed*` -> `feed_swipe`). Khi sửa logic sâu bên trong một file monolith lớn (như nhánh fallback tab, 2FA, switcher, xử lý rớt mạng), `canary_runner.py` chỉ chạy lệnh hardcode thô thiển (`--recovery-test-swipes 2`). Kết quả là máy thật chỉ lướt 2 video For You rồi dừng, **nhánh code vừa vá hoàn toàn chưa hề được chạy qua**, nhưng runner vẫn cấp `CANARY_VERDICT: PASSED`. Đây là PASS GIẢ.
- **Giải pháp:** Tích hợp tầng AI Semantic Canary Planner để đọc `git diff` thực tế, tự sinh tham số CLI ép máy thật chạy đúng nhánh code vừa sửa, và thiết lập các assertion bắt buộc kiểm tra log.

## 2. Kiến Trúc Não Bộ (Đồng Nhất Thang Gate B)
CẤM TUYỆT ĐỐI hardcode riêng lẻ một model (như chỉ gọi `claude-cli`), mà phải tuân thủ chuẩn xác **thang mô hình phân tầng của Gate B**:
1. **Ưu tiên 1 (Primary):** `gemini-web` qua OmniRoute `:20129` (timeout 120s, nhanh, miễn phí token pool).
2. **Fallback 1:** `gpt-web-sol` qua OmniRoute `:20129` (timeout 120s, Sol Worker).
3. **Fallback 2 (Chặn cuối):** `claude-cli` local qua `stdin` (timeout 150s, Sonnet, CREATE_NO_WINDOW trên Windows).

## 3. Schema Semantic Canary Plan
`canary_plan.py` sinh ra cấu trúc `semantic`:
```json
{
  "target_flow": "<tên hàm / nhánh nghiệp vụ vừa sửa>",
  "rationale": "<lý do cần tham số này>",
  "cli_args_override": [
    "--feed-distribution", "{\"for-you\": 0.0, \"following\": 0.5, \"friends\": 0.5}",
    "--recovery-test-swipes", "4"
  ],
  "log_assertions": {
    "required_patterns": ["fallback_feed_tab", "FEED_TYPE_FOR_YOU"],
    "forbidden_patterns": ["navigation mismatch", "Traceback", "Exception"],
    "min_matches": 1
  },
  "ocr_spec": {
    "required_terms": ["For You", "Dành cho bạn"],
    "forbidden_terms": ["launcher", "màn hình chính"]
  },
  "planner": "gemini-web"
}
```

## 4. Kỷ Luật Hậu Kiểm Cơ Học Trong Runner (Fail-Closed Gate)
`canary_runner.py` không tin lời hứa mà đối soát trực tiếp hiện trường file `log.jsonl` và `summary.txt` sau ca chạy:
1. **Ép cờ CLI:** Nạp đè `cli_args_override` vào câu lệnh khởi chạy trên máy thật.
2. **Quét Assertion Log:**
   - Đếm số pattern bắt buộc (`required_patterns`) xuất hiện trong log.
   - Nếu số pattern khớp < `min_matches`: **ĐÁNH RỚT CANARY NGAY LẬP TỨC** (`[CANARY_FAIL] SEMANTIC_ASSERTION_FAILED`), exit code 1, không ghi nhận `.canary_receipt.json`.
   - Nếu xuất hiện bất kỳ chuỗi lỗi cấm (`forbidden_patterns`): **ĐÁNH RỚT CANARY NGAY LẬP TỨC**.
3. **Cách Kiểm Thử 2 Chiều (Verification Protocol):**
   - *Chiều thuận (Planner):* Chạy `canary_plan.py --repo ... --base HEAD~1` kiểm tra LLM đọc diff và sinh đúng `cli_args_override` và `log_assertions`.
   - *Chiều nghịch (Fail-closed Gate):* Viết unit test giả lập một plan có pattern không tồn tại (`NON_EXISTENT_PATTERN`), khẳng định runner phải trả về exit code 1 khi log thiếu pattern nghiệm thu.
