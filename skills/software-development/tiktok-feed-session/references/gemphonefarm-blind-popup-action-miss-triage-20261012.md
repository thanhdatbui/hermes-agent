# GemPhoneFarm Blind Popup Action-Miss Triage & Navigation-Confirm Popup Trap (2026-10-12)

## 1. Hiện Tượng & Triệu Chứng Thực Tế
Trong các phiên nuôi acc TikTok (Ca 1 Phiên 2/2 ngày 12/10/2026), nhiều máy ở cả 2 cụm Kibe (`M45`) và Admin (`M201`, `M232`, `M234`, `M247`, `M276`, `M278`) bị dừng phiên với trạng thái `manual-needed` do:
- `unexpected popup/dialog marker detected; swipe recovery (2 swipes) still stuck` (ở vòng lặp swipe, ví dụ `M45`)
- `unexpected popup/dialog marker detected` (ở bước chuyển tab navigation confirm, ví dụ `M201`, `M232`, `M247`)

## 2. Phân Tích Cơ Chế Lỗi Gốc Rễ (Root Cause)

### A. Lỗ hổng Action-Miss trong `_run_gemphonefarm_blind_popup_checkpoint`
1. **False-Positive Detector:**
   - Rule `learn_more_dialog_dismiss` có `detector_xpath = //node[@text="Tìm hiểu thêm" or ...]`.
   - Trên một số video quảng cáo (In-Feed Ad), xuất hiện pill/nhãn "Tìm hiểu thêm" ở góc dưới video (`[270,1665][576,1722]`), kích hoạt detector thành công.
2. **Action Target không tồn tại tại thời điểm probe:**
   - Do chỉ là nhãn trên video chứ chưa phải modal popup có nút đóng, `_gem_blind_action` quét `action_xpath` (`Đóng`, `tv_close`, `i2y`...) và trả về:
     `ok = False, reason = "GemPhoneFarm blind popup action not found: ..."`
3. **Lỗi logic tại caller `_maybe_run_gemphonefarm_blind_popup_checkpoint`:**
   - Code kiểm tra:
     ```python
     actions = _run_gemphonefarm_blind_popup_checkpoint(...)
     if not actions:
         return row
     ```
   - Khi action thất bại (`ok = False`), `actions` vẫn chứa `[{"rule": "learn_more_dialog_dismiss", "success": False, ...}]`. Do đó điều kiện `if not actions` bị bỏ qua!
   - Script tiếp tục gọi `after_row = _capture_step(..., step=after_step, ...)` để chụp lại màn hình.
   - Tại nhịp chụp này, modal dialog quảng cáo (`feature_promo_overlay` với nút `Tìm hiểu thêm` và `Đóng` `[120,1049][960,1164]`) hoặc popup mới (`Tạo Sự kiện` trên M45) xuất hiện hoàn chỉnh, khiến `classify_screen` cắm cờ `manual-needed:popup`.
   - Kết quả: `after_row` mang trạng thái lỗi `manual-needed` được trả về, đè bẹp `row` sạch trước đó dù thực tế không có thao tác tap nào được thực hiện thành công.

### B. Thứ tự kiểm tra lỗi trong luồng Chuyển Tab (Navigation Confirm)
- Tại `switch_{next_feed_type}_{swipe_count}_navigation_confirm`:
  1. `confirm = _maybe_dismiss_navigation_confirm_popup(...)` (chạy allowlist popup dismisser).
  2. `confirm = _maybe_run_gemphonefarm_blind_popup_checkpoint(...)` (chạy blind popup checkpoint).
- Do `_maybe_dismiss_navigation_confirm_popup` chạy **trước** blind popup checkpoint, màn hình recapture `after_step` từ blind checkpoint không bao giờ được đưa qua allowlist dismisser để đóng `feature_promo_overlay`.
- Ngay sau đó:
  ```python
  navigation_confirmed = confirm["status"] in {ExitStatus.SUCCESS.value, ExitStatus.DEGRADED.value}
  if not navigation_confirmed and not _is_navigation_mismatch_row(confirm, next_feed_type):
      results.append(confirm)
      return finalize_feed_session_cleanup(...)
  ```
  Runner thấy `confirm["status"] == "manual-needed"`, lập tức kết thúc toàn bộ phiên nuôi acc của máy thay vì gạt popup để chạy tiếp.

## 3. Bản Vá Đề Xuất (Patch Strategy)
1. **Kiểm tra thành công thực tế của actions:**
   ```python
   # Trong _maybe_run_gemphonefarm_blind_popup_checkpoint:
   if not any(action.get("success") for action in actions):
       return row
   ```
   Nếu không có thao tác nào tap thành công, tuyệt đối không recapture và không đè trạng thái `row`.
2. **Đưa màn hình sau blind checkpoint qua Allowlist Popup Dismiss:**
   Khi `after_row` có `detected == "manual-needed:popup"`, tiếp tục gọi `_maybe_dismiss_allowed_popup_after_swipe` để gạt các popup chuẩn như `feature_promo_overlay`.
3. **Thêm Handler cho Modal "Tạo Sự kiện" (`M45`):**
   Thêm detector/dismisser bấm nút Back/Close góc trên trái (`[48,114][120,186]`) khi xuất hiện `Tạo Sự kiện` / `Đăng ký`.
