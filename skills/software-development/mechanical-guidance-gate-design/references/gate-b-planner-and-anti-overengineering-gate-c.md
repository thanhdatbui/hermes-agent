# Gate B Planner & Anti-Overengineering Gate C Architecture (2026-10-30)

## 1. Bản chất vấn đề
Trong mô hình điều phối của Hermes Agent Coordinator:
1. **Lỗ hổng của Coordinator tự lập plan:** Khi Coordinator (Gemini Flash) tự vẽ plan rồi ném cho Worker, chất lượng plan rất kém, dễ suy diễn sai logic, dẫn đến Worker sửa sai hoặc bị Guard chặn.
2. **Cơ chế Gate A-B-C cần được khôi phục nhưng không được lặp lại sai lầm cũ:**
   - Phiên bản cũ của `plan_exec_gate.py` bị over-engineered nặng nề (1.787 dòng): dùng Windows DACL, HMAC, memory scan, gây timeout > 120s và làm tê liệt hệ thống.
   - Thẩm định ban đầu của Claude đề xuất timeout 15s và `file_sha256`, bị User bóc trần là lý thuyết suông và over-engineered: 15s không đủ cho Gemini Pro suy luận sâu và failover acc; SHA256 dễ chết vì lệch xuống dòng CRLF/LF trên Windows.

## 2. Kiến trúc Gate B Planner chuẩn thực chiến
- **Primary (Tier 1 Planner):** `gemini-web` (Argon 4 Pool qua `http://127.0.0.1:20129/v1/chat/completions`) để tận dụng khả năng reasoning của Gemini Pro và tiết kiệm 100% quota Claude.
- **Timeout thực tế:** `GEMINI_TIMEOUT = 90s` (cho phép Gemini Pro đọc hiện trường lớn và OmniRoute failover giữa 15 acc nếu gặp session 401).
- **Fallback (Tier 2 Planner):** Nếu `gemini-web` quá 90s hoặc lỗi cả pool $\rightarrow$ Tự động fallback sang `claude -p` local (`CLAUDE_TIMEOUT = 120s`).
- **Chuẩn hóa CRLF/LF & Bỏ SHA256:**
  - Chuẩn hóa text: `nl(s) = s.replace("\r\n", "\n")`.
  - Không băm `file_sha256`. Chỉ kiểm tra điều kiện O(1): `txt.count(old_string) == 1` (anchor duy nhất).
- **Đầu ra chuẩn Contract O(1):**
  ```json
  {
    "planner": "gemini-web",
    "edits": [
      {
        "file": "path/to/target.py",
        "old_string": "exact_unique_content",
        "new_string": "replacement_content"
      }
    ],
    "test_cmd": "pytest tests/test_focused.py -q"
  }
  ```

## 3. Thứ tự Worker Gate C & Hậu kiểm độc lập
- **Thang Worker ưu tiên:**
  1. **Tier 0 (Primary):** `qoder_worker.py` (Qoder CLI chạy DeepSeek-Flash — miễn phí, tốc độ cao).
  2. **Tier 1 (Fallback 1):** `sol_worker.py` (`gpt-web-sol` qua `:20129`).
  3. **Tier 2 (Fallback 2):** `ag_cli.py fix` (Antigravity CLI pool).
  4. **Tier 3 (Fallback 3):** `claude_worker.py --role worker` (Haiku CLI).
- **Hậu kiểm độc lập ở Gate C:**
  - Gate C không tin lời khai của Worker mà tự kiểm tra file thực tế:
    ```python
    def applied(e):
        t = nl(Path(e["file"]).read_text(encoding="utf-8"))
        old, new = nl(e["old_string"]), nl(e["new_string"])
        return t.count(new) >= 1 and (old in new or old not in t)
    ```
  - **Cứu tiến độ dở dang:** Tier sau chỉ thi công các edit chưa hoàn thành (`pending = [e for e in edits if not applied(e)]`), không đè lại việc đã xong.
  - **Phát hiện xung đột anchor:** Nếu `count(old_string) != 1` trước khi giao việc $\rightarrow$ Trả về `REPLAN` để Gate B lập lại plan, cấm sửa đè mù quáng.
