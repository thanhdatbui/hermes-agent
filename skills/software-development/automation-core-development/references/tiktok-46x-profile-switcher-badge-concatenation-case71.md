# TikTok 46.x Profile Layout & UIAutomator Badge Digit Concatenation (Incident Case 71, Máy 60)

## 1. Hiện Tượng & Triệu Chứng
- Trên thiết bị Máy 60 (chạy TikTok bản 46.x, tài khoản `crystal.1.1`):
  - Runner bị kẹt ở màn hình Profile root hoặc bấm nhầm vào node `@crystal.1.15` (nút copy username ở phần body), dẫn đến không thể mở bảng Account Switcher hoặc báo lỗi:
    `manual-needed:account-switcher-not-open: profile switch anchor could not be resolved safely`

## 2. Nguyên Nhân Kỹ Thuật (Root Causes)

### A. Body Username Copy-Button Trap (`id/sr3`)
- Trên layout Profile TikTok 46.x chưa cuộn:
  - Display name nằm ở `id/su7` (`text='crystal.1.11'`).
  - Username nằm ở `id/sr3` (`text='@crystal.1.15'`, `bounds=[36,370][273,415]`, `center=(154, 392)`).
  - Vùng top bar chưa hiển thị sticky header.
- Trên TikTok, node username `id/sr3` ở phần thân trang (body) chỉ là nút copy username, bấm vào không mở Account Switcher.
- Hàm `_profile_switch_fallback_anchor` trước đây trả về `username_element` vô điều kiện khi có node username, khiến runner tap nhầm vào `sr3` ở body.

### B. UIAutomator Trailing Badge/Digit Concatenation
- UIAutomator trên một số bản Android/TikTok tự động nối các TextView con hoặc badge số unread/copy vào chuỗi text chính mà không có dấu cách:
  - Display name `crystal.1.1` + badge `1` -> `"crystal.1.11"`.
  - Username `@crystal.1.1` + icon/count `5` -> `"@crystal.1.15"`.
- Khi runner cuộn trang (`_profile_scroll`), header username sticky `id/pke` xuất hiện ở top center (`bounds=[370,117][730,183]`) với text chuẩn `"crystal.1.1"`.
- Tuy nhiên, các hàm so khớp identity (`_find_sticky_profile_header` và `find_switcher_anchor`) dùng phép so sánh tuyệt đối `node_value in identity_values` (`"crystal.1.1"` in `{"crystal.1.11", "crystal.1.15"}`) -> Trả về `False` -> Bỏ qua node `pke` hợp lệ.

## 3. Giải Pháp & Quy Chuẩn Xử Lý

### A. Strict Fallback Anchor Bounds Gate (`feed_swipe_smoke.py`)
- `_profile_switch_fallback_anchor` bắt buộc kiểm tra tọa độ:
  - CẤM trả về node username khi nằm trong vùng body (`center[1] > 260` hoặc `bounds[0] < 300`).
  - CHỈ chấp nhận khi node là sticky top header (`center[1] <= 250` và `300 <= center[0] <= 780` và `bounds[0] >= 300`).
- `_profile_identity_has_switch_anchor(identity)` đồng bộ trả về `_profile_switch_fallback_anchor(identity) is not None`.

### B. Prefix & Fuzzy Identity Matching (`automation-core` & `consumer`)
- Cung cấp hàm so khớp prefix/fuzzy:
  ```python
  def _matches_profile_identity_text(val1: str, val2: str) -> bool:
      v1 = _normalized_ui_text(val1).lstrip("@")
      v2 = _normalized_ui_text(val2).lstrip("@")
      if not v1 or not v2:
          return False
      if v1 == v2:
          return True
      if len(v1) >= 3 and len(v2) >= 3:
          if v1.startswith(v2) or v2.startswith(v1):
              return True
          if v1.rstrip("0123456789+ ") == v2.rstrip("0123456789+ "):
              return True
      return False
  ```
- Áp dụng trong:
  1. `automation_core.tiktok.account_switcher.find_switcher_anchor`: So khớp `preferred_candidates` và `identity_candidates`.
  2. `feed_swipe_smoke._find_sticky_profile_header`: So khớp `node_value` với `identity_values` và `expected_username`.

### C. Scroll, Re-capture & Re-derive Flow
- Trong `_resolve_profile_switch_anchor`:
  - Khi view ban đầu chưa có sticky header, thực hiện cuộn profile (`_profile_scroll`).
  - Chụp lại XML (`_capture_xml_text`).
  - Trích xuất lại identity từ XML mới: `scrolled_identity = _profile_identity_from_xml(scrolled_xml)`.
  - Phân giải sticky header: `_find_sticky_profile_header(scrolled_xml, scrolled_identity) or _find_sticky_profile_header(scrolled_xml, identity)`.
