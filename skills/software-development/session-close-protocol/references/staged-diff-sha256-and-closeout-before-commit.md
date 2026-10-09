# Staged Diff SHA256 & Closeout-Before-Commit Architecture (2026-10-02)

## 1. Bối cảnh & Rủi ro Cũ
- Trước đây: Quy trình cho phép commit trước rồi mới chạy `closeout_gate.py` so sánh `HEAD` với `HEAD~1`.
- Rủi ro phát hiện bởi Claude CLI & Sol Reviewer:
  1. **Commit trộm trước kiểm duyệt**: Worker hoặc Coordinator có thể tạo commit rác/chưa đạt chuẩn trước khi có phán quyết của Giám khảo.
  2. **Tree vs Diff Mismatch**: Sau khi closeout đạt, có thể có thêm chỉnh sửa unstaged lọt vào working tree nhưng không nằm trong diff đã được review.
  3. **Lạm dụng commit**: Dùng `--no-verify` hoặc `--amend` để tráo đổi nội dung commit sau khi closeout đã cấp cờ.

---

## 2. Quy trình Chuẩn Hóa: "Closeout trước, commit sau"

### Bước 1: Worker thi công, cấm tự commit
- Worker subagent nhận task thi công trong phạm vi Scope Lock (`<= 30 dòng diff`, 1 file code + 1 file test).
- Worker chạy focused test verify đạt `< 30s`.
- **CẤM Worker gọi `git commit`**. Worker trả kết quả cho Coordinator.

### Bước 2: Coordinator staging đúng phạm vi
- Coordinator kiểm tra `git status` và `git diff`.
- Sử dụng `git add <file1> <file2>` để đưa đúng các file cần đóng gói vào staging area (`git diff --cached`).

### Bước 3: Thẩm định Staged Binding qua `closeout_gate.py`
- Lệnh chạy:
  ```bash
  python D:/Taadaa/tools/closeout_gate.py --repo <đường_dẫn_repo> --json-output
  ```
- **Cơ chế Staged Binding (`resolve_audit_binding`)**:
  ```python
  HERMETIC_GIT_CONFIG = ("-c", "core.fsmonitor=", "-c", "core.hooksPath=NUL")

  def staged_diff_sha256(repo: Path) -> str:
      result = subprocess.run(
          ["git", *HERMETIC_GIT_CONFIG, "-C", str(repo), "diff", "--cached", "--binary",
           "--no-color", "--no-ext-diff", "--no-textconv"],
          capture_output=True, timeout=30,
      )
      return hashlib.sha256(result.stdout).hexdigest()
  ```
- **Chặn Mismatch tuyệt đối**:
  - So sánh `staged = git diff --cached --name-only` và `dirty = git diff --name-only`.
  - Nếu `overlap = set(staged) & set(dirty)` tồn tại: REJECT ngay với lỗi `binding mismatch: staged files also have unstaged edits (tested tree != reviewed diff)`.
  - Tính SHA256 byte-level của staged diff và lưu vào `audit_binding`.

### Bước 4: Ghi nhận Audit Log & Cấp phép Commit
- Khi Sol Reviewer trả về `Overall Score >= 85` và `Verdict: APPROVED`:
  - `closeout_gate.py` ghi entry mới vào `D:/Taadaa/logs/gate_audit.jsonl` kèm chuỗi băm SHA256 chain và `audit_binding`.
  - Guard plugin (`farm-coordinator-guard`) đọc xác thực `gate_audit.jsonl` và cấp phép cho `git commit`.

### Bước 5: Coordinator Commit & Báo cáo User
- Coordinator thực hiện commit chuẩn:
  ```bash
  git commit -m "<type>(<scope>): <mô tả>"
  ```
- Cờ `closeout_passed` tự động reset về `False` ngay sau commit để chống commit nối.
- **CẤM Coordinator gọi `git push`** — Quyền push duy nhất thuộc về User sau khi xem báo cáo nghiệm thu.

---

## 3. Pitfall: Local Proxy Catching OmniRoute Endpoint
- **Hiện tượng**: `closeout_gate.py` gọi OmniRoute tại `http://127.0.0.1:20129/v1/chat/completions` bị timeout hoặc connection refused.
- **Nguyên nhân**: Biến môi trường hệ thống (`HTTP_PROXY`, `ALL_PROXY`, proxy của VPN/Singbox) bắt gói tin local.
- **Khắc phục**: Trong `resolve_omni_url()` của `closeout_gate.py`, luôn ép:
  ```python
  os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1,192.168.110.123")
  os.environ.setdefault("no_proxy", "localhost,127.0.0.1,192.168.110.123")
  ```

---

## 4. Kiểm chứng Hồi quy
- Suite `D:/Taadaa/tools/test_closeout_guard_integration.py` chứa test cases:
  - `test_staged_diff_sha256_and_binding_integrity`: Kiểm thử tính toán hash, resolve binding, và bắt lỗi overlap staged/unstaged.
  - `test_resolve_omni_url_sets_no_proxy`: Kiểm thử tự động gán `NO_PROXY`.
  - Chạy `pytest D:/Taadaa/tools/test_closeout_guard_integration.py` đạt 25/25 passed.
