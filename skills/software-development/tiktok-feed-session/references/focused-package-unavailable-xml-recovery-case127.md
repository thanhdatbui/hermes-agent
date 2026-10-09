# Case 127: Tự Động Khôi Phục Focused Package Unavailable Khi Đang Mở TikTok Qua XML Markers

## 1. Triệu Chứng & Hiện Trường Sự Cố
- **Hiện tượng:** Máy farm (ví dụ Máy 46 `ce0916092531413504`) đang lướt feed TikTok thì bị dừng đột ngột với Farm Alert: `focused package unavailable`.
- **Hiện trường thực tế:** Ứng dụng TikTok vẫn đang mở trên màn hình và hiển thị feed bình thường.

## 2. Nguyên Nhân Cốt Lõi (Root Cause)
1. **Dumpsys Jitter Trong Lúc Android Chuyển Cảnh:**
   - Khi Android chuyển đổi view/video hoặc hệ thống bận, lệnh `dumpsys window` / `dumpsys activity` có thể trả về `focused_package = None` tạm thời (hoặc bị rỗng).
2. **Khiếm Khuyết Truyền Tham Số Tại `safety_check_attempt`:**
   - `safety_check_attempt` (`python_runner/core/safety.py`) gọi `safety_check(...)` nhưng:
     * Không truyền tham số `raw_xml` (mặc định là `None`).
     * Chỉ đọc `attempt.get("detected_screen")`, bỏ qua `attempt.get("detected")`.
   - Kết quả: Biến `is_tiktok_xml` trong `safety_check` luôn đánh giá là `False`.
3. **Cơ Chế Fail-Closed Quá Cứng Nhắc Khi `focus_pkg is None`:**
   - Trong `safety_check`:
     ```python
     if (focus_pkg in SYSTEM_OVERLAY_PACKAGES or focus_pkg is None) and xml_available and (is_known_tiktok_screen or is_tiktok_xml):
         focus_pkg = expected
     elif focus_pkg is None:
         return SafetyCheckResult(SAFETY_FAILED, "focused package unavailable", ...)
     ```
   - Do `is_tiktok_xml` luôn `False` và khi `detected` rỗng, nhánh recover bị bỏ qua và lập tức ném lỗi `SAFETY_FAILED: "focused package unavailable"`.

## 3. Giải Pháp Chuẩn (Case Fix)
1. **Fallback Đọc `raw_xml` & `detected` trong `safety_check_attempt`:**
   ```python
   detected = (
       attempt.get("detected_screen")
       or attempt.get("detected")
       or attempt.get("image_selected_top_tab")
       or attempt.get("image_selected_bottom_tab")
   )
   raw_xml = attempt.get("raw_xml") or attempt.get("xml_text")
   if not raw_xml and attempt.get("xml_path"):
       try:
           from pathlib import Path
           xml_p = Path(str(attempt["xml_path"]))
           if xml_p.is_file():
               raw_xml = xml_p.read_text(encoding="utf-8", errors="ignore")
       except Exception:
           raw_xml = None
   ```
2. **Mở Rộng Nhận Diện `is_tiktok_xml` & `is_known_tiktok_screen`:**
   - Kiểm tra toàn diện các biến thể package trong `KNOWN_TIKTOK_PACKAGES` (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`).
   - Kiểm tra các markers đặc trưng của feed TikTok: `"Đề xuất"`, `"Bạn bè"`, `"Following"`, `"For You"`, `"Hồ sơ"`, `"Profile"`, resource-id prefixes (`:id/root_view`, `:id/viewpager`).
   - Gộp điều kiện `has_xml_evidence = bool(xml_available or raw_xml)`.
3. **Phục Hồi Focus Khi Có Bằng Chứng XML Hợp Lệ:**
   - Khi `(focus_pkg in SYSTEM_OVERLAY_PACKAGES or focus_pkg is None) and (is_known_tiktok_screen or (has_xml_evidence and is_tiktok_xml))`:
     * Tự động phục hồi `focus_pkg = expected` kèm log warning.
     * Vẫn bảo đảm tính fail-closed: nếu `focus_pkg is None` mà KHÔNG có bất kỳ bằng chứng XML/screen TikTok nào thì vẫn trả về `SAFETY_FAILED: "focused package unavailable"`.
4. **Tối Ưu Parse Focus Tại `observe.py`:**
   - Bổ sung định dạng `Window{...}` của Samsung OneUI vào `FOCUS_RE`.
   - Thêm lệnh lightweight grep `dumpsys window | grep -E 'mCurrentFocus|mFocusedApp...'` làm fallback trước khi đọc recents.

## 4. Kiểm Thử Verification
- Unit test: `test_safety.py` bổ sung 4 test cases kiểm tra:
  * `test_focus_none_recovers_when_xml_has_tiktok_elements` -> PASS
  * `test_focus_none_recovers_when_screen_is_known_tiktok` -> PASS
  * `test_focus_none_recovers_avoiding_package_unavailable_on_xml` -> PASS
  * `test_focus_none_without_tiktok_evidence_fails_unavailable` (fail-closed check) -> PASS
- Canary thực tế: Chạy `run-feed-session.ps1` trên máy thật với `-RecoveryTestSwipes 2` -> Hoàn thành 2/2 swipes, `final_status: success`.
