# Upload Hook Auto-Login Recovery & Canary Gate Wiring

## 1. Hiện Tượng & Triệu Chứng Lỗi Farm Alert
- **Cảnh báo P0 giả lập văng phiên:** Watchdog batch quét từ khóa `ACCOUNT_MISSING` trong log và bắn còi đỏ P0 *"mất phiên / văng account"*, trong khi thực tế nick chưa từng được nạp vào máy hoặc slot Switcher còn thiếu (ví dụ máy mới nạp 7/8 nick).
- **Điểm đứt gãy giữa Feed Session và Upload Hook:**
  - Ở batch Upload độc lập (`run_tiktok_upload_batch.ps1`): Có sẵn nhánh bắt Exit Code 4 (`LOGIN_RECOVERY_REQUIRED`) để tự động nạp bù nick và retry.
  - Ở ca Nuôi Feed (`multi_machine_feed_session.py`): Subprocess upload khi gặp `rc == 4` trước đây chỉ dừng lại, gán `upload_failed` và bắn alert ra ngoài mà không tự động khôi phục.

## 2. Giải Pháp Chuẩn Hóa O(1) Cho Upload Hook
- Trong `python_runner/flows/multi_machine_feed_session.py`:
  ```python
  # Bắt Exit Code 4 (LOGIN_RECOVERY_REQUIRED do thiếu nick trong Switcher)
  if proc.returncode == 4 and not getattr(child_ctx, "_upload_login_recovered", False):
      setattr(child_ctx, "_upload_login_recovered", True)
      if isinstance(child_ctx.config, dict):
          child_ctx.config["_machine"] = account.machine
          child_ctx.config["machine"] = account.machine
      logger.warning(
          "[UPLOAD_HOOK] Machine %s hit LOGIN_RECOVERY_REQUIRED (rc=4); triggering auto-login recovery for %s...",
          account.machine, account_id
      )
      _login_ok = _maybe_recover_missing_account_via_login(child_ctx, account_id)
      if _login_ok:
          logger.info(
              "[UPLOAD_HOOK] Auto-login recovery succeeded for machine %s; retrying upload subprocess...",
              account.machine
          )
          proc = subprocess.run(command, **subp_kwargs)
          _subproc_duration = time.monotonic() - _subproc_start_mono
  ```
- **Kỷ luật an toàn:**
  - Cờ guard `_upload_login_recovered` trên context và cơ chế chặn trùng trong core recovery ngăn chặn tuyệt đối vòng lặp vô tận (infinite retry).
  - Tái sử dụng `_maybe_recover_missing_account_via_login` canonical, không viết lại script login ad-hoc.

## 3. Kỷ Luật Cơ Giới Hóa Canary Gate (Script Codification vs Memory)
- **User Invariant:** Tuyệt đối CẤM dùng LLM memory để lưu các quy tắc vận hành hay hướng dẫn truyền cờ script (`--allow-upload-hook`). Memory của LLM dễ trôi và vi phạm nguyên tắc cơ giới hóa farm.
- **Cơ giới hóa hạ tầng Gate:**
  1. `canary_matrix.json`: Khai báo rule ánh xạ rõ ràng:
     ```json
     {
       "id": "upload-hook",
       "path_globs": ["*upload*", "**/flows/*upload*", "**/flows/multi_machine_feed_session*"],
       "hook": "upload",
       "scope": "single"
     }
     ```
  2. `canary_runner.py`: Tự động gọi `canary_plan.build_canary_plan(repo_dir, DEFAULT_MATRIX)` khi người dùng không truyền `--hook`.
  3. **Bẫy quét đơn lẻ `reqs[0]` (Reviewer Finding):** Khi diff chạm nhiều file (ví dụ cả switcher và multi_machine_feed_session), `reqs[0]` sẽ chỉ lấy hook đầu tiên và bỏ rơi hook `upload`. Bắt buộc phải quét tập hợp bằng `any()`:
     ```python
     if any("upload" in str(r.get("hook", "")).lower() for r in reqs):
         auto_upload_hook = True
     ```
     Sau đó tự động append `--allow-upload-hook` xuống lệnh thực thi của farm.
