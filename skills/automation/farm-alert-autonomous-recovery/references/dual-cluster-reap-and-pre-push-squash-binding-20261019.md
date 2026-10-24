# Dual-Cluster Lock Reaping & Pre-Push Scope Binding Protocol (2026-10-19)

## 1. Dual-Cluster Device Lock Reaping Architecture
- **Triệu chứng**: Batch feed/upload hoặc automation trên cụm Farm Admin (Máy 201-280) đồng loạt thất bại với lỗi `ACQUIRE_LOCKS` / `device needs user decision (locked by another owner)`.
- **Nguyên nhân gốc**: Admin-PC (`192.168.110.119`) không có tiến trình Hermes gateway/daemon chạy thường trực. Khi các script trên Admin-PC thoát ngang (crash/kill), các lock file tồn lưu vĩnh viễn trong `C:\Users\Admin\.codex\device-locks\`.
- **Kỷ luật Dual-Cluster**:
  - Script dọn lock `scripts/reap-dead-owner-locks.py` chạy từ Kibe bắt buộc tích hợp cơ chế `_maybe_reap_admin_remote()` qua `tools/admin_ssh.py`.
  - Kiểm tra danh tính host chặt chẽ qua `taadaa_host.load_host_config()` kết hợp biến môi trường:
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
  - Quoting chuẩn trên PowerShell: Lệnh SSH gọi PowerShell phải bọc đường dẫn script trong nháy đơn để an toàn khi có khoảng trắng:
    `python tools/admin_ssh.py --powershell "python 'D:/Taadaa/tiktok-luot nuoi acc/scripts/reap-dead-owner-locks.py'"`
  - `_maybe_reap_admin_remote()` bắt buộc nằm trong khối `finally:` của `main()` để luôn được kích hoạt trên mọi luồng thoát (kể cả khi đĩa Kibe sạch hoặc gặp lỗi cục bộ). Ghi nhận telemetry `duration_s`.

## 2. Subprocess Stderr Masking & Unmasking Pattern
- **Bẫy trích xuất stderr**: Các lệnh thực thi qua SSH hoặc module nạp `taadaa_host.py` luôn in thông tin môi trường ra `stderr`:
  - `Warning: Permanently added '192.168.110.119' ...`
  - `[HOST] host=admin machines=200-999 workbook_root=...`
- **Quy tắc trích xuất an toàn (`_extract_upload_subprocess_error`)**:
  - CẤM TUYỆT ĐỐI lấy mù `lines[-1]` của `stderr`.
  - Bắt buộc lọc bỏ các dòng bắt đầu bằng `[HOST]`, `warning:`, hoặc chứa `permanently added`.
  - Quét `stdout` từ dưới lên để tìm các marker lỗi nghiệp vụ đích thực: `[NEEDS_USER_DECISION]`, `Workflow failed:`, `[ERROR]`, `[CRITICAL]`, `>>> state:`.

## 3. Pre-Push Scope-Binding Invariant (Single-Commit Squash Rule)
- **Cơ chế Hook**: File `.git/hooks/pre-push` trong các repo Taadaa kiểm tra `gate_audit.jsonl` theo điều kiện nghiêm ngặt:
  - `binding.get('commit_sha') == git rev-parse HEAD`
  - `binding.get('scope_hash') == sha256(git diff-tree --no-commit-id --name-only -r HEAD)`
- **Bẫy nhiều commit trong phiên (Multi-commit trap)**:
  - Nếu Coordinator thực hiện nhiều commit nhỏ trong quá trình vá lỗi (VD: 5 commits), lệnh `closeout_gate.py --base HEAD~5 --files ...` sẽ ghi nhận `scope_hash` cho toàn bộ 4 file trong 5 commit.
  - Tuy nhiên, khi `git push`, hook chạy `diff-tree -r HEAD` chỉ thấy các file thuộc về commit cuối cùng, làm lệch `scope_hash` -> **PRE-PUSH HOOK BLOCKED**.
- **Quy trình chuẩn trước khi Closeout Push**:
  - Trước khi chạy closeout gate chốt phiên, nếu phiên có từ 2 commits trở lên:
    `git reset --soft origin/master`
    `git commit -m "..."`
  - Đảm bảo toàn bộ scope sửa đổi nằm trọn vẹn trong đúng 1 commit duy nhất tại `HEAD`.
  - Chạy `closeout_gate.py --repo <path> --base HEAD~1 --files <files> --push`.
