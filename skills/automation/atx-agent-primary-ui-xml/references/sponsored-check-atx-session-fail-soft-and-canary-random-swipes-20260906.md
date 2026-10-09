# ATX Session Unavailable Trong Sponsored Check & Fail-Soft Recovery Cho Auxiliary Checks (Case 132, 2026-09-06, Máy 36)

## 1. Hiện tượng & Bối cảnh
- **Máy:** 36 | Serial: `ce10160ac8f1962305` | Nick: `jasomntqsso`
- **Quy trình:** Nuôi Acc / Lướt Feed (`tiktok-luot nuoi acc`)
- **Triệu chứng:**
  ```text
  stop_reason: capture-invalid: ATX_SESSION_UNAVAILABLE artifact=.../account_1b316b3aa7/sponsored_check
  final_status: manual-needed
  total_swipes_completed: 0
  ```
- **Hiện trường thực tế:** TikTok vẫn đang hiển thị Home Feed (`com.ss.android.ugc.trill`), video đang phát bình thường, không crash.

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Thiếu Exception Wrapper & Recovery tại tác vụ phụ trợ (`sponsored_check`):**
   - Tại `python_runner/flows/feed_swipe_smoke.py`, vòng lặp swipe gọi `_sponsored_present(ctx)`.
   - `_sponsored_present` gọi trực tiếp `_capture_xml_text(ctx, "sponsored_check")`.
   - Khi ATX stub hoặc JSON-RPC transport bị ngắt/timeout trên Samsung S7/Android 7, `_capture_xml_text` ném `UIDumpError("ATX_SESSION_UNAVAILABLE")`.
   - Vì `_sponsored_present` không bọc `try/except`, exception văng thẳng lên `feed_session_smoke`, đánh sập toàn bộ phiên lướt feed (`total_swipes_completed: 0`).
2. **Vi phạm nguyên tắc sống còn vs phụ trợ:**
   - `sponsored_check` là heuristic check để skip video quảng cáo hoặc gắn tag, không phải gate an toàn sống còn (như profile identity check hay crash safety).
   - Khi XML dump lỗi tại bước này, không được phép fail-closed toàn phiên.
3. **Cố định số swipe Canary Test:**
   - Mặc dù template alert B4 truyền `-RecoveryTestSwipes 2`, người vận hành mong muốn canary chạy random 2–3 swipe. Script `run-feed-session.ps1` trước đó nhận số 2 cứng khiến canary luôn chỉ chạy 2 swipe.

## 3. Giải pháp Khắc phục (2 Tầng)
1. **Tự động phục hồi ATX và Fail-Soft trong `_sponsored_present`:**
   - Bọc `_capture_xml_text` trong khối `try/except UIDumpError as exc:`.
   - Kiểm tra: Nếu `is_atx_failure` và TikTok vẫn ở foreground (`cur_pkg in tiktok_pkgs`):
     - Log action `sponsored_check_atx_recovery`.
     - Kích hoạt `reset_atx_agent(ctx.adb, timeout=15)` (chuẩn không dùng monkey).
     - Sleep 1.0s và recapture với step `sponsored_check_retry`.
   - Nếu retry vẫn fail hoặc TikTok không foreground:
     - Log action `sponsored_check_degraded`.
     - Fail-soft trả về `False` để bỏ qua sponsored check cho video hiện tại và tiếp tục chuỗi lướt feed an toàn.
2. **Random ngẫu nhiên 2–3 Swipes cho Canary (`run-feed-session.ps1` & `run_tiktok.py`):**
   - Trong `scripts/run-feed-session.ps1`: Khi `$RecoveryTestSwipes -eq 2` (từ template lệnh B4), tự động chuyển đổi sang `$effectiveSwipes = Get-Random -Minimum 2 -Maximum 4` (sinh ngẫu nhiên 2 hoặc 3).
   - Trong `python_runner/run_tiktok.py`: Cập nhật validation `--recovery-test-swipes` từ `<= 3` lên `<= 4`.
   - Cập nhật test suite: `python_runner/tests/test_multi_machine_feed_session.py` và `test_sponsored_check_atx_recovery.py`.

## 4. Verification Evidence
- Unit test mới: `python_runner/tests/test_sponsored_check_atx_recovery.py` (3/3 test cases passed).
- Unit test cập nhật: `test_multi_machine_feed_session.py` (2/2 passed).
- Live Canary Test Máy 36: Hoàn thành 2/2 swipes (`final_status: success`), ảnh screencap xác nhận TikTok feed ổn định.
