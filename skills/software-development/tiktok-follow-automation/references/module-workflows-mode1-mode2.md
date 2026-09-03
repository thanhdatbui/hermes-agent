# Canonical Workflows: Module 1 (Search-Follow) & Module 2 (Anchor Following Cross-Follow)

## 1. Module 2: `mode2_follow_followers.py` (Follow chéo qua Following list của Anchor)
- **Mục đích:** Quét danh sách "Đang theo dõi" (Following) của các nick hạt giống nội bộ (Anchor - Tik1/Tik2), lọc đúng các nick thuộc Farm để thực hiện follow chéo.
- **Workflow:**
  1. **Khởi tạo & Budget:**
     - Đọc danh sách UID Anchor từ cấu hình / workbook Tik1 & Tik2 (`engine.anchor_uids()`).
     - Trộn ngẫu nhiên (shuffle) và chọn tối đa **3 anchor** cho phiên.
     - Gate Video: >=5 video mới kích hoạt follow, <5 video safe-skip budget = 0.
  2. **Tiếp cận Anchor:**
     - Đảm bảo Feed precondition (`_back_to_feed`).
     - `_nav_search(uid)`: Tìm kiếm icon Search trên Feed -> gõ UID -> chọn exact result -> mở Profile.
     - Kiểm tra Identity Gate (`profile_identity_from_xml` khớp 100% `@username`).
     - `_ensure_anchor_followed`: Nếu chưa follow -> tap Follow và pull-to-refresh reload. Nếu đã follow sẵn (hoặc nút Bạn bè / Nhắn tin / Đang theo dõi) -> ghi nhận `already_followed`, tiếp tục mở tab Following.
     - Bấm tab "Đã follow" / "Following" trên profile anchor -> xác nhận list populated.
  3. **Quét & Lọc nick nội bộ trong danh sách:**
     - Nạp danh sách UID farm (`internal_uids = engine.follow_uids()`).
     - Thu thập follower rows: Trích xuất handle Fail-Closed (`txt_user_name` / `txt_desc`).
     - Lọc: Nếu nick không thuộc farm -> skip (không lưu state). Nếu 20 nick ngoài farm liên tiếp -> đổi anchor.
     - Bấm Follow: Delay ngẫu nhiên giữa các lần follow -> bấm Follow đúng hàng theo bounding box Y.
  4. **Verification & Fail-Closed:**
     - Path A (Row-level): Reload dump XML xác nhận nút đổi sang đã follow.
     - Path B (Profile-level sampling): Mở profile nick kiểm tra định kỳ mỗi N lượt hoặc khi Path A không rõ ràng.
     - Nếu bị nhả follow (reload thấy nút quay về Follow) -> báo `FOLLOW_FAILED`, dừng toàn bộ phiên ngay lập tức, dọn dẹp đưa máy về Home an toàn.
  5. **Scroll:** Cuộn danh sách (tối đa 40 lần / 5 lần cuộn rỗng liên tiếp).

## 2. Module 1: `mode1_search_follow.py` (Search Follow trực tiếp từng UID)
- **Mục đích:** Tìm kiếm trực tiếp từng UID trong danh sách phân bổ (`taikhoan_run_safe.xlsx` / file task) và follow đích danh (hoặc dùng bù budget sau khi chạy Module 2).
- **Workflow:**
  1. **Khởi tạo:** Lấy danh sách UID mục tiêu (`engine.follow_uids()`), shuffle nếu `order: random`, trừ budget đã tiêu thụ nếu chạy chế độ `both`.
  2. **Target Precondition:** Bỏ qua UID đã `is_followed` / `is_skipped`. Kiểm tra đang ở Feed (`ensure_feed_for_follow`), lướt nhẹ 1-2 video tạo ngữ cảnh tự nhiên.
  3. **Search & Điều hướng (`_nav_search`):** Bấm Search -> focus EditText -> xóa text cũ -> gõ UID -> submit / chọn exact suggestion card -> vào Profile.
  4. **Identity & Phân loại:** Trích xuất `@username` chuẩn hóa (loại bỏ bidi/isolate unicode format).
     - `identity_mismatch` (nick sai/trùng): Ghi `failed_ids`, bỏ qua không lưu state (cho phép tìm lại sau).
     - `followed`: Đánh dấu `skipped`.
     - `not_followed`: Tìm đúng node nút Follow semantic.
  5. **Bấm Follow & Verify (`verify_after_tap`):** Bấm Follow -> đóng popup phát sinh -> kéo pull-to-refresh reload profile -> dump XML kiểm tra.
     - Nếu đã follow -> lưu state, trừ budget.
     - Nếu bị nhả follow -> kích hoạt `FOLLOW_FAILED`, dừng phiên khẩn cấp.
  6. **UI Recovery:** Nếu kẹt UI -> chạy thang phục hồi (ATX reset -> force-stop/launch -> soft reboot).
