# BẪY ĐƯỜNG DẪN POSIX MSYS TRONG GIT PRE-PUSH HOOK TRÊN WINDOWS (2026-10-13)

## 1. Hiện tượng & Triệu chứng Sự cố
Sau khi chạy `closeout_gate.py` thành công với điểm số cao (ví dụ: **88/100 APPROVED**), bản ghi đã được ghi đầy đủ vào `D:/Taadaa/logs/gate_audit.jsonl`.
Tuy nhiên khi thực hiện lệnh `git push`, pre-push hook (`.git/hooks/pre-push` hoặc `hooks/pre-push.sh`) lập tức chặn đứng:
```text
[pre-push] Kiểm tra Closeout Gate audit log trước khi push...
❌ [BLOCKED - PRE-PUSH HOOK]: Gate check FAILED — Không tìm thấy bản ghi Closeout Gate APPROVED >= 85 cho commit hiện tại!
   Không tìm thấy bản ghi Closeout Gate APPROVED (Score >= 85) khớp đúng commit/scope hiện tại.
   Quy tắc Hard Invariant (INC-HERMES-2026-001) cấm tuyệt đối push khi gate chưa thông qua!
error: failed to push some refs to '...'
```

---

## 2. Căn nguyên Kỹ thuật (Root Cause)

1. **Lệch pha định dạng đường dẫn giữa MSYS Bash và Windows Native Python:**
   - Pre-push hook chạy trong môi trường Git Bash (MSYS2).
   - Lệnh `REPO_DIR="$(pwd)"` trả về đường dẫn dạng POSIX: `/d/Taadaa/Hermes`.
2. **Windows Python không hiểu đường dẫn `/d/...`:**
   - Hook truyền biến `REPO_DIR` vào đoạn mã Python:
     ```python
     repo_dir = Path('$REPO_DIR')
     def git_output(*args):
         result = subprocess.run(['git', '-C', str(repo_dir), *args], capture_output=True, text=True)
         ...
     current_commit = git_output('rev-parse', 'HEAD')
     ```
   - Windows native Python (`python.exe`) coi `/d/Taadaa/Hermes` là thư mục không tồn tại trên ổ đĩa hiện tại (`C:\d\Taadaa\Hermes`).
   - Kết quả: Lệnh `git -C /d/Taadaa/Hermes rev-parse HEAD` văng lỗi:
     `fatal: cannot change to '/d/Taadaa/Hermes': No such file or directory`
   - `git_output()` trả về chuỗi rỗng `''`.
3. **Fail-Closed Gate Mù Quáng:**
   - Do `current_commit == ''`, hook không thể so khớp với bất kỳ `commit_sha` nào trong `gate_audit.jsonl`, dẫn đến kết luận sai lầm rằng *"Không tìm thấy bản ghi APPROVED cho commit hiện tại"* và chặn push 100%.

---

## 3. Quy tắc Sửa Chữa & Chuẩn Hóa Bất Biến

### A. Chuẩn hóa lệnh lấy đường dẫn Windows trong Bash Hook
Trong toàn bộ các file hook bash (`pre-push`, `pre-commit`, shell scripts) trên Windows, **CẤM TUYỆT ĐỐI** dùng `REPO_DIR="$(pwd)"`.
**BẮT BUỘC** dùng:
```bash
REPO_DIR="$(pwd -W 2>/dev/null || pwd)"
```
- Trong Git Bash (MSYS), `pwd -W` in ra đường dẫn chuẩn Windows dạng POSIX slash: `D:/Taadaa/Hermes`.
- Khi truyền vào `Path('$REPO_DIR')` của Python trên Windows, Python nhận diện chính xác ổ đĩa `D:` và thực thi lệnh git con mượt mà.

### B. Kiểm chứng độc lập
Sau khi sửa, test ngay bằng lệnh:
```bash
bash .git/hooks/pre-push
```
Xác nhận stdout hiển thị thành công:
```text
✅ [pre-push] Closeout Gate OK: verdict=APPROVED score=88 passed=True commit=e8a367aa3...
[pre-push] Cho phép push.
```
