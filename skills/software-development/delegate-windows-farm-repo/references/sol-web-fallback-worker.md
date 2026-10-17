# Sol Web Autonomous Fallback Worker (:20129)

Module: `D:/Taadaa/tools/sol_worker.py`
Unit Tests: `D:/Taadaa/tools/tests/test_sol_worker.py`

## 1. Bối cảnh & Vị trí trong Thang Điều Phối (Tiered Architecture)

Khi Claude CLI (`claude_worker.py`) và Agy CLI (`ag_cli.py`) chạm trần quota (85% session / 90% weekly), hệ thống kích hoạt **T2 Emergency Fallback: Sol Web Autonomous Worker**.

- **Endpoint**: OmniRoute `:20129` (model: `gpt-web-sol` hoặc `chatgpt-web/gpt-5.6-sol-high`).
- **Ưu điểm**: Không tốn chi phí token API chính ngạch; xoay tua tự động qua pool tài khoản Web của Farm.
- **Quyền hạn Worker Invariant**: Worker chỉ thực hiện đọc file, áp dụng patch, chạy test offline < 30s và **báo cáo diff + evidence**. CẤM TUYỆT ĐỐI Worker tự ý `git commit`, `push` hay tự ý chạy closeout gate. Quyền chốt phiên thuộc về User/Coordinator.

---

## 2. Kiến trúc Kỹ thuật Chống Rủi ro Web

Giao diện Web thường có 3 nhược điểm lớn khi làm worker coding: (1) Cắt cụt code / lười code (`# giữ nguyên phần cũ`), (2) Vỡ cú pháp JSON khi streaming dài, (3) Lỗ hổng shell injection nếu dùng `shell=True`. 

`sol_worker.py` giải quyết triệt để 3 nhược điểm này:

### A. Tolerant DSL Parser (Chống vỡ JSON)
Không dùng `json.loads` mà dùng text-block DSL regex:
```text
ACTION: READ_FILE
PATH: scripts/target.py
LINES: 1-100

ACTION: PATCH
PATH: scripts/target.py
<<<<<<< SEARCH
<exact existing lines in file to replace>
=======
<new replacement lines>
>>>>>>>

ACTION: COMMAND
COMMAND: python -m pytest tests/test_target.py -q

ACTION: DONE
SUMMARY: <brief summary>

ACTION: BLOCKED
REASON: <exact technical explanation>
```

### B. Atomic Patching & Cú pháp AST
- **Anchor duy nhất**: `search_block` bắt buộc xuất hiện đúng 1 lần trong file (`occurrences == 1`).
- **AST parse trước khi ghi**: Với file `.py`, kiểm tra `ast.parse` trên nội dung sau patch. Nếu văng `SyntaxError`, hủy patch và yêu cầu model sinh lại.
- **Ghi file Atomic**: Ghi ra file tạm `.tmp.<uuid>` cùng thư mục rồi `os.replace` để nguyên tử hóa, chống rách/hỏng file nếu tiến trình gián đoạn.
- **Chuẩn hóa LF**: Giữ nguyên line endings LF để tránh làm phình git diff trên Windows.

### C. Sandboxing Lệnh Shell (`is_command_safe`)
- Chặn tuyệt đối shell metacharacters: `re.search(r"[;&|`$]", cmd)`.
- Chặn danh sách lệnh phá hoại: `rm`, `del`, `rmdir`, `git reset`, `git clean`, `git push`, `adb shell input`.

---

## 3. Cách Sử Dụng CLI

```bash
python D:/Taadaa/tools/sol_worker.py "Sửa lỗi X trong target.py" \
  --workdir "D:/Taadaa/tools" \
  --file "target.py" \
  --max-turns 8 \
  --model gpt-web-sol \
  --url http://127.0.0.1:20129/v1/chat/completions
```

- **Exit code 0**: Hoàn thành và test pass.
- **Exit code 1**: Blocked hoặc lỗi logic.
- **Exit code 124**: Hết số turns tối đa (`max_turns`).
- **Exit code 125**: Quota / Rate limit (để trigger xoay tua sang account Web tiếp theo).
