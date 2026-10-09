# Closeout Gate: Staged Scope Matching and Diff Truncation Remediation

## 1. Vấn đề "Staged files != --files targets"
Khi chạy `closeout_gate.py --files <path1> <path2>`, hàm `targeted_candidate` kiểm tra nghiêm ngặt:
```python
staged = _z_paths(_git_bytes(repo, "diff", "--cached", "--name-only", "-z"))
if staged and staged != targets:
    raise ValueError(f"staged files {staged} != --files targets {targets}; unstage extras or adjust --files")
```
Nếu có file từ task trước vô tình bị staged trong index, Closeout Gate sẽ lập tức từ chối chạy review với lỗi `Failed to extract diff`.

### Khắc phục:
Reset các file ngoài lề khỏi git index trước khi chạy Closeout Gate:
```bash
git -C <repo> reset HEAD -- <unrelated_files_or_dir>
# Hoặc reset toàn bộ index rồi chỉ stage đúng danh sách target:
git -C <repo> reset HEAD
git -C <repo> add <target1> <target2>
```

---

## 2. Bẫy Diff Truncation (> 60KB) khiến Sol trừ điểm
Khi diff quá lớn (> 60KB, ví dụ file monolith 800+ dòng), `closeout_gate.py` tự động cắt ngắn diff:
`[... diff truncated due to size limit ...]`
Reviewer (Sol High :20129) sẽ trừ điểm nặng ở tiêu chí **Logic Correctness** và **Farm Safety** vì không thấy được toàn bộ code thực thi ("diff bị truncation nên chưa thể xác minh toàn bộ logic thực thi").

### Khắc phục:
1. **Cô lập scope tối thiểu**: Chỉ đưa các file có thay đổi thực sự trong phiên vào danh sách staged.
2. **Kẹp unit test nhỏ gọn và bao phủ**: Đảm bảo diff của file test súc tích, test trực tiếp các branch quan trọng (idempotency, runtime behavior, error recovery).
3. **Giữ diff < 50KB** để Sol quan sát được 100% diff mà không bị truncation flag.

---

## 3. Tiêu chí Windows Directory Junction & Setup Script
Khi refactor từ copy thư mục sang `mklink /J`:
1. **Kiểm tra ReparsePoint**:
   `$Existing.Attributes -band [System.IO.FileAttributes]::ReparsePoint`
   Nếu là thư mục thường thì throw error, cấm dùng `rmdir` xóa nhầm dữ liệu thật.
2. **Xóa junction an toàn**:
   Dùng `cmd.exe /d /c "rmdir \"$TargetJunc\""` (chỉ xóa con trỏ junction, không xóa đích).
3. **Bắt mã lỗi mklink**:
   Kiểm tra `if ($LASTEXITCODE -ne 0) { throw ... }`.
4. **Viết test hành vi runtime thật**:
   Không chỉ test string matching trên source code PowerShell; viết test chạy `mklink /J` thật trong `tempfile.TemporaryDirectory()` để chứng minh tính năng trên Windows.
