# Sol Web Autonomous Fallback Worker Architecture (:20129)

Date: 2026-10-17  
Module: `D:/Taadaa/tools/sol_worker.py`  
Unit Tests: `D:/Taadaa/tools/tests/test_sol_worker.py` (8/8 passing)

---

## 1. Bối cảnh & Mục đích

Khi cả **Claude CLI** (chạm trần session 85% / weekly 90%) và **Agy CLI** đều cạn quota, hệ thống Taadaa Farm kích hoạt tầng phao cứu sinh **Sol Web Autonomous Worker** chạy qua OmniRoute `:20129` (model: `gpt-web-sol` / `chatgpt-web/gpt-5.6-sol-high`).

### Phân biệt với Sol Repair (:20129)
- **`sol_repair.py`**: Cơ chế 1-shot O(1) ($\le 30$ dòng diff) phục vụ độc quyền Closeout Gate Remediation (Strike 1 & 2).
- **`sol_worker.py`**: Autonomous ReAct Agent Loop đa bước (mặc định 8 turns) có khả năng đọc file, thực hiện chuỗi patch, và chạy test offline lặp lại cho tới khi hoàn tất.

---

## 2. Kỷ luật Phân vai Worker (Worker Permission Invariant)

**Worker chỉ làm việc trong sandbox hiện trường, tuyệt đối không có quyền chốt phiên:**
- Worker nhận prompt $\rightarrow$ Đọc repo $\rightarrow$ Áp dụng patch $\rightarrow$ Chạy lệnh test verification/focused test $\rightarrow$ **DỪNG LẠI và báo cáo nguyên văn bằng chứng (Diff + Test evidence)** về cho Coordinator & User.
- **VÙNG CẤM WORKER**: Worker CẤM TUYỆT ĐỐI tự ý chạy `git commit`, `git push`, hoặc tự ý chạy `closeout_gate.py`.
- Quyền phát lệnh chốt phiên thuộc về User; Coordinator chỉ chạy `closeout_gate.py` khi User ra lệnh.

---

## 3. Kiến trúc Chống Rủi ro Web của `sol_worker.py`

Giao diện Web chat thông thường có các nhược điểm nghiêm trọng khi dùng làm coding worker:
1. **Lười code / cắt cụt code** (`# ... giữ nguyên phần cũ ...`): Làm bay màu logic nếu ghi đè file.
2. **Vỡ cú pháp JSON**: Web không có native function calling của GPU, dễ sinh JSON hỏng khi context dài.
3. **Lỗ hổng Shell Injection**: Khi gõ lệnh qua `shell=True`.

`sol_worker.py` triệt tiêu 100% các rủi ro trên:

### A. Tolerant DSL Parser (Chống vỡ JSON)
Thay vì bắt model trả JSON nghiêm ngặt, worker sử dụng text-block DSL với regex:
- `ACTION: READ_FILE` (kèm `PATH: ...`, `LINES: X-Y`)
- `ACTION: PATCH` (kèm block `<<<<<<< SEARCH ... ======= ... >>>>>>>`)
- `ACTION: COMMAND` (kèm `COMMAND: ...`)
- `ACTION: DONE` (kèm `SUMMARY: ...`)
- `ACTION: BLOCKED` (kèm `REASON: ...`)

### B. Patch Search/Replace Độc quyền & Atomic Write
- CẤM hành động ghi đè cả file (`write_file`).
- Bắt buộc `SEARCH` block xuất hiện **duy nhất 1 lần** trong file (`count == 1`).
- Với file Python (`.py`), chạy `ast.parse` trên bộ nhớ; nếu lỗi cú pháp (`SyntaxError`), hủy patch ngay lập tức và báo model sửa lại.
- **Atomic File Replacement**: Ghi ra file tạm `.tmp.<uuid>` cùng thư mục rồi gọi `os.replace` để nguyên tử hóa, chống hỏng file khi đứt gãy tiến trình.
- Chuẩn hóa line endings LF (`\n`) để tránh phình git diff trên Windows MSYS.

### C. Sandboxing Lệnh Shell (`is_command_safe`)
- **Chặn đứng Shell Injection**: Regex quét chặn các metacharacters nguy hiểm: `re.search(r"[;&|`$]", cmd)`.
- **Chặn lệnh phá hoại**: Cấm `rm`, `del`, `rmdir`, `git reset`, `git clean`, `git push`, `adb shell input`.

---

## 4. Cách Sử Dụng CLI

```bash
python D:/Taadaa/tools/sol_worker.py "Sửa lỗi X trong script Y" \
  --workdir "D:/Taadaa/tools" \
  --file "script_y.py" \
  --max-turns 8 \
  --model gpt-web-sol \
  --url http://127.0.0.1:20129/v1/chat/completions
```

- `0`: Thành công và test passed.
- `1`: Bị blocked hoặc lỗi logic / input không hợp lệ (`max_turns <= 0`).
- `124`: Hết ngân sách turns (`max_turns`).
- `125`: `QUOTA_BLOCKED` (429 rate limit hoặc quota cạn $\rightarrow$ trigger xoay tua sang account tiếp theo trong pool).
