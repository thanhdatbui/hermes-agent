# Staged Candidate Binding & Unstaged Overlap Remediation (2026-10-09)

## 1. Triệu chứng & Lỗi Thực tế
Khi chạy Closeout Gate trước khi commit:
```bash
python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/tiktok-luot nuoi acc" --base HEAD --json-output
```
Cổng bị dừng ngay lập tức tại **STEP 2: EXTRACT CANDIDATE DIFF** với exit code 1:
```text
  · Không có staged diff, thử git diff HEAD...
  · Extracted diff: 2 file(s), 4825 chars
  ✔ Extracted valid diff: 2 file(s), 4825 chars, sha256=730ab23aced6b9dc
  ✘ binding mismatch: staged/working-tree candidate overlaps committed HEAD
```

---

## 2. Nguyên nhân Cốt lõi (Root Cause trong `closeout_gate.py`)
Trong hàm `resolve_audit_binding`:
```python
    staged = _z_paths(_git_bytes(repo, "diff", "--cached", "--name-only", "-z"))
    dirty = _z_paths(_git_bytes(repo, "diff", "--name-only", "-z"))
    if staged:
        # Staged candidate (closeout BEFORE commit): bind to HEAD + exact staged diff bytes.
        overlap = set(staged) & set(dirty)
        if overlap:
            return None, f"binding mismatch: staged files also have unstaged edits {sorted(overlap)} (tested tree != reviewed diff)"
        ...
        return {"mode": "staged", ...}, ""

    head = _z_paths(_git_bytes(repo, "diff-tree", "-z", "--root", "-m", "--no-commit-id", "--name-only", "-r", "HEAD"))
    committed, foreign = set(head), set(staged + dirty)
    if not head or set(candidate_scope) != committed or foreign & committed:
        return None, "binding mismatch: staged/working-tree candidate overlaps committed HEAD"
```
- Khi các file sửa đổi **chưa được stage** (`staged` rỗng):
  - Gate rơi xuống nhánh fallback giả định đây là lượt review của commit đã tạo (`committed HEAD`).
  - Tuy nhiên, vì các file đang có thay đổi trong working tree (`dirty` không rỗng), tập `foreign & committed` phát hiện có file dirty trùng với HEAD của repo.
  - Hậu quả: Gate ném lỗi fail-closed `binding mismatch: staged/working-tree candidate overlaps committed HEAD`.

---

## 3. Quy chuẩn Khắc phục Chuẩn hóa (The Staged Audit Binding Rule)
Để thực hiện Closeout Gate hợp lệ **TRƯỚC KHI COMMIT** (theo đúng Invariant: Gate APPROVED mới được phép commit & push):
1. **BẮT BUỘC STAGE CÁC FILE SỬA ĐỔI:**
   ```bash
   git add <file1> <file2>
   ```
2. **ĐẢM BẢO KHÔNG CÒN UNSTAGED EDITS TRÊN CÁC FILE ĐÓ:**
   - Kiểm tra `git diff --name-only -- <file1> <file2>` phải rỗng.
   - Nếu còn unstaged edits đè lên file đã stage, gate sẽ văng lỗi `staged files also have unstaged edits (tested tree != reviewed diff)`.
3. **TRUYỀN TƯỜNG MINH `--files` VÀO CLOSEOUT GATE:**
   ```bash
   python D:/Taadaa/tools/closeout_gate.py --repo "<repo>" --files <file1> <file2> --json-output
   ```
   - Lệnh này kích hoạt hàm `targeted_candidate`:
     - Xác nhận `staged == targets`.
     - Xác nhận `dirty` trên `targets` rỗng.
     - Trả về mode `staged` an toàn, bỏ qua hoàn toàn các file rác/untracked khác trong repo (như thư mục `data/`).
