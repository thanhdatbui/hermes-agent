# Remote Dispatch Telemetry, Strict Assertion Discipline & Pre-Push Commit Rebinding

Bài học từ ca chốt phiên thực tế 2026-10-08 trên repo `tiktok-luot nuoi acc` (vượt ngưỡng 84/100 kẹt lên 87/100 APPROVED và vượt qua Pre-Push Hook).

---

## 1. KHẮC PHỤC ĐIỂM NGHẼN REVIEWER 84/100 (THE SUBPROCESS & ASSERTION TRAP)

Khi Closeout Gate bị kẹt ở điểm số 84/100 (ngưỡng APPROVED là >= 85), Reviewer Sol Auditor (:20129) thường nhắm vào 3 điểm cốt tử:

### 1.1 Cấm làm mềm Assertion trong Unit Test (Anti-Softened Assertion)
- **Bẫy thường gặp**: Khi code thay đổi trả về status mới hoặc khi muốn test pass nhanh, developer đổi từ:
  ```python
  assert res["status"] == "skipped"
  ```
  sang dạng nới lỏng:
  ```python
  assert res["status"] in ("skipped", "failed")
  ```
- **Reviewer bắt lỗi**: Sol Auditor sẽ trừ điểm nặng ở mục `Test Evidence` và `Farm Safety / Regression` vì coi đây là hành vi hạ thấp hàng rào bảo vệ (weaken regression contract), dẫn đến bị kẹt điểm ở 84/100.
- **Quy chuẩn**: Giữ nguyên assertion nghiêm ngặt và đơn nhất (`assert res["status"] == "skipped"`). Nếu logic sinh ra nhánh khác, phải mock hoặc setup test fixture chuẩn xác để rơi đúng vào trạng thái kỳ vọng.

### 1.2 Cấu hình hóa các tham số Remote Execution (Configurable Over Hardcoding)
- **Bẫy thường gặp**: Hardcode chuỗi SSH target (`"admin-farm"`), repo path (`r"D:\Taadaa\tiktok-video"`), hoặc Python executable (`r"D:\Taadaa\python-envs\..."`).
- **Khắc phục**: Luôn ưu tiên đọc từ context config trước khi fallback về hằng số mặc định:
  ```python
  admin_python = ctx.config.get("admin_python_exe") or r"D:\Taadaa\python-envs\automation\Scripts\python.exe"
  admin_repo = ctx.config.get("admin_video_repo") or r"D:\Taadaa\tiktok-video"
  admin_ssh_target = ctx.config.get("admin_ssh_target") or "admin-farm"
  admin_wb = str(ctx.config.get("admin_workflow_workbook") or workbook_path).replace("/", "\\")
  admin_media = str(ctx.config.get("admin_media_source_root") or media_root).replace("/", "\\")
  ```

### 1.3 Telemetry toàn diện cho Subprocess Lifecycle & Silent Exception Handling
- **Bẫy thường gặp**: Chạy `subprocess.run` nhưng không đo thời gian chạy, không log sự kiện bắt đầu/kết thúc, hoặc bọc ngoại lệ bằng `except Exception: pass` khi đọc artifact remote qua SSH.
- **Khắc phục**:
  1. Ghi log chuẩn bị: `logger.info("[UPLOAD_HOOK_TELEMETRY] event=remote_admin_dispatch_prepared ...")`.
  2. Bọc timing vòng đời:
     ```python
     _subproc_start_mono = time.monotonic()
     logger.info("[UPLOAD_HOOK_TELEMETRY] event=upload_subprocess_started ...")
     try:
         proc = subprocess.run(...)
         _duration = time.monotonic() - _subproc_start_mono
         logger.info("[UPLOAD_HOOK_TELEMETRY] event=upload_subprocess_finished duration=%.2fs ...", _duration)
     except subprocess.TimeoutExpired:
         _duration = time.monotonic() - _subproc_start_mono
         logger.warning("[UPLOAD_HOOK_TELEMETRY] event=upload_subprocess_timeout duration=%.2fs ...", _duration)
     ```
  3. Khi SSH fetch artifact thất bại hoặc ném exception, ghi log cảnh báo chi tiết thay vì `pass` im lặng:
     ```python
     except Exception as _ssh_err:
         logger.warning("[UPLOAD_HOOK_TELEMETRY] event=remote_admin_report_ssh_error error=%s", str(_ssh_err))
     ```
  4. Trả telemetry `duration_seconds` và các cờ phân loại (`is_admin`) trực tiếp trong result payload.

---

## 2. KỶ LUẬT PRE-PUSH COMMIT REBINDING (TRÁNH LỖI COMMIT MISMATCH KHI PUSH)

### 2.1 Cơ chế kiểm tra của `.git/hooks/pre-push`
Pre-push hook kiểm tra dòng cuối cùng trong `D:/Taadaa/logs/gate_audit.jsonl`:
- `entry["verdict"] == "APPROVED"`
- `entry["score"] >= 85`
- `entry["audit_binding"]["commit_sha"] == git rev-parse HEAD`
- `entry["audit_binding"]["scope"] == current_diff_scope`

### 2.2 Bẫy Commit Mismatch & Non-Fast-Forward Push
- Khi sửa code sau review hoặc khi `git commit --amend`, commit SHA thay đổi. Nếu chạy `git push` ngay, hook sẽ báo:
  `❌ [BLOCKED - PRE-PUSH HOOK]: Gate check FAILED — commit mismatch`
- Nếu push bị remote reject do non-fast-forward (`[rejected] master -> master (non-fast-forward)`), developer thường `fetch` rồi `reset` hoặc merge, tạo commit SHA mới.
- **Quy tắc bất biến**:
  1. Chỉ chạy `closeout_gate.py` **SAU KHI** commit cuối cùng của branch đã được tạo trên đúng HEAD hiện tại và đã đồng bộ với remote tracking.
  2. Sau khi amend hoặc tạo commit mới, **BẮT BUỘC chạy lại `closeout_gate.py --repo <repo> --base HEAD~1`** để ghi lại một dòng audit mới khớp 100% với commit SHA của HEAD trước khi chạy `git push`.
