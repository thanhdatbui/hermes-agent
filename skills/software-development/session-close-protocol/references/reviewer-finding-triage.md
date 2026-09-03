# Triage reviewer findings before repair (closeout)

Dùng khi plan-review trả `REJECT` trong closeout: phân loại finding nào là
lỗi thật, finding nào là false-positive, trước khi sửa. Sửa mù theo review
đã từng tạo ra string hỏng và commit lỗi trong phiên 2026-09-03.

## 1. Reproduce từng blocker trước khi edit

- **Syntax claim** → `python -m py_compile <file>` trên đúng file. Chỉ sửa
  khi compile fail thật.
- **Missing function/import claim** → grep định nghĩa trong source + import
  bằng đúng cwd mà runner chính thức dùng (ví dụ `python_runner/` chứ không
  phải repo root). Import sai cwd cho `ModuleNotFoundError` giả.
- **Broken-string claim** → in `repr()` dòng bị nêu tên, kiểm tra continuation.

## 2. Baseline check cho test fail

Khi focused test fail sau edit, stash scoped file và chạy lại trên HEAD sạch:

```bash
git stash push -m "wip: triage" <scoped-file>
python -m pytest <failing-test> -x
git stash pop
```

Fail cả trên HEAD sạch = lỗi có sẵn (baseline), không quy cho candidate.
Báo rõ baseline, không fix lan man ngoài scope.

## 3. Pitfall: backslash-newline trong f-string

```python
canary_cmd=f'...scripts\
un-follow.ps1" ...'
```

Backslash cuối dòng là line-continuation: hoặc sinh chuỗi hỏng
(`scriptsun-follow.ps1`, mất `run-`) hoặc `SyntaxError: unterminated string
literal` (py_compile bắt được). Fix: khi chuỗi không cần interpolation, bỏ
`f` prefix và dùng plain string một dòng với `/` thay vì `\\`.

## 4. Stale git lock sau tiến trình timeout

`fatal: cannot lock ref ... File exists` sau khi git process timeout:
chứng minh không còn writer active (tasklist), rồi chỉ xóa đúng file
`*.lock` stale (`index.lock`, `HEAD.lock`, `refs/heads/*.lock`). Tuyệt đối
không `reset --hard` / `clean -fd` để "dọn" lock.

## 5. Tự động sửa lỗi & Re-review vòng lặp đến APPROVED

Khi review trả `REJECT` trong chốt phiên:
1. **KHÔNG DỪNG LẠI & CẤM PUSH KHI CÒN REJECTED:** Tuyệt đối không dừng phiên báo blocker dở dang khi chưa nỗ lực sửa, và CẤM TUYỆT ĐỐI push lên remote khi chưa có `DECISION: APPROVED`.
2. **Tự động triage & fix vòng lặp:**
   - Triage từng blocker (kiểm tra syntax bằng `py_compile`, kiểm tra circular import, loại bỏ collision priority, thêm fail-closed checks).
   - Chạy focused unit tests để bảo đảm fix hoạt động.
   - Gọi lại G1 Plan-Review với toàn bộ diff phiên (so với base commit đầu phiên `git diff <base_commit>` để reviewer nhìn thấy đầy đủ các alias và hàm phụ trợ, tránh false-rejection).
   - Lặp lại quy trình sửa -> test -> review đến khi nhận được `DECISION: APPROVED`.
3. **Chỉ chuyển sang G2/G3/G4 sau khi APPROVED:** Khi đã có verdict APPROVED từ 9Router, mới tiến hành commit exact scope, rebase upstream và push remote.
