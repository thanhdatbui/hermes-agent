# Case 71 (02/09/2026): Loại trừ Body Username khỏi Switcher Anchor Fallback & Chuẩn hóa So khớp Header `:id/pke` trên Layout TikTok 46.x (Sự cố Máy 60)

## 1. Hiện tượng & Triệu chứng (Máy 60)
- **Script:** `multi-machine-feed-session` chạy preflight tài khoản chuyển sang `evav155`.
- **Lỗi dừng phiên:** `manual-needed:account-switcher-not-open: profile switch anchor could not be resolved safely`.
- **Hiện trường (Ảnh & XML):**
  - Màn hình Profile của tài khoản `crystal.1.1` thuộc layout TikTok 46.x (khi chưa cuộn, username `@crystal.1.15` nằm ở thân profile bên trái tại `y=370..415`, top bar chưa có sticky header).
  - Script tap vào body username `@crystal.1.15` (`id/sr3`, center `[154, 392]`), nhưng trên TikTok, nút body username chỉ là nút copy handle, không mở bottom sheet *Chuyển đổi tài khoản*.
  - Script lặp lại 2 lần thử không mở được switcher và fail-closed dừng phiên.

## 2. Phân tích Nguyên nhân Gốc (Root Cause)
1. **Lỗi Fallback Tap Body Username:**
   - Trong `_resolve_profile_switch_anchor`: Khi màn hình Profile root ban đầu chưa cuộn, hàm `_find_sticky_profile_header` trả về `None` do chưa xuất hiện sticky top bar.
   - Hàm sau đó rơi xuống `_profile_switch_fallback_anchor(identity)` trả về `username_element` (`id/sr3` `@crystal.1.15` tại `y=392`). Tapping vào body username chỉ copy handle vào clipboard chứ không mở switcher.
2. **Lỗi Ghép Chuỗi Badge/Số Đuôi của UIAutomator:**
   - Trên layout chưa cuộn, UIAutomator dump text của `su7` (display name) bị nối thêm index/badge thành `crystal.1.11` và `sr3` thành `@crystal.1.15`.
   - Khi script cuộn Profile (`_profile_scroll`), node header `:id/pke` xuất hiện trên cùng với text sạch `crystal.1.1`.
   - Khi so sánh `node_value` (`crystal.1.1`) với `identity_values` (`{'crystal.1.11', 'crystal.1.15'}`), phép kiểm tra `node_value in identity_values` trả về `False`, khiến `_find_sticky_profile_header` loại bỏ nhầm node header thật.

## 3. Giải pháp Chuẩn hóa (Code Fix)
1. **Loại trừ Body Username khỏi Fallback:**
   - Trong `_profile_switch_fallback_anchor(identity)`: Tuyệt đối không trả về `username_element` khi nó nằm ở vùng thân Profile (`center[1] > 260` hoặc `bounds[0] < 300`). Chỉ chấp nhận khi username thực sự là sticky header (`center[1] <= 250` và `300 <= center[0] <= 780`).
2. **Hỗ trợ Fuzzy / Prefix Matching cho Header Node:**
   - Trong `_find_sticky_profile_header`: Cho phép so khớp `node_value` và `identity_values` theo prefix/fuzzy (ví dụ: `val.startswith(node_value)` hoặc `node_value.startswith(val)` sau khi strip số đuôi/badge).
   - Khi `node` là resource `:id/pke` / `:id/pkh` ở top center (`y <= 250`), chấp nhận là Switcher Anchor hợp lệ.
3. **Tự động Cuộn Re-derive Identity trong `_resolve_profile_switch_anchor`:**
   - Nếu XML ban đầu chưa có sticky header, kích hoạt `_profile_scroll(ctx)` (từ y=1200 lên y=700, 400ms, settle 1.0s), dump lại XML, gọi `_profile_identity_from_xml(scrolled_xml)` để lấy identity sạch và phân giải header anchor `:id/pke`.
4. **Deduplication `matches_switcher_identity` & Chặn Đệ quy Auto-Login Recovery:**
   - Đưa hàm so khớp danh tính `matches_switcher_identity` vào `automation_core.tiktok.account_switcher` làm module chuẩn, consumer `feed_swipe_smoke.py` import trực tiếp.
   - Khi kích hoạt auto-login recovery trong `verify_and_switch_profile`, truyền cờ `allow_auto_reconcile=False` vào lượt gọi đệ quy tiếp theo để chặn nguy cơ lặp vô hạn / stack overflow nếu tài khoản vẫn không đăng nhập được.
