# ATX Session Unavailable Tại Bước sponsored_check & Fail-Soft Cho Heuristic Feed Checks (Case 121, 2026-09-06, Máy 36)

## Hiện trường sự cố (Evidence Máy 36)
- **Thiết bị**: Máy 36 | Serial: `ce10160ac8f1962305` | Nick: `jasomntqsso`
- **Thời gian**: 2026-09-06T09:10:22Z
- **Triệu chứng**: Phiên nuôi acc / lướt feed (`feed-session-smoke`) dừng đột ngột ngay sau khi vào Home Feed, hoàn thành 0 swipe (`total_swipes_completed: 0`), gán status `manual-needed`:
  ```text
  stop_reason: capture-invalid: ATX_SESSION_UNAVAILABLE artifact=D:\Taadaa\runtime\kibe\live\2026-09-06\row-4-151758\20260906-094205\machines\machine_36\20260906-094205\artifacts\device_8a620305b0\account_1b316b3aa7\sponsored_check
  ```
- **Hiện trạng máy thật**: TikTok vẫn đang mở bình thường tại Home Feed ('Đề xuất' For You) đang phát video, không hề crash hay văng app.

## Root Cause
1. **Lỗi `raise` trong `_capture_xml_text`**:
   - Khi uiautomator stub hoặc socket JSON-RPC bị nghẽn/timeout trên Android 7 (Samsung S7), tầng `capture_required_ui` ném `UIDumpError("ATX_SESSION_UNAVAILABLE")`.
   - Trong `python_runner/flows/feed_swipe_smoke.py`, hàm `_capture_xml_text` coi `ATX_SESSION_UNAVAILABLE` là `terminal_recovery` và thực hiện `raise` exception ra ngoài (dòng 1774) nhằm ngăn các heuristic profile identity / switch account kết luận nhầm là tài khoản không khớp.
2. **Thiếu recovery & try/except trong `_sponsored_present`**:
   - Tại đầu vòng lặp swipe mỗi video (`for swipe_count in range(1, selected_total_videos + 1)`), script kiểm tra:
     ```python
     if is_feed_session and not fast_swipe_focus_lost and _sponsored_present(ctx):
     ```
   - Hàm `_sponsored_present` gọi trực tiếp `_capture_xml_text(ctx, "sponsored_check")` mà KHÔNG có `try/except`.
   - Khi `UIDumpError` bị raise, exception văng thẳng lên `feed_session_smoke`, làm sập toàn bộ phiên lướt feed.
3. **Vi phạm nguyên tắc fail-soft của heuristic check**:
   - `sponsored_check` là kiểm tra phụ trợ nhằm skip video quảng cáo (Sponsored Ad) trên feed, KHÔNG PHẢI gate an toàn sống còn.
   - Việc để một heuristic check làm fail-stop toàn bộ phiên lướt video là lỗi thiết kế nghiêm trọng khi video feed vẫn đang phát bình thường.

## Giải pháp chuẩn hóa (3 Tầng)

### Tầng 1: Phục hồi ATX Session tại chỗ khi TikTok foreground
Trong `_sponsored_present(ctx)`:
- Kiểm tra `get_focused_activity(ctx)`. Nếu TikTok vẫn ở foreground (`cur_pkg in tiktok_pkgs`) và lỗi là `is_atx_failure`:
- Log `sponsored_check_atx_recovery` với `result="retry"`.
- Gọi `from automation_core.persistent_ui import reset_atx_agent; reset_atx_agent(ctx.adb, timeout=15)`.
- Sleep 1.0s để bind socket JSON-RPC.
- Thử recapture 1 lần với step `sponsored_check_retry`.

### Tầng 2: Fail-soft tuyệt đối cho Heuristic Check
- Nếu sau khi retry vẫn ném exception (hoặc TikTok không ở foreground, hoặc reset fail):
- Log `sponsored_check_degraded` với `result="degraded"`.
- Bắt buộc trả về `False` (coi như không phát hiện sponsored) để vòng lặp feed tiếp tục phát và vuốt video bình thường, KHÔNG ĐƯỢC để exception văng ra ngoài làm crash flow.

### Tầng 3: Unit Test mô phỏng các kịch bản & Pitfalls (`test_sponsored_check_atx_recovery.py`)
- **Tệp test**: `python_runner/tests/test_sponsored_check_atx_recovery.py`.
- **Kịch bản 1**: ATX lỗi lần đầu -> reset_atx_agent -> retry capture thành công -> trả kết quả `_is_sponsored_xml`.
- **Kịch bản 2**: ATX lỗi cả 2 lần -> catch exception -> log degraded -> fail-soft trả về `False`.
- **Kịch bản 3**: TikTok mất focus -> fail-soft trả về `False` không gọi `reset_atx_agent`.

#### ⚠️ Unit Test Mocking Pitfalls (Bắt buộc nhớ):
1. **Bẫy Mock Guard `artifacts.__class__.__module__ == "unittest.mock"`**:
   - `_sponsored_present` có guard: `if artifacts is None or artifacts.__class__.__module__ == "unittest.mock": return False`.
   - Nếu dùng `ctx.artifacts = Mock()` thông thường như các test khác, hàm sẽ return `False` ngay ở dòng đầu và không bao giờ gọi tới `_capture_xml_text`.
   - Bắt buộc tạo một dummy class không thuộc `unittest.mock`:
     ```python
     class RealDummyArtifacts:
         def step_dir(self, step_name: str) -> str:
             return f"/mock_artifacts/{step_name}"
     ctx.artifacts = RealDummyArtifacts()
     ```
2. **Signature Khởi Tạo `UIDumpError`**:
   - `UIDumpError(code: str, message: str, ...)` có tham số đầu tiên là `code`.
   - Khởi tạo dạng: `UIDumpError("ATX_SESSION_UNAVAILABLE", "message")`. Cấm truyền cả vị trí lẫn keyword `code="ATX_SESSION_UNAVAILABLE"` vì sẽ gây `TypeError: got multiple values for argument 'code'`.
3. **Lệnh chạy verification**:
   ```bash
   cd "D:/Taadaa/tiktok-luot nuoi acc" && PYTHONPATH="D:/Taadaa/automation-core/src;D:/Taadaa/tiktok-luot nuoi acc/python_runner" python -m unittest -v python_runner/tests/test_sponsored_check_atx_recovery.py
   ```
