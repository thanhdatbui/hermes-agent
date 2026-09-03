# Case 71: TikTok 46.x Profile Switcher Anchor Resolution & Body Username Exclusion

- **Nguyên nhân dừng phiên**: Trên layout TikTok 46.x mới, username `@username` khi Profile chưa cuộn nằm ở thân bên trái (`id/sr3`, `y=370..415`). Hàm `_profile_switch_fallback_anchor` trả về node này làm switch anchor khiến script bấm nhầm vào nút copy handle thay vì mở sheet Switcher.
- **UIAutomator text concatenation**: `su7` (display name) và `sr3` (username) bị uiautomator nối số index badge (`crystal.1.1` $\rightarrow$ `crystal.1.11`, `@crystal.1.15`). Khi cuộn lên, header `:id/pke` xuất hiện với text sạch `crystal.1.1`. So khớp identity phải hỗ trợ prefix/fuzzy matching.
- **Quy chuẩn**:
  1. `_profile_switch_fallback_anchor` CẤM trả về node ở vùng body (`center[1] > 260` hoặc `bounds[0] < 300`).
  2. Khi chưa có sticky header, kích hoạt `_profile_scroll` (từ y=1200 lên y=700 trong 400ms), re-dump XML và re-derive identity sạch từ XML sau cuộn.
