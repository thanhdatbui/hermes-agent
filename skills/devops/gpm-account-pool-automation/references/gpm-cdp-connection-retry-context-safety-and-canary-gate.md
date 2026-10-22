# GPM CDP Connection Retry, Context Ownership & Canary Gate Discipline

## 1. CDP Connection Readiness & Port Retry
- **Triệu chứng**: Gọi `/api/v3/profiles/start/{id}` trả về `remote_debugging_address` (ví dụ `127.0.0.1:59014`) thành công ngay lập tức, nhưng Playwright gọi `p.chromium.connect_over_cdp(f"http://{cdp_addr}")` lập tức quăng lỗi `BrowserType.connect_over_cdp: connect ECONNREFUSED 127.0.0.1:59014`.
- **Nguyên nhân**: Process `chrome.exe` của GPM đang trong pha nạp DLL/extensions antidetect và chưa kịp mở socket lắng nghe DevTools Protocol.
- **Quy chuẩn**: BẮT BUỘC bọc `connect_over_cdp` trong vòng lặp retry 5 lần với `time.sleep(1)` trước khi fail-closed.
  ```python
  for _att in range(5):
      try:
          browser = p.chromium.connect_over_cdp(f"http://{cdp_addr}")
          break
      except Exception:
          time.sleep(1)
  else:
      browser = p.chromium.connect_over_cdp(f"http://{cdp_addr}")
  ```

## 2. Fail-Closed Context Ownership (Cấm `new_context()` Fallback)
- **Cạm bẫy**: `ctx = browser.contexts[0] if browser.contexts else browser.new_context()`
- **Hậu quả**: Khi Playwright kết nối CDP nhưng vì race condition chưa kịp gắn vào session context chính của GPM profile, việc fallback sang `new_context()` âm thầm tạo một browser context trắng (blank/incognito), không có bất kỳ cookie hay storage nào đã lưu trong profile. Script sẽ ngỡ profile bị mất session và kích hoạt re-login/quarantine sai.
- **Quy chuẩn**: BẮT BUỘC fail-closed:
  ```python
  if not browser.contexts:
      raise RuntimeError(f"GPM CDP connected ({cdp_addr}) but browser.contexts is empty; cannot access profile session")
  ctx = browser.contexts[0]
  ```

## 3. Canary Gate & Working Tree Hash Timeout Tránh Bẫy Untracked Crawl
- **Cơ chế**: `done_gate.py` và `canary_runner.py` yêu cầu đối soát `tree_diff_sha256` qua `git status --porcelain --untracked-files=all`.
- **Cạm bẫy crawl đĩa**: Các repo GPM thường sinh ra hàng chục thư mục runtime lớn (`checkmail_proxy_data_*`, `debug_screenshots/*`, SQLite `*.db`). Nếu `.gitignore` chỉ ghi `checkmail_proxy_data/` mà không có wildcard `checkmail_*` hay `*.db`, lệnh git status sẽ quét đệ quy hàng chục nghìn file cache của browser, gây timeout 30s và làm `get_working_tree_diff_sha256()` trả về `None` dẫn đến `CANARY_COMMIT_VERIFY_FAILED`.
- **Quy chuẩn Matrix**: File `D:/Taadaa/tools/canary_matrix.json` bắt buộc khớp chính xác tên thư mục repo (case-sensitive: `"GPM auto"`), gán mode `"shadow"` và khai báo `exempt_globs` rõ ràng.

## 4. Kiểm Soát Diff & Test Log Tránh Bẫy Truncation Manifest (:20129)
- **Hiện tượng**: Reviewer Sol High trả về `NEED_CONTEXT:tests/...` và chấm 0 điểm dù test xanh 100%.
- **Nguyên nhân**: `sol_payload_guard.py` cắt tỉa diff hoặc log khi tổng kích thước vượt ngân sách `SOL_TARGET_BYTES` (~36KB, trong đó diff chiếm 80% ~28.8KB). Khi có hunks bị cắt tỉa, guard đóng dấu `[TRUNCATION_MANIFEST]` kèm ghi chú không được coi là đã review.
- **Giải pháp**:
  - Gộp các unit test trùng lặp bằng `pytest.mark.parametrize` và context manager tập trung để khống chế diff `< 28KB`.
  - Khử warning deprecation (vd `pydub`, `speech_recognition`, `pytest_asyncio`) trong test suite để test log ngắn gọn, không bị cắt xén.
