# GPM CDP Connection Retry, Context Ownership & Canary Gate Discipline

## 1. CDP Connection Readiness & Port Retry
- **Triệu chứng**: Gọi `/api/v3/profiles/start/{id}` trả về `remote_debugging_address` (ví dụ `127.0.0.1:59014`) thành công ngay lập tức, nhưng Playwright gọi `p.chromium.connect_over_cdp(f"http://{cdp_addr}")` lập tức quăng lỗi `BrowserType.connect_over_cdp: connect ECONNREFUSED 127.0.0.1:59014`.
- **Nguyên nhân**: Process `chrome.exe` của GPM đang trong pha nạp DLL/extensions antidetect và chưa kịp mở socket lắng nghe DevTools Protocol.
- **Quy chuẩn**: BẮT BUỘC bọc `connect_over_cdp` trong vòng lặp retry 5 lần với `time.sleep(1)` trước khi fail-closed.
  ```python
  for _att in range(5):
      try:
          browser = p.chromium.connect_over_cdp(f"http://{cdp_addr}")
          if _att > 0:
              log_telemetry_metric("cdp_connection_retry", {"attempt": _att + 1, "max_attempts": 5})
          break
      except Exception:
          time.sleep(1)
  else:
      log_telemetry_metric("cdp_connection_retry_exhausted", {"attempts": 5})
      browser = p.chromium.connect_over_cdp(f"http://{cdp_addr}")  # final attempt, will raise
  ```

## 2. Fail-Closed Context Ownership (Cấm `new_context()` Fallback)
- **Cạm bẫy**: `ctx = browser.contexts[0] if browser.contexts else browser.new_context()`
- **Hậu quả**: Khi Playwright kết nối CDP nhưng vì race condition chưa kịp gắn vào session context chính của GPM profile, việc fallback sang `new_context()` âm thầm tạo một browser context trắng (blank/incognito), không có bất kỳ cookie hay storage nào đã lưu trong profile. Script sẽ ngỡ profile bị mất session và kích hoạt re-login/quarantine sai.
- **Quy chuẩn**: BẮT BUỘC fail-closed:
  ```python
  if not browser.contexts:
      raise RuntimeError(f"GPM CDP connected on {cdp_addr} but browser.contexts is empty")
  ctx = browser.contexts[0]
  ```

## 3. Phân Loại Telemetry Nguyên Nhân Lỗi GPM CDP (2026-10-22)
Khi kết nối GPM CDP thất bại, cần phân biệt 3 nguyên nhân khác nhau để debug được chính xác:
- **`gpm_start_failed`**: GPM Local API `/profiles/start/{id}` trả lỗi (API không thành công hoặc không có `remote_debugging_address`).
- **`cdp_connect_failed`**: API start thành công nhưng `connect_over_cdp` fail sau retry 5 lần (`connect_over_cdp` nằm trong traceback).
- **`cdp_contexts_empty`**: Connect CDP OK nhưng `browser.contexts` rỗng (race condition GPM chưa khởi tạo context chính).

```python
reason_code = (
    "cdp_contexts_empty" if "contexts is empty" in str(e)
    else ("cdp_connect_failed" if "connect_over_cdp" in str(e)
    else "gpm_start_failed")
)
log_telemetry_metric(reason_code, {"mid": mid, "email": email, "reason": str(e)})
```

## 4. Tách Biệt Tuyệt Đối Cleanup trong `finally:` (Login-Only vs Normal)
- **Cạm bẫy cũ (code chết logic)**: 
  ```python
  if gpm_started and gpm_profile_id:
      stop_gpm_profile(gpm_profile_id)
      gpm_started = False          # <- reset ngay sau stop
  if not gpm_started and prof_dir:  # <- luôn True sau bước trên!
      subprocess.run(["powershell", ...])  # <- always runs, kể cả login_only
  ```
  Lỗi: sau khi reset `gpm_started = False`, điều kiện `if not gpm_started` luôn True, PowerShell cleanup sẽ chạy ngay cả ở login-only mode.

- **Quy chuẩn đúng** — phân nhánh theo `login_only`, KHÔNG dựa vào `gpm_started` flag sau reset:
  ```python
  finally:
      if login_only:
          if gpm_started and gpm_profile_id:
              stop_gpm_profile(gpm_profile_id)   # Local API stop
          # CẤM PowerShell kill tiến trình trong login_only
      elif prof_dir:
          # Chỉ Normal mode mới dọn thư mục profile tạm qua PowerShell
          subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], ...)
  ```

## 5. Telemetry `stop_gpm_profile` Fail-Silent (Không Raise)
`stop_gpm_profile()` phải không bao giờ raise, nhưng bắt buộc emit telemetry khi fail:
```python
def stop_gpm_profile(profile_id: str):
    try:
        body = gpm_get(f"/profiles/stop/{profile_id}", timeout=15)
        if not body.get("success", True):
            log_telemetry_metric("gpm_stop_failed", {"profile_id": profile_id, "reason": str(body)})
    except Exception as e:
        logger.warning(f"GPM stop {profile_id} failed: {e}")
        log_telemetry_metric("gpm_stop_failed", {"profile_id": profile_id, "reason": type(e).__name__})
```

## 6. Canary Gate & Working Tree Hash — Pitfalls

### Canary Matrix (case-sensitive!)
- `canary_matrix.json` lookup là case-sensitive trên tên thư mục repo.
- `"gpm auto"` ≠ `"GPM auto"` — phải khớp chính xác với `Path(repo).name` của repo đang chạy.
- Triệu chứng: `CANARY_PLAN_UNAVAILABLE: "Repo 'GPM auto' chưa có trong matrix"`.
- Fix: thêm entry đúng tên vào matrix, mode `"shadow"` là đủ nếu không có hook-specific rules.

### Working Tree Hash Timeout
- Lệnh `git status --porcelain --untracked-files=all` trong `get_working_tree_diff_sha256()` có timeout 30s.
- Với repo GPM có hàng trăm untracked files (`checkmail_proxy_data_*`, `debug_screenshots/*`, `*.db`), nếu `.gitignore` không chặn đủ, git sẽ liệt kê hàng chục nghìn file → timeout → trả về `None` → `CANARY_COMMIT_VERIFY_FAILED`.
- Fix `.gitignore`: phải chặn directories bằng trailing `/` (không phải glob) để git tự cắt tỉa recursion:
  ```gitignore
  checkmail_browser_data/
  checkmail_proxy_data/
  checkmail_results/
  debug_screenshots/
  *.db
  ```
  Cẩn thận: `checkmail_*` không tương đương với `checkmail_browser_data/` — glob không chặn được recursion.

## 7. Kiểm Soát Diff & Sol Payload Truncation
- **Hiện tượng**: Reviewer Sol High trả về `NEED_CONTEXT:tests/...` và chấm 0 điểm dù test xanh 100%.
- **Nguyên nhân**: `sol_payload_guard.py` cắt tỉa diff hoặc log khi tổng kích thước vượt ngân sách `SOL_TARGET_BYTES` (~36KB, trong đó diff chiếm 80% ~28.8KB). Khi có hunks bị cắt tỉa, guard đóng dấu `[TRUNCATION_MANIFEST]`.
- **Giải pháp**:
  - Gộp các unit test trùng lặp bằng `pytest.mark.parametrize` và context manager tập trung để khống chế diff `< 28KB`.
  - Xóa warning deprecation (`pydub`, `speech_recognition`, `pytest_asyncio`) khỏi test suite bằng `filterwarnings` trong `pytest.ini` hoặc `conftest.py` — KHÔNG dùng `warnings.filterwarnings("ignore")` đầu file test (che cả lỗi thật).
  - Cân nhắc tách thành 2 lần closeout nếu diff tổng > 28KB.
