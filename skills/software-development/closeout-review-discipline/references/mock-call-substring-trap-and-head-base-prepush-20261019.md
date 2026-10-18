# Mock Call Substring Trap & Pre-Push Commit Re-Audit Protocol (2026-10-19)

## 1. Bẫy Substring "Program Files" Trong Mock Call Assertion
### Hiện tượng
Khi viết unit test kiểm tra hàm cứu hộ / launcher không được gọi lệnh shell phụ (ví dụ cờ `--reboot` bỏ qua Level 1 gọi `am force-stop`):
```python
# CODE LỖI DÍNH BẪY:
assert not any("am" in str(c) for c in mock_run.call_args_list)
```
Test lập tức bị FAIL dù luồng code không hề gọi `am`!

### Nguyên nhân cốt lõi
- Hàm `str(c)` ép toàn bộ đối tượng `call(args, ...)` thành chuỗi.
- Trên Windows, đường dẫn nhị phân ADB thường nằm tại:
  `"C:\Program Files (x86)\xiaowei\tools\adb.exe"`
- Chữ `"Program"` chứa chuỗi con `"am"`. Vì vậy `"am" in str(c)` luôn luôn trả về `True`!

### Quy chuẩn xử lý chuẩn xác
Tuyệt đối không so khớp substring trên chuỗi `str(mock_call)`. Bắt buộc bóc tách danh sách tham số (args list) hoặc token cuối:
```python
# QUY CHUẨN ĐÚNG:
cmds = [call_args[0][0][-1] for call_args in mock_run.call_args_list]
assert "am" not in cmds
assert "force-stop" not in cmds
assert cmds == ["get-state", "reboot"]
```

---

## 2. Quy Trình Pre-Push Hook & Thẩm Định Độc Lập Với `--base HEAD~1`
### Hiện tượng
Coordinator chạy `closeout_gate.py --base HEAD` khi working tree dirty đạt điểm 82 (Grace Approved), sau đó thực hiện `git commit` O(1) các file đích. Khi chạy `safe_push.py`, lệnh bị chặn đứng bởi pre-push hook:
`❌ [BLOCKED - PRE-PUSH HOOK]: Gate check FAILED — Không tìm thấy bản ghi Closeout Gate APPROVED >= 80 cho commit hiện tại!`

### Bản chất kỹ thuật
- Pre-push hook (`pre-push.sh` và `gate_common.py`) đối soát SHA commit chuẩn bị push với bảng audit log `gate_audit.jsonl`.
- Bản ghi chạy trước commit chỉ gắn với uncommitted / staged state, không có commit hash thực tế của commit mới tạo (`df0a546...`).

### Kỷ luật đóng phiên 2 bước
1. **Bước 1 (Staged Check & Commit):** Kiểm tra test xanh, commit O(1) đúng các file đích (`git commit -m "..." <file1> <file2>`).
2. **Bước 2 (Committed Re-Audit với `--base HEAD~1`):** 
   Chạy lệnh thẩm định ràng buộc trực tiếp vào commit vừa tạo:
   `python D:/Taadaa/tools/closeout_gate.py --repo <repo> --base HEAD~1 --files <file1> <file2> --json-output`
3. Khi Reviewer cấp điểm APPROVED (>= 85 hoặc Grace 80–84), token HMAC gắn đúng SHA commit mới sẽ được ghi vào audit log.
4. Chạy `python D:/Taadaa/tools/safe_push.py <repo> origin <branch>` sẽ thông qua pre-push hook ngay lập tức.
