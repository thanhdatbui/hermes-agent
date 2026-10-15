# Đồng bộ hóa Block giữa scripts/ và hermes_cron/ & Kỷ luật Line Budget Architecture Gate

## 1. Cơ chế kiểm tra đồng bộ character-for-character (Helper Block Identity)
Trong repo `tiktok-luot nuoi acc`, các hàm helper dùng chung cho watchdog (như `RECONCILE_METRICS`, `buffer_reconcile_iso`, `parse_reconcile_iso_dt`, `is_session_key_p1_or_unknown`) tồn tại song song ở hai vị trí:
1. `scripts/feed_session_watchdog.py` (runtime tiêu chuẩn trong repo).
2. `scripts/hermes_cron/feed_session_watchdog.py` (standalone wrapper deploy cho cron Hermes).

Test `test_reconcile_helpers_in_sync_with_hermes_cron` trong `tests/test_feed_session_watchdog.py` kiểm tra chặt chẽ:
```python
def helper_block(path):
    src = open(os.path.join(root, path), encoding="utf-8").read()
    return src[src.index("RECONCILE_METRICS: dict"):src.index("def reconcile_cluster_following(")]

assert helper_block("feed_session_watchdog.py") == helper_block("hermes_cron/feed_session_watchdog.py")
```

### Bẫy thường gặp (Pitfall):
- Khi sửa logic ở `feed_session_watchdog.py` mà quên sửa `hermes_cron/feed_session_watchdog.py` hoặc ngược lại -> test fail 100%.
- Khi sửa cả hai file nhưng một file viết inline `if was_capped: buffered_dt = end_of_day`, file kia xuống dòng 2 dòng -> test fail vì lệch chuỗi ký tự.
- **Quy tắc:** Bất kỳ sửa đổi nào trong vùng helper block bắt buộc phải copy/patch đồng nhất 100% giữa hai file và chạy pytest trước khi commit.

---

## 2. Kỷ luật ngân sách dòng Architecture Gate (Line Budget <= 1450)
`tests/test_watchdog_architecture_gate.py` thiết lập chốt chặn cứng:
```python
assert line_count <= 1450, f"feed_session_watchdog.py has {line_count} lines, exceeds 1450 budget"
```

### Cách xử lý khi chớm vượt trần (> 1450 dòng):
1. **Không mở rộng file monolith:** Không viết thêm helper dài dòng trực tiếp vào `feed_session_watchdog.py`.
2. **Dọn dẹp import và docstring thừa ở header:** Thu gọn các đoạn import trùng lặp (ví dụ `import os`, `import sys` lặp lại nhiều lần) và các docstring mô tả lịch ca quá dài.
3. **Phân rã sang package:** Đưa các khối logic chức năng sang `scripts/watchdog/` (ví dụ `scripts/watchdog/lock.py`, `scripts/watchdog/merger.py`, `scripts/watchdog/alerts.py`, `scripts/watchdog/formatters.py`, `scripts/watchdog/parser.py`).

---

## 3. Quản lý Diff Size và Scoped Files trong Closeout Gate
- **Diff Ceiling (30KB):** Nếu diff tổng (bao gồm cả test suite lớn) vượt quá 30.000 bytes, `closeout_gate.py` sẽ báo lỗi `GATE-FAIL(diff-too-large)`.
- **Giải pháp:** Chỉ định danh sách file cốt lõi cần review bằng `--files <file1> <file2>`.
- **Ràng buộc Staging:** Khi dùng `--files`, danh sách staged changes phải khớp chính xác với danh sách file truyền vào tham số `--files`, tránh tình trạng `staged files != --files targets` hoặc `targets without working-tree changes`.
