# Sol Repair Empty Proposal Pitfall & Pytest PYTHONPATH Resolution (2026-10-18)

## 1. Bẫy Sol Repair trả về rỗng (`patches_count: 0`)

### Triệu chứng
Khi chạy `python D:/Taadaa/tools/sol_repair.py` trong vòng Strike 1 Remediation, file proposal trả về `valid: true` nhưng `file_patches: []` và `patches_count: 0`.

### Nguyên nhân gốc rễ
1. **Thiếu `--diff-file`:** Trong mã nguồn `sol_repair.py`, nếu không truyền `--diff-file`, biến `diff_text` gửi lên cho Sol High (`gpt-web-sol`) là chuỗi rỗng `""`.
2. **Monolith không có ngữ cảnh code:** Khi chỉ nhận được vài câu tóm tắt finding chung chung mà không có git diff, model không thể tự suy đoán chính xác từng dòng code cũ (`<<<OLD>>>`) trong file mã nguồn lớn hàng ngàn dòng.
3. **Regex bóc tách khắt khe:** `_parse_repair_response` sử dụng regex bắt buộc cấu trúc:
   ```text
   <<<FILE: path/to/file.py>>>
   <<<OLD>>>
   <old_code_exact>
   <<<NEW>>>
   <new_code>
   <<<END>>>
   <</FILE>>>
   ```
   Do không có diff, Sol chuyển sang giải thích bằng văn xuôi/markdown $\rightarrow$ regex không bắt được hunk nào $\rightarrow$ trả về danh sách patch rỗng.

### Quy chuẩn gọi `sol_repair.py` chuẩn xác
Luôn xuất diff trước ra file tạm và truyền đầy đủ cờ `--diff-file`:
```bash
git -C <repo> diff <base> -- <target_files> > D:/Taadaa/logs/candidate.diff
python D:/Taadaa/tools/sol_repair.py \
  --repo <repo> \
  --files <target_files> \
  --diff-file D:/Taadaa/logs/candidate.diff \
  --scorecard-json <scorecard_path> \
  -o <output_proposal_path>
```

---

## 2. Lỗi Pytest `ModuleNotFoundError: No module named '_path_setup'` trong Closeout Gate

### Triệu chứng
`closeout_gate.py` tự động phát hiện test và chạy pytest từ root repo nhưng bị crash ngay tại bước collection:
```text
ImportError while importing test module '.../python_runner/tests/test_multi_machine_feed_session.py'.
ModuleNotFoundError: No module named '_path_setup'
```

### Nguyên nhân
Khi pytest chạy từ root repo mà `pytest.ini` không khai báo `pythonpath`, Python chỉ đưa thư mục root vào `sys.path`. Các helper test đặt trong subfolder `python_runner/tests` (như `_path_setup.py`) sẽ không được tìm thấy.

### Giải pháp
Trong `pytest.ini` của repo con, bắt buộc cấu hình rõ `pythonpath`:
```ini
[pytest]
addopts = --import-mode=importlib
pythonpath = python_runner/tests python_runner
```

---

## 3. Kỷ luật giao tiếp khi User hỏi "Xong hết chưa" (Anti-Bureaucracy / Anti-Stalling)

- **Triệu chứng:** Khi user hỏi "xong hết chưa", agent trả lời mang tính quan liêu ("chưa xong vì chưa commit, chưa closeout, repo dirty...") khiến user ức chế.
- **Hành động đúng:**
  1. Xác nhận dứt khoát trạng thái code: Code đã lưu và kích hoạt trên đĩa thực tế hay chưa.
  2. Báo cáo cụ thể: Đã test pass cái gì, ca chạy tiếp theo sẽ tự động áp dụng logic mới ra sao.
  3. Chủ động kích hoạt Closeout Gate ngay nếu user có ý định kết thúc phiên, không chần chừ hay đưa ra lý do thoái thác.
