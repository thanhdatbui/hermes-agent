# Case UI-40: Stat Counter Resource-ID `id/svu` & `id/svt` Trong Nhận Diện Zero Following (TikTok 46.x)

## Hiện Tượng & Nguyên Nhân
- **Sự cố Máy 59** (`ngocanh.34589` anchor `longtuong10`): Follow runner rơi vào vòng lặp retry/recovery ladder rồi bị follow-timeout khi gặp anchor có 0 Following (0 Đã follow).
- **Nguyên nhân cốt lõi**:
  - Trên phiên bản TikTok 46.x (ví dụ Máy 59), layout trang cá nhân chia tách số đếm và nhãn thành 2 nodes riêng biệt trong cùng một cột dọc:
    - Node số đếm: `text="0"`, `resource-id="com.ss.android.ugc.trill:id/svu"`, `bounds="[88,651][388,717]"`.
    - Node nhãn: `text="Đã follow"`, `resource-id="com.ss.android.ugc.trill:id/svt"`, `bounds="[88,711][388,759]"`.
  - Bộ hằng số `_STAT_COUNTER_IDS` trong `verify_follow.py` trước đây chỉ chứa: `("id/sdn", "id/shq", "id/svt", "id/svs", "id/suu", "id/sut")` — thiếu `"id/svu"`.
  - Hàm `_is_zero_following_profile` trong `mode2_follow_followers.py` dùng `_STAT_COUNTER_IDS` để lọc các node counter hợp lệ. Do thiếu `id/svu`, node đếm `0` bị bỏ qua trong vòng lặp tìm căn gióng cột dọc (`abs(label_center_x - node_center_x) <= 45.0` và `abs(label_center_y - node_center_y) <= 120.0`), khiến hàm trả về `False`.

## Quy Tắc Khắc Phục (Standard Fix)
1. **Mở rộng Allowlist Stat Counter ID**:
   - `_STAT_COUNTER_IDS` trong `verify_follow.py` bắt buộc phải bao gồm đầy đủ:
     ```python
     _STAT_COUNTER_IDS = (
         "id/sdn", "id/shq", "id/svt", "id/svs", "id/suu", "id/sut", "id/svu",
     )
     ```
2. **Kế thừa và Đồng bộ trong Mode 2**:
   - `_is_zero_following_profile` trong `mode2_follow_followers.py` kế thừa trực tiếp từ `_STAT_COUNTER_IDS`.
   - `_following_tab_node` trong `mode2_follow_followers.py` bổ sung `"id/svu"` vào danh sách resource-id dòng tab ưu tiên (`tab_id_matches`).
3. **Fail-Closed & Không Bỏ Sót Anchor Rỗng**:
   - Khi phát hiện anchor có `0 Following` / `0 Đã follow`, runner gán `engine._last_anchor_follow_outcome = "zero_following"`, skip không tap nút hay follow anchor, và quay về Feed an toàn mà không kích hoạt recovery ladder hay retry lần 2.
