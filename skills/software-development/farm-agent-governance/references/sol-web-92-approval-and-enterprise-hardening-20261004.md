# Sol Web 92/100 Architectural Approval & Enterprise Hard Enforcement Remediation (2026-10-04)

## Bối cảnh và Thách thức Kiểm toán
Trong đợt thẩm định độc lập kiến trúc Hard Enforcement toàn diện trên đàn 80–160 thiết bị Taadaa Phone Farm, Chief Auditor Sol Web (:20129) ban đầu chỉ chấm **58/100 (REJECT)** vì chỉ ra 4 lỗ hổng chí tử của giải pháp Local Pre-Commit Hook đơn thuần:
1. `git commit --no-verify` hoàn toàn bỏ qua local hook (`pre-commit` không phải security boundary).
2. `core.hooksPath` có thể bị chuyển hướng về `/dev/null`.
3. File guard có thể bị sửa đổi ngay trong cùng commit nếu nằm cùng repo (`untrusted verifier`).
4. Kiểm tra Regex đơn thuần là lexical matching, dễ bị né bởi dynamic import, indirect variable, split string hoặc catch-all wrapper.

Sau khi tái cấu trúc và hoàn thiện theo mô hình 3 Cửa Ngõ Bất Biến (Three-Tier Enforcement), Sol Web đã chính thức cấp phán quyết:
**STATUS: APPROVED — SCORE: 92/100 (Pass có điều kiện)**.

---

## Mô hình 3 Cửa Ngõ Bất Biến (Three-Tier Enforcement Model)

```
                     ┌─────────────────────────────────┐
                     │ Policy / Anti-Skip Invariants   │
                     │ (D:/Taadaa/tools/guard_*.py)    │
                     └────────────────┬────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              ▼                       ▼                       ▼
      CỬA 1: LOCAL HOOK       CỬA 2: FOCUSED TESTS    CỬA 3: CLOSEOUT GATE
    (.git/hooks/pre-commit)   (Pytest Golden Matrix)   (closeout_gate.py)
              │                       │                       │
      Feedback lập tức        Chống hồi quy pixel      TRẠM THẨM ĐỊNH TỐI CAO
       khi Agent gõ lệnh      giữa các đời máy         Độc lập, duyệt >= 85 mới
              │                       │                được phép PUSH
              └───────────────────────┼───────────────────────┘
                                      ▼
                           MÁY THẬT ĐƯỢC BẢO VỆ
```

---

## Chi tiết 7 Tiêu chí Nghiệm thu A1–A7 (Sol Web Rubric 100 Điểm)

### A1 / P1 — Adversarial Anti-Skip Coverage (12/15)
- Không chỉ bắt 7 literal regex cơ bản mà mở rộng sang bao phủ toàn bộ semantic evasion:
  - Gán biến trung gian (`tmp = "SKIPPED_"; status = tmp`)
  - Ghép chuỗi (`status = "SKIP" + "PED_AVATAR"`)
  - Nuốt lỗi qua wrapper hoặc hàm tiện ích ngoại vi
  - Fallback unhandled error trả về `True`
  - Catch-all exception (`except Exception: return True`)
- **Positive Allowlist Invariant:** Trạng thái `PASS` chỉ tồn tại khi toàn bộ invariant nghiệp vụ được chứng minh. Mọi trạng thái `UNKNOWN`, `ERROR`, `SKIPPED`, `TIMEOUT`, `PARSE_ERROR` đều bắt buộc fail-closed $\rightarrow$ **REJECT**.

### A2 / P0 — Anti-TOCTOU & Artifact Binding (18/20)
- **Lỗ hổng TOCTOU (Time-of-Check to Time-of-Use):** Agent đưa commit A đi kiểm tra tại T1, nhưng tại T2 sửa sang commit B và đẩy lên farm tại T3.
- **Biện pháp cưỡng chế:** Mỗi đánh giá của Closeout Gate được gắn chặt với cryptographic context:
  ```python
  commit_sha = git_rev_parse("HEAD")
  tree_sha = git_rev_parse("HEAD^{tree}")
  guard_sha256 = sha256(guard_file)
  sol_score = score
  audit_entry = sha256(f"{commit_sha}:{tree_sha}:{guard_sha256}:{sol_score}:{timestamp}")
  ```
- Release Runner kiểm tra live git tree trước khi push: Nếu `commit_sha` hoặc `tree_sha` không khớp với audit chain entry $\rightarrow$ **Hủy lệnh lập tức (TOCTOU_DETECTED)**.

### A3 / R0 — Guard Integrity & Pinned Hash (15/15)
- **Vấn đề:** Agent có thể sửa file `guard_selector_change.py` trong repo để tự pass.
- **Biện pháp cưỡng chế:**
  - Chuyển guard thành Hash-Pinned Immutable Artifact.
  - `closeout_gate.py` trước khi thực thi guard bắt buộc tính `SHA-256` của `D:/Taadaa/tools/guard_selector_change.py` và đối chiếu với pinned hash bất biến.
  - Sai lệch dù 1 byte $\rightarrow$ **GUARD_INTEGRITY_COMPROMISED (Exit 1)**.
  - Áp dụng NTFS Write-Deny ACL trên host Windows để chặn quyền ghi của agent process.

### A4 — Hook Tampering Immunity (9/10)
- Closeout Gate hoàn toàn độc lập với `.git/hooks/` và `core.hooksPath`.
- Dù Agent có xóa file hook, sửa hook thành `exit 0`, hoặc dùng `git commit --no-verify` $\rightarrow$ Khi đến Closeout Gate ở bước cuối, script vẫn tự gọi bộ guard bên ngoài để quét toàn bộ diff.

### A5 — Cross-Repo Single Source of Truth (10/10)
- Triệt tiêu hoàn toàn các bản sao `guard_selector_change.py` phân mảnh trong từng repo con.
- Toàn bộ 5 repo consumer (`Tiktok-video`, `tiktok-follow`, `tiktok-add-bao-mat-f2a`, `tiktok-luot nuoi acc`, `Tiktok_Reg`) đều chia sẻ chung 1 verifier trung tâm duy nhất tại `D:/Taadaa/tools/`.

### A6 — Mandatory Release Gate (15/15)
- Mọi thao tác kết thúc phiên hay phát hành code lên farm bắt buộc có `exit_code == 0` từ `closeout_gate.py` và `Overall Score >= 85/100` từ Reviewer độc lập (Sol Web :20129 hoặc Claude CLI).
- Điểm số được khóa trong chuỗi hash `--verify-chain`, agent không thể tự bịa hay sửa file text để giả mạo điểm.

### A7 — Strict Fail-Closed (10/10)
- Mọi trường hợp subprocess crash, timeout, XML parser failure, rớt kết nối mạng hoặc thiếu dependency $\rightarrow$ **REJECT vô điều kiện**.
- Tuyệt đối không có nhánh `except: pass` hay fallback âm thầm cho qua.

---

## 3 Remediation Bắt buộc để Nâng Điểm từ 92 lên 100/100
1. **R0.1 (Signed Trust Manifest):** Thay thế so khớp hash trần bằng chữ ký số bất đối xứng (Ed25519) ký bởi private key độc lập không nằm trên farm controller.
2. **A6.1 (Signed Audit Chain):** Ký số từng block audit entry trong ledger.
3. **SEC.1 (Runtime Isolation):** Tách quyền thực thi: Agent chạy trong unprivileged context, chỉ có thể submit artifact; chỉ Verifier Service chạy bằng tài khoản đặc quyền mới có quyền kích hoạt lệnh release.
