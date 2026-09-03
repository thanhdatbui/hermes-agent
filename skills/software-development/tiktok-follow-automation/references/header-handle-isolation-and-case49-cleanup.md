# Header Handle Isolation vs Suggested Accounts & Case 49 Cleanup Failure Contract

## 1. Header Handle Isolation vs Suggested Accounts (TikTok 46.x)

### Bối cảnh & Hiện tượng
Khi profile của anchor (hoặc user mục tiêu) có phần **Tài khoản được đề xuất (Suggested Accounts)** hiển thị ở nửa dưới màn hình:
- XML dump xuất hiện nhiều node có text dạng `@<suggested_handle>` cùng các nút `Follow`/`Follow lại`.
- Gate cũ đếm tổng số node bắt đầu bằng `@` trên toàn màn hình (`len(at_nodes) == 1`). Khi có Suggested Accounts, `len(at_nodes) > 1` dẫn đến báo lỗi sai: `hồ sơ thiếu handle (@uid) — từ chối tap Following` (hoặc `MANUAL_REVIEW`).
- Đồng thời, nếu ép so sánh cứng `identity_bounds == matching_header_node.bounds`, sự khác biệt về biểu diễn bounds giữa `automation_core` (`left, top, right, bottom`) và consumer parser (`x, y, w, h`) sẽ làm trượt điều kiện so khớp ngay cả khi đúng nick.

### Quy tắc xử lý chuẩn
1. **Header Y-boundary Scoping:**
   - Chỉ lọc các node `@-prefixed` nằm trong vùng header phía trên (`y < 650` hoặc `bounds[1] < 650`).
   - Bỏ qua toàn bộ các node `@...` thuộc danh sách Suggested Accounts (`y >= 650`).
2. **Exact Handle Match:**
   - Chuẩn hóa normalized handle: `_normalize_handle(node.text) == target_normalized`.
   - Yêu cầu chính xác 1 node header duy nhất khớp với UID mục tiêu.
3. **Tránh ép cứng Element Bounds khi không cần thiết:**
   - Không từ chối profile hợp lệ chỉ vì đối tượng `username_element` từ helper thiếu thuộc tính bounds hoặc sai khác format biểu diễn hình học khi text `@handle` trên header đã được kiểm chứng duy nhất và chính xác.

---

## 2. Empty Follower Surface Selector Drift (`id/yx1`)

Trên TikTok 46.x, màn hình danh sách trống (Empty Follower/Following surface) có thể sử dụng resource ID title mới:
- `com.ss.android.ugc.trill:id/yx1` (cùng các biến thể normalized `:id/yx1`, `id/yx1`).
- Bổ sung `id/yx1` vào `FOLLOWER_EMPTY_TITLE_IDS` song song với `id/yhj`, `id/yxo`, `id/yby`.
- Bắt buộc kiểm chứng cấu trúc: 1 ViewPager quan hệ (`FOLLOWER_RELATION_VIEWPAGER_ID`), 1 empty title Button, 1 empty message TextView, và tab quan hệ được chọn.

---

## 3. Case 49: Hợp đồng Cleanup & Xử lý Lỗi Fail-Closed

### Bảng trạng thái chuẩn

| Trạng thái ban đầu | Kết quả `close_all_recent_apps()` | Trạng thái cuối (`status`) | `failed` | `follow_failed` | Exit Code | Hành vi Alert |
|---|---|---|---|---|---|---|
| `OK` | Thành công (`True`/None) | `OK` | `False` | `False` | `0` | Không alert |
| `OK` | Exception hoặc trả về `False` | `CLEANUP_FAILED` | `True` | `False` | `1` | Alert hiện trường |
| `FOLLOW_FAILED` (clean) | Thành công (`True`/None) | `FOLLOW_FAILED` | `False` | `True` | `0` | Không alert (cooldown) |
| `FOLLOW_FAILED` (dirty) | Thành công (`True`/None) | `FOLLOW_FAILED` | `True` | `True` | `1` | Alert fail-closed |
| `FOLLOW_FAILED` | Exception hoặc trả về `False` | `CLEANUP_FAILED` | `True` | `True` | `1` | Alert fail-closed |

### Điểm mấu chốt
- Khi `close_all_recent_apps` ném ngoại lệ HOẶC trả về `False`, status BẮT BUỘC được promote thành `CLEANUP_FAILED` với `failed=True` và `exit_code=1`, đồng thời giữ nguyên cờ `follow_failed=True` để phục vụ tracing.
- Phía consumer feed session (`multi_machine_feed_session.py`): CHỈ bỏ qua alert Telegram khi thỏa mãn đồng thời: `status == 'FOLLOW_FAILED'`, `proc.returncode == 0`, `follow_failed is True` và `failed == 0/False`. MỌI lỗi kỹ thuật khác (`CLEANUP_FAILED`, `MANUAL_REVIEW`, `TIMEOUT`, crash, non-zero returncode) đều BẮT BUỘC gửi alert Telegram giữ hiện trường.
- Không nuốt lỗi cleanup để tránh biến lỗi kỹ thuật thành kết thúc êm.
