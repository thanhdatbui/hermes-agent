# Numstat Diff Counting, Pre-Commit Audit Binding & Short-Circuit Invariants (2026-10-18)

## 1. Bối Cảnh & Vấn Đề Gốc Rễ
Trong phiên chốt closeout cho các công cụ farm, hệ thống gặp hiện tượng Coordinator bị đóng băng (paralysis) và báo `BLOCKED` do 4 mâu thuẫn cơ học giữa Gate và script push:
1. **Lỗi đếm dòng unified diff (RFC-1):** `closeout_gate.py` tính `diff_lines = len(diff_res.diff_text.splitlines())`. Số dòng header (`diff --git`, `index`, `---`, `+++`, `@@`) và context 3 dòng bị tính gộp, khiến patch 30 dòng code bị đội lên 150+ dòng, làm `gate_common` từ chối cấp Grace token (`grace_conditions_unmet`).
2. **Khóa bàn phím Strike 3 Handoff (RFC-2):** `write_handoff_lock` ghi cứng `"owner": "claude_cli"`. Khi Claude chạm trần Quota Guard 85%, câu chữ thông báo ép buộc chỉ dùng Claude khiến Coordinator không dám kích hoạt Antigravity pool (`ag_cli.py fix`).
3. **Quên `--files` gây `DIFF_TOO_LARGE` (RFC-3):** Khi repo có nhiều file dirty từ các tác vụ khác, việc quên `--files` khiến gate quét toàn bộ working tree (>82KB) và văng `DIFF_TOO_LARGE` thay vì nhắc nhở scope.
4. **Lệch SHA giữa Pre-Commit Gate và `safe_push.py` (RFC-4):** Gate chạy trước khi commit lưu `HEAD` cũ (commit cha). Sau khi commit, `safe_push` so sánh `HEAD` mới với audit log và từ chối push (`BLOCKED_GATE_NOT_APPROVED`).

---

## 2. Giải Pháp Cơ Học Đã Thi Công

### RFC-1: Đếm dòng thực tế theo Numstat
Thay vì `len(diff_text.splitlines())`, tính số dòng thêm và xóa thực tế:
```python
numstat_lines = sum(
    1 for l in diff_res.diff_text.splitlines()
    if (l.startswith('+') and not l.startswith('+++')) or (l.startswith('-') and not l.startswith('---'))
)
```
Loại bỏ hoàn toàn sự thổi phồng do header và context lines.

### RFC-2: Mở rộng Strike 3 sang Antigravity Pool
Trong `write_handoff_lock`, bổ sung:
```python
lock_data = {
    "owner": "claude_cli",
    "fallback_owner": "antigravity_pool",
    ...
}
```
Thông báo handoff nêu rõ: `Tier 1: Claude CLI hoặc Tier 2: Agy CLI (Antigravity pool)` để Coordinator tự động kích hoạt fallback khi Claude chạm quota.

### RFC-3: Fail-Fast Scope Guard ở Step 2
Nếu không có `--files` và số file dirty > 2:
```python
if not targets:
    undeclared = set(_z_paths(_git_bytes(repo_path, "diff", "--cached", "--name-only", "-z")))
    undeclared |= set(_z_paths(_git_bytes(repo_path, "diff", "--name-only", "-z")))
    if len(undeclared) > 2:
        err(f"[Gate Fail-Fast: SCOPE_NOT_DECLARED] {len(undeclared)} changed files without --files allowlist; pass --files <targets>")
        sys.exit(2)
```

### RFC-4: Đối Soát Pre-Commit Audit Binding trong `safe_push.py`
Trong `safe_push.py`, thêm hàm `_staged_diff_matches`:
- Kiểm tra `HEAD~1` khớp `parent_sha` (yêu cầu prefix tối thiểu 7 ký tự).
- Băm `git diff --binary -M -C --no-color --no-ext-diff HEAD~1..HEAD` và đối soát khớp byte-exact với `staged_diff_sha256` trong audit binding.
- Siết chặt Grace Band: Điểm 80-84 chỉ được duyệt khi `is_grace is True` (không nhận score >= 80 đơn thuần).

### Hardening Pre-Closeout Short-Circuit:
1. Bắt buộc có target tường minh: `if not targets: return False, "requires explicit non-empty targets"`.
2. Kiểm tra `HEAD == upstream` và không có drift đối với `base_ref`.
3. Bắt buộc chạy focused tests và yêu cầu `passed > 0` (cấm bypass khi `--skip-test` bật).
