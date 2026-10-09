# Case UI-46: Header Identity Scoping, Suggested Account Action Filtering & Clickable Ancestor Resolution

## Triệu chứng & Bối cảnh Sự cố (Máy 45 thoanvrr5n8 -> Target @thanhphuc45826)
- **Thiết bị:** Máy 45 (Serial: `ce0716071586c80602`, Row 2, nick `thoanvrr5n8`).
- **Hiện tượng:** Follow runner chạy timeout 1200s (`follow-timeout`), màn hình dừng tại profile target `@thanhphuc45826` với nút đỏ "Follow", nút "Nhắn tin", thống kê 0 Đã follow, 11 Follower, 1 video (89 views).

## 3 Điểm Lỗi Cốt Lõi (Anti-Patterns) & Cách Khắc Phục

### 1. Global `@` Matching trong Mode 1 (`_classify_exact_profile_action`)
- **Anti-Pattern:** Dùng `len(at_nodes) != 1` trên toàn bộ cây XML dump. Khi target profile có thêm các node chứa `@` ở vùng dưới (`y >= 650`, ví dụ: caption video `@friend`, gợi ý bạn bè "Bạn có thể biết"), kiểm tra này đánh giá sai thành `identity_mismatch` khiến flow skip nhầm và lặp lại tìm kiếm liên tục.
- **Fix chuẩn:** Sử dụng `_find_header_handle_node` (giới hạn vùng header `top_y < 650` kèm kiểm tra package TikTok hợp lệ) và `_extract_identity_package`, tuân thủ nghiêm ngặt **Dual Structural Identity Gate**.

### 2. Ambiguous Follow Button Match khi có Thẻ Gợi Ý (`_tap_follow_button`)
- **Anti-Pattern:** `_tap_follow_button` tìm kiếm nút bấm trên toàn màn hình qua `_action_targets` mà không ưu tiên các nút header action thuộc whitelist (`y < 1200`). Khi profile có khối tài khoản gợi ý ("Bạn có thể biết") chứa các nút "Follow" riêng ở phía dưới, `len(matches) > 1` khiến hàm trả về `False` và không tap được nút Follow chính.
- **Fix chuẩn:**
  1. Ưu tiên tìm nút Follow đã được whitelist qua `_is_profile_action_node(node)` trong dải header `y < 1200`. Nếu có đúng 1 nút, tap ngay.
  2. Fallback sang `_action_targets` có điều kiện lọc `bounds[1] < 1200` để loại trừ các thẻ gợi ý bên dưới.

### 3. `NameError` & Hủy Danh Sách Tổ Tiên Ngầm trong `_node_or_clickable_ancestor` (`verify_follow.py`)
- **Anti-Pattern:**
  1. Thiếu `import xml.etree.ElementTree as ET` ở đầu file, dẫn đến `ET.fromstring` ném `NameError` bị nuốt ngầm bởi `except Exception: return []`.
  2. Câu lệnh `if target is None: return []` làm hủy toàn bộ danh sách khi có bất kỳ text node nào trong dump không gắn với clickable parent.
- **Fix chuẩn:**
  1. Bổ sung `import xml.etree.ElementTree as ET`.
  2. Đổi `if target is None: return []` thành `if target is None: continue` để bỏ qua node không có clickable parent và tiếp tục tìm các node hợp lệ còn lại.

### 4. Cooldown State Reset Kỹ Thuật Khi Chạy Live Canary
- Khi reset state để chạy live canary trên máy dính `FOLLOW_FAILED`, luôn gọi hàm `st.reset_follow_failed()` hoặc `pop` triệt để key `"cooldown_until_at"`. Nếu để `"cooldown_until_at": null` trong file JSON, `_check_and_sync_cooldown_expiry()` sẽ coi `None` là malformed timestamp và kích hoạt fail-closed (`return True`).
