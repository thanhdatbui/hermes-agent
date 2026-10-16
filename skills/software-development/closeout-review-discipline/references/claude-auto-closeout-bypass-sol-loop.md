# Auto-Closeout: Sol First-Pass -> Claude Worker Fix -> Mechanical Gate -> Direct Push (16/10/2026)

## Bối cảnh Sự cố: Thảm họa 27 Vòng Cày Điểm (12h - 6h sáng)
Khi dùng Sol High (:20129) làm reviewer bắt buộc chấm điểm >= 85:
- Sol chấm 82-84 điểm trong 27 vòng lặp lại do điểm số LLM là thước đo nhiễu ngẫu nhiên.
- Coordinator rơi vào bẫy Goodhart, cày sửa các vi chi tiết không cần thiết.
- Mệnh lệnh cứng của Operator:
  1. CẤM quarantine / CẤM báo BLOCKED khóc lóc đẩy việc cho Operator.
  2. Khi Sol trượt 2 lần (hoặc có `--skip-sol`), Claude CLI vào can thiệp.
  3. Claude CLI sửa code in-place + Claude Reviewer duyệt -> **Kích hoạt AI Push Gate (4 nấc cơ học) -> PUSH LUÔN QUA safe_push.py, BỎ QUA SOL HOÀN TOÀN**.

## Công cụ Thực thi: `D:/Taadaa/tools/auto_closeout.py`
Cú pháp:
```bash
python D:/Taadaa/tools/auto_closeout.py --repo <repo> --files <files> [--skip-sol]
```

### 4 Nấc Cổng Cơ Học Không Thể Gian Lận (AI Push Gate):
1. `py_compile`: Quét sạch lỗi cú pháp toàn bộ file `.py` đã sửa.
2. `pytest`: Toàn bộ suite test pass 100% (`rc == 0`).
3. `Test Integrity Guard`:
   - Số test collect không được giảm (`after >= baseline`).
   - Cấm xóa assert (`removed <= added`).
   - Cấm skip/xfail (`SKIP_RE`: `pytest.mark.skip`, `pytest.mark.xfail`, `unittest.skip`, `self.skipTest`).
4. `Diff Budget Guard`:
   - `git diff --numstat` <= 150 lines, <= 5 files.
   - Cấm đụng Protected Paths (`.env`, `config.yaml`, `AGENTS.md`, `tools/`, `.git/`).

### An toàn Phiên:
- **Rollback an toàn (Non-Destructive):** Lưu snapshot `pre_fix` patch trước khi sửa. Nếu vòng fix fail, tự động re-apply `pre_fix` để trả lại nguyên vẹn trạng thái ban đầu của user, TUYỆT ĐỐI CẤM `git checkout HEAD --` làm mất code dở dang.
- **Staging đúng target files:** Chỉ stage đúng các files trong `--files`, cấm stage file rác/DB phát sinh.
- **Auto-Detect Remote:** Tự động phát hiện remote (ưu tiên `fork` nếu có, ngược lại `origin`).
