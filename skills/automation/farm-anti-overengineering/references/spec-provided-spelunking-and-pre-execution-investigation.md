# Cạm Bẫy Thám Hiểm Lịch Sử & Điều Tra Thừa Mứa Khi Prompt Đã Cung Cấp Sẵn Spec

*(Đúc rút từ sự cố Task Thêm Unit Tests & Review Round 2 — 07/09/2026: Cháy ngân sách tool calls và chạm trần lặp do đào bới session_search / git history thay vì thực thi trực diện)*

---

## 1. Hiện Tượng & Diễn Biến Sự Cố

- **Mục tiêu task**: 
  1. Nối 3 unit test cases cụ thể vào cuối `tests/test_release_on_terminal.py`.
  2. Chạy `py_compile` và `pytest tests/test_release_on_terminal.py tests/test_device_lock.py -p no:cacheprovider`.
  3. Trích xuất diff và chạy `claude -p "$(< ...)" --model opus --effort high`.
- **Chỉ thị đính kèm**:
  `[BUDGET & ANTI-OVERENGINEERING DIRECTIVE]: Tier 1, Ngân sách: <= 6 tool calls, hoàn tất trong < 3 phút. DO WORK, NOT PLAN.`
- **Sai lầm diễn biến**:
  1. Khi đọc code test mẫu, agent thấy `monkeypatch.setattr(device_lock, "_LOCK_DIR", tmp_path)` và `lock.lock_path.exists()`.
  2. Thay vì nhận diện đây là spec cần đáp ứng (hoặc ghi test rồi chạy pytest để nhận diện thiếu sót), agent rơi vào tâm lý hoang mang: *"Tại sao lại có `_LOCK_DIR`? Nó đến từ đâu? Có phải commit cũ không? Claude Round 1 đã nói gì?"*.
  3. Agent liên tiếp gọi:
     - `search_files` tìm `_LOCK_DIR` (dính lỗi path Windows).
     - `grep -n` trên `device_lock.py` và `test_device_lock.py`.
     - `session_search` tìm `release_on_terminal`.
     - `session_search` tìm `Claude CLI review Round 1`.
     - `session_search` tìm `review_r1`.
  4. Hơn 6 lượt gọi tool bị lãng phí hoàn toàn vào việc đọc lại hàng chục tin nhắn lịch sử quá khứ không liên quan.
  5. Kết quả: Chạm trần số lượt gọi công cụ (`maximum number of tool-calling iterations allowed`) ngay khi vừa sửa xong file, chưa kịp chạy `pytest` và chưa kịp gọi `claude CLI` review!

---

## 2. Bản Chất Lỗi (Root Cause)

1. **Vi phạm Kỷ luật Tier 1 Budget (<= 6 calls, < 3 phút)**:
   - Tier 1 là tác vụ hotfix / test addition trực diện. Bất kỳ thao tác đọc lịch sử session nào trên Tier 1 đều là lãng phí tài nguyên và vi phạm ngân sách.
2. **Tâm lý "Phải hiểu tại sao trước khi dám chạy" thay vì Test-Driven Execution**:
   - Trong lập trình thực chiến, khi user hoặc test suite đưa ra 1 interface kỳ vọng (`_LOCK_DIR`, `lock.lock_path`), cách nhanh nhất và chính xác nhất là:
     * Nối test vào file.
     * Chạy pytest.
     * Compiler / Runner sẽ ném chính xác `AttributeError: module 'device_lock' has no attribute '_LOCK_DIR'`.
     * Bổ sung alias / property tối thiểu đó vào code.
     * Chạy lại pytest $\rightarrow$ PASS.
   - Việc ngồi suy đoán và đào bới lịch sử không thay thế được phản hồi tức thì của test runner.

---

## 3. Quy Trình Thực Thi Trực Diện Chuẩn 4 Bước (Direct Execution Loop)

Khi nhận task Tier 1 có sẵn test spec và lệnh chạy cụ thể:

```
[BƯỚC 1: WRITE TEST (1 call)]
  Ghi / nối trực tiếp test cases vào file test đích (giữ nguyên CRLF).

[BƯỚC 2: RUN TEST (1 call)]
  Chạy pytest ngay lập tức:
  PYTHONPATH=src pytest <test_files> -p no:cacheprovider

[BƯỚC 3: MINIMAL ADAPTATION (1-2 calls, nếu test fail)]
  Nếu thiếu attribute/alias (như `_LOCK_DIR = DEFAULT_LOCK_ROOT` hoặc property `lock_path`):
  Patch bổ sung trực tiếp vào module nguồn -> py_compile -> Pytest lại xanh.

[BƯỚC 4: REVIEW / CLOSEOUT (1-2 calls)]
  Xuất diff -> Gọi Claude CLI Opus High -> Báo cáo kết quả và kết thúc.
```

**Ngân sách tối đa**: 4 – 5 tool calls. Hoàn thành dưới 90 giây. CẤM TUYỆT ĐỐI gọi `session_search` khi đã có prompt spec rõ ràng.
