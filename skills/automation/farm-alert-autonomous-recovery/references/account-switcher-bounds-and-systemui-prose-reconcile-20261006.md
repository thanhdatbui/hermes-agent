# Account Switcher Bounds & SystemUI Prose Reconcile (2026-10-06)

## Hiện tượng thực tế trên Machine 7 (SM-G930F / TikTok v47.x)
Trong ca chạy feed session trên M7 (`run-feed-session.ps1 -Machines 7 -Row 5`), hai lỗi liên tiếp khiến luồng account switcher bị kẹt và báo sai trạng thái:

1. **Bẫy Tọa Độ Tap Switcher Hàng Toàn Màn Hình (`x=540` vs `x=300`):**
   - Trên Samsung Galaxy S7 (OneUI), mỗi hàng tài khoản trong bottom sheet `Chuyển đổi tài khoản` là một widget `android.widget.Button` kéo dài toàn bộ chiều rộng màn hình `[0, 1140][1080, 1356]`.
   - Avatar và tên tài khoản (ví dụ `@huehoafi23`) chỉ nằm ở nửa bên trái (`x=36..520`). Nửa bên phải (`x=540..1080`) là khoảng trống (whitespace).
   - Khi runner tính tọa độ click bằng `bounds.center`, điểm chạm rơi vào `x=540`. Samsung/OneUI nuốt sự kiện chạm tại vùng trống này mà không kích hoạt chuyển tài khoản.
   - Hệ quả: Log báo `action: tap_expected_account, result: success`, nhưng sau khi đóng switcher, tài khoản trên profile vẫn giữ nguyên nick cũ, dẫn đến lỗi `profile username still mismatched after switch`.
   - **Khắc phục:** Kẹp giới hạn chiều ngang của bounds hàng tài khoản về tối đa 600px (`bounds[0] + 600`), đưa tọa độ tâm tap về `x=300`, đảm bảo chạm trực tiếp vào text và avatar của tài khoản.

2. **Bẫy Loại Bỏ Nhầm Switcher 8 Nick Do Va Chạm Text SystemUI:**
   - Khi thiết bị nạp đủ 8 nick, nút "Thêm tài khoản" bị đẩy xuống dưới đáy màn hình và không xuất hiện trong XML ban đầu.
   - Đồng thời, cây Accessibility XML của Android chứa các thông báo từ SystemUI và Google Play (ví dụ: *"Thông báo của dịch vụ Google Play: yêu cầu đăng nhập"*, *"Đang sạc pin, 67%"*, *"4G tín hiệu điện thoại"*).
   - Logic cũ kiểm tra `has_profile_prose = any(" " in value and value not in _ACCOUNT_SWITCHER_TITLES for value in values)`. Vì các chuỗi SystemUI có khoảng trắng, `has_profile_prose` thành `True` và làm hàm `_is_profile_account_switcher_xml` trả về `False`, khiến runner nhầm tưởng switcher chưa bung và báo `manual-needed:account-switcher`.
   - **Khắc phục:** Nếu XML đã có tiêu đề chuẩn `_ACCOUNT_SWITCHER_TITLES` (`Chuyển đổi tài khoản`) và có ít nhất 1 hàng tài khoản hợp lệ (`account_rows`), công nhận ngay là switcher hợp lệ mà không đòi hỏi nút "Thêm tài khoản" và không bị vô hiệu bởi text SystemUI.

3. **Kỷ Luật Chống Đóng Băng / Chống Than Vãn BLOCKED (User Mandate 2026-10-06):**
   - Khi worker subagent cạn budget hoặc hoàn thành một phần, Coordinator tuyệt đối KHÔNG được ngồi im báo BLOCKED để bắt User debug.
   - Nếu nguyên nhân gốc rễ và diff đã rõ ràng trong phạm vi O(1) (<= 30 dòng, 1 focused test), Coordinator kích hoạt L2 Emergency Surgery để tự sửa dứt điểm và chạy tiếp Canary ngay lập tức.
