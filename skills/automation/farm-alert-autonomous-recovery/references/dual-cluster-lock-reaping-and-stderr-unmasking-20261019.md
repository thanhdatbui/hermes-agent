# Dual-Cluster Lock Reaping, Subprocess Stderr Unmasking & Pre-Push Single-Commit Binding

> Date: 2026-10-19
> Scope: Farm Admin (M201-280) & Kibe (M1-80), `tiktok-luot nuoi acc`, `closeout_gate.py`

## 1. Hiện tượng & Vấn đề thực tế

### Sự cố 1: 72/80 máy cụm Admin (M201-280) đồng loạt báo lỗi UploadHook
- **Signature báo cáo**: `UploadScriptError:UploadHook: [HOST] host=admin machines=200-999 workbook_root=D:\OneDrive\TaadaaData\admin runtime=D:\Taadaa\runtime\admin`
- **Thực tế ngầm**: Batch lướt feed hoàn thành 100% (swipes 16-22). Đến cuối ca gọi hook upload (`_run_upload_hook`), toàn bộ máy bị chặn bởi `[NEEDS_USER_DECISION] ACQUIRE_LOCKS`.
- **Nguyên nhân gốc**:
  1. Ngày hôm trước (18/10), tác vụ `tiktok-add-bao-mat-f2a` chạy trên Admin-PC thoát đột ngột, bỏ lại 148 file lock rác trong `C:\Users\Admin\.codex\device-locks\`.
  2. Cron reaper (`reap-dead-owner-locks.py`) chạy trên Kibe chỉ quét `Path.home() / ".codex" / "device-locks"` cục bộ, hoàn toàn "mù" cụm Admin-PC.
  3. Hàm bóc tách lỗi `_extract_upload_subprocess_error()` đọc stderr và lấy mù dòng cuối cùng (`lines[-1]`). Do SSH và `taadaa_host` luôn in `[HOST]` và SSH warnings ra stderr, thông tin này che lấp toàn bộ lỗi thật trong stdout (`[NEEDS_USER_DECISION] ACQUIRE_LOCKS`).

---

## 2. Quy chuẩn khắc phục chuẩn hóa

### A. Dual-Cluster Lock Reaping (`scripts/reap-dead-owner-locks.py`)
- Mỗi lần cron chạy reaper trên Kibe, sau khi dọn xong máy cục bộ, bắt buộc kích hoạt `_maybe_reap_admin_remote()` qua `admin_ssh.py --powershell "python 'D:/Taadaa/tiktok-luot nuoi acc/scripts/reap-dead-owner-locks.py'"`.
- Bắt buộc kiểm tra danh tính host trước khi gọi remote:
  ```python
  try:
      from python_runner.taadaa_host import load_host_config
      if str(load_host_config().get("host_id") or "").strip().lower() == "admin":
          return
  except Exception:
      pass
  if "admin" in str(Path.home()).lower() or os.environ.get("HOST_ID", "").startswith("admin"):
      return
  ```
- Đo lường telemetry `duration_s` và bắt buộc bảo đảm `_maybe_reap_admin_remote()` được gọi trong khối `finally:` của `main()` để không bao giờ bị bỏ qua khi có lỗi cục bộ.

### B. Lọc Stderr & Unmask Real Errors (`python_runner/flows/multi_machine_feed_session.py`)
- Khi bóc tách lỗi từ tiến trình con, CẤM lấy mù `lines[-1]` của stderr.
- BẮT BUỘC lọc bỏ các dòng thông tin lành tính:
  - Dòng cấu hình: `l.startswith("[HOST]")`
  - Dòng cảnh báo SSH / key: `l.lower().startswith("warning:")`, `"permanently added" in l.lower()`
- Đồng thời ưu tiên trích xuất lỗi nghiệp vụ từ stdout:
  `if any(k in line_lower for k in ("[error]", "[critical]", "workflow failed", "needs_user_decision")):`

---

## 3. Quy tắc Pre-Push Hook & Single-Commit Scope Binding

### Hiện tượng kẹt Gate khi Push
- Reviewer Sol High chấm APPROVED (Grace band 80-84 hoặc >= 85), nhưng `git push` bị chặn đứng bởi hook:
  `❌ [BLOCKED - PRE-PUSH HOOK]: Gate check FAILED — Không tìm thấy bản ghi Closeout Gate APPROVED >= 80 cho commit hiện tại!`

### Nguyên nhân
- Hook `.git/hooks/pre-push` tính `current_scope` bằng lệnh:
  `git diff-tree --no-commit-id --name-only -r HEAD` (chỉ xét duy nhất commit ở đỉnh HEAD).
- Sau đó hook đối chiếu:
  `if sorted(binding.get('scope', [])) == current_scope and binding.get('scope_hash') == scope_hash(current_scope):`
- Nếu phiên làm việc có nhiều commit nhỏ (ví dụ commit sửa code riêng, commit sửa test riêng), `closeout_gate.py --base HEAD~N --files ...` ghi nhận audit log chứa toàn bộ N files, nhưng commit HEAD chỉ chứa 1-2 files cuối cùng -> `scope` không khớp -> PRE-PUSH HOOK TỪ CHỐI CHO PUSH.

### Kỷ luật bắt buộc
- **BẮT BUỘC SQUASH / AMEND VỀ 1 COMMIT DUY NHẤT** trước khi chạy lệnh closeout gate cuối cùng:
  ```bash
  git reset --soft origin/master
  git commit -m "fix(scope): <thông điệp mô tả toàn bộ thay đổi>"
  python D:/Taadaa/tools/closeout_gate.py --repo <path> --base origin/master --files <tất cả files> --push
  ```
- Điều này bảo đảm `commit_sha`, `current_scope` của HEAD khớp chính xác 100% với `audit_binding` được ghi nhận trong `gate_audit.jsonl`, push sẽ thành công ngay lập tức.
