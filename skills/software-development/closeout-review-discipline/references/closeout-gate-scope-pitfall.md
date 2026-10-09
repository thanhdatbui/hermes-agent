# Closeout Gate — Scope Pitfall (HEAD~N Selection)

## Vấn đề

`closeout_gate.py` chấm điểm dựa trên **toàn bộ diff trong `--base` scope**. Khi một session có nhiều commit nhỏ liên tiếp (alias, wrapper, test bổ sung, fix nhỏ), nếu mỗi lần chạy gate chỉ truyền `HEAD~1`, reviewer chỉ thấy 1 commit cực nhỏ và không có đủ context để hiểu giá trị thực của session → **điểm thấp giả, bị REJECTED dù thực ra tốt**.

## Ví dụ thực tế (2026-10-07 — Hotmail repo)

Session có 5 commits:
```
HEAD~0: fix: null-safe GPM start_profile + integration tests
HEAD~1: test: resilient state handling, malformed API responses & workbook filtering
HEAD~2: feat: telemetry for gpm profile lookup & comprehensive test coverage
HEAD~3: fix: add backward-compatible alias find_gpm_profile_for_machine
HEAD~4: feat: gpm_change_hotmail_security full workflow
```

| Base ref | Score | Verdict |
|----------|-------|---------|
| `HEAD~1` | 75/100 | REJECTED — "chưa có integration test" |
| `HEAD~2` | 78/100 | REJECTED — "scope test quá hẹp" |
| `HEAD~5` | **88/100** | **APPROVED** |

Reviewer có đủ context để thấy workflow 4 bước, test suite đầy đủ, và evidence real-world canary → điểm tăng 10+ điểm nhờ scope đúng.

## Rule

**Khi chọn `--base`, tính ngược từ trước khi session bắt đầu task đó.**

```bash
# Bước 1: Đếm số commit thuộc session này
git log --oneline HEAD~15..HEAD

# Bước 2: Truyền đúng N
python D:/Taadaa/tools/closeout_gate.py \
  --repo "D:/Taadaa/Hotmail" \
  --base HEAD~5 \
  --files scripts/gpm_change_hotmail_security.py tests/test_gpm_change_hotmail_security.py \
  --json-output
```

## Pattern chuẩn

1. Trước khi chạy gate, chạy `git log --oneline HEAD~10..HEAD` để đếm commit của session.
2. Đặt `--base HEAD~<số commit session>`.
3. `--files` phải match đúng danh sách files trong scope commit range:
   ```bash
   git diff --name-only HEAD~N  # list files changed trong N commits
   ```
4. Gate nhận diff đủ lớn → reviewer có context hoàn chỉnh → điểm phản ánh thực chất.

## Khi Gate Fail vì "scope quá hẹp"

Đây **không phải lỗi code** — là lỗi truyền tham số gate. Không cần sửa code. Chỉ cần mở rộng `--base HEAD~N` và retry.

Reviewer thường reject với các lý do sau khi scope quá hẹp:
- "chưa chứng minh toàn bộ luồng"
- "phạm vi test còn giới hạn"
- "không có evidence về hành vi farm thực tế"
- "thiếu integration test"

Các lý do này biến mất khi scope đúng.
