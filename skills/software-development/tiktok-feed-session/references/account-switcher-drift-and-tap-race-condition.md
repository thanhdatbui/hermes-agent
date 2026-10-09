# Account Switcher Drift & Tap Race Condition Recovery (Case 128)

Tài liệu kỹ thuật chuyên sâu về xử lý lỗi `profile username still mismatched after switch` trong luồng nuôi acc / lướt feed TikTok (`tiktok-luot nuoi acc`).

---

## 1. Hiện tượng lỗi / Triệu chứng thực tế
- **Alert:** `[ALERT] [MÁY N] Dừng: manual-needed | Lý do: profile username still mismatched after switch`.
- **Hệ quả:** Hàng loạt máy bị dừng phiên ngay tại bước `profile_preflight`, không vào được vòng lướt feed.
- **Sự cố thực địa:** Máy 78, Máy 79 (TikTok phiên bản `46.2.3` trên Samsung Galaxy S7 Android 8.0).

---

## 2. Các nguyên nhân gốc rễ & Cơ chế gây lỗi

### A. Drift về Home/Feed nhưng XML sạch (`xml_error == ""`)
- **Cơ chế:** Khi TikTok thực hiện switch account hoặc tải lại phiên, app thường tự động điều hướng văng về Trang chủ (Home / For You feed).
- **Anti-Pattern trong `_profile_guard_drifted_from_profile`:**
  ```python
  # ❌ SAI LẦM: Chỉ coi là drift khi có degraded xml error hoặc keyboard cleanup
  if "keyboard cleanup" in reason:
      return True
  return xml_error in FEED_CONFIRMED_XML_DEGRADED_ERRORS
  ```
  Khi màn hình đang là For You video nhưng XML dump thành công hoàn chỉnh (`xml_error == ""`), hàm trả về `False` (tưởng nhầm app vẫn đang ở Profile).
- **Hậu quả:** Code trôi thẳng xuống `read_profile_identity()`, đọc màn hình Feed như Profile, bốc nhầm `@creator` của video For You (ví dụ `@Linhnguyen1707`) làm username của máy và so khớp với nick nuôi $\rightarrow$ báo mismatch hàng loạt máy.
- **Giải pháp chuẩn:** Bắt buộc kiểm tra `if detected in {"home", "for-you", "following", "friends"}: return True` để khẳng định màn hình đã trôi khỏi Profile, từ đó kích hoạt `_try_profile_retap_on_drift` re-tap tab Hồ sơ.

---

### B. Override Bounds sang Child TextView Không Clickable trong Account Switcher
- **Cấu trúc UI XML Switcher:**
  ```xml
  <android.widget.Button rid='...:id/l9b' cdesc='ruffumyxkvv' bounds='[0,816][1080,1032]' clickable='true'>
      <android.widget.TextView rid='...:id/mtx' text='ruffumyxkvv' bounds='[252,894][543,954]' clickable='false' />
  </android.widget.Button>
  ```
- **Anti-Pattern trong `_find_account_switch_option`:**
  Đoạn logic override container full-width (`>= 600px`) tìm inner `TextView` (`mtx`) và gán `best_bounds = inner.bounds` (tâm `x ≈ 397`).
  Trên một số bản TikTok (đặc biệt `46.2.3`), `TextView` có `clickable="false"` không nhận touch event, trong khi tap vào `x=540` lại rơi vào khoảng trống bên phải của username.
- **Giải pháp chuẩn:**
  Kiểm tra thuộc tính `clickable` của `node`:
  ```python
  is_node_clickable = node.attributes.get("clickable", "false").casefold() == "true"
  if not is_node_clickable and node.bounds is not None and (node.bounds[2] - node.bounds[0]) >= 600:
      # Chỉ override khi bản thân container không clickable
  ```

---

### C. Race Condition giữa Tap Switcher Row và `_navigate_profile_for_preflight`
- **Cơ chế:** Khi tap chọn tài khoản trong Account Switcher, TikTok cần 4–6s để reload state, xác thực session và chuyển đổi giao diện.
- **Anti-Pattern:** Ngay sau `tap_expected_account`, runner chỉ sleep ngắn rồi gọi ngay `_navigate_profile_for_preflight` vốn thực hiện `tap_navigation_target(_profile_target())` tại `[972, 1857]`.
  Lúc này Account Switcher sheet (`[0,420][1080,1920]`) vẫn đang hiển thị che phủ toàn bộ nửa dưới màn hình. Cú tap vào `[972, 1857]` chạm trúng vào đáy switcher sheet (vùng nút 'Thêm tài khoản' hoặc ngoài lề), khiến switcher sheet bị dismiss ngay lập tức trước khi TikTok ghi nhận sự kiện chuyển tài khoản.
- **Hậu quả:** Sheet đóng lại nhưng tài khoản active vẫn là nick cũ.
- **Giải pháp chuẩn:**
  1. Tăng thời gian chờ sau switch: `time.sleep(random.uniform(4.5, 6.0))`.
  2. Kiểm tra trạng thái màn hình hiện tại trước khi re-navigate: nếu đã ở Profile thì bỏ qua cú tap tab Profile đáy màn hình.

---

## 3. Quy trình Kiểm thử & Nghiệm thu Canary (B4)
1. Luôn kiểm tra đúng Row của nick trong `taikhoan_run_safe.xlsx` (tránh chạy nhầm Row 1 khi máy đang nuôi Row 6).
2. Lệnh Canary chuẩn:
   ```powershell
   powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row <R> -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
   ```
3. Nghiệm thu thành công khi:
   - Account switcher chọn đúng nick mong đợi.
   - Profile identity verify khớp `matched: true`.
   - Hoàn thành đủ số lượt recovery swipes với exit code 0.
