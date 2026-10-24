# Friends Tab Empty Feed Popup False-Positive & Regression Prevention Protocol

## 1. Bản Chất Sự Cố: Bẫy Kính Lúp Tìm Kiếm Trong `_find_follow_friends_semantic_close_control`
- **Hiện tượng lỗi (Sự cố Máy 5, Ca 2 Row 3)**:
  - Máy dừng phiên với lỗi `stop_reason: unknown TikTok state` tại lượt vuốt thứ 11 ở tab Bạn bè (*Friends*).
  - Màn hình hiện danh sách gợi ý tài khoản ("Follow bạn", "Follow lại", "Xóa") do tài khoản chưa có bạn bè đăng video.
- **Nguyên nhân cốt lõi (Root Cause)**:
  - Trong `python_runner/flows/benign_popup.py`, hàm `_find_follow_friends_semantic_close_control` có nhánh fallback tìm `ImageView` trong bán kính $600\text{px}$ quanh tiêu đề.
  - Trên tab Bạn bè, nhãn "Follow bạn" nằm ở $Y=241$. Hàm đã quét trúng **icon Kính lúp Tìm kiếm** (`ImageView` với `content-desc="Tìm kiếm"` tại bounds `[912,75][1080,243]`) và nhận diện nhầm Kính lúp là "nút đóng" của popup!
  - Việc tìm thấy nút đóng giả này đã đánh lừa Main Feed / Profile Guard của **Case 122** (`_is_main_feed_or_profile_screen`), khiến hệ thống kết luận có popup cần dismiss $\rightarrow$ bấm nhầm vào Kính lúp mở thanh tìm kiếm rồi kẹt luôn.

---

## 2. Quy Tắc Chống Regression Bắt Buộc (Soi Chiếu Case 122 & Case M43)

### CẤM SỬA CHỮA NGỌN (Bypass Classifier Gate):
- **CẤM TUYỆT ĐỐI** thêm điều kiện `if selected_feed_screen is None` trong `classify_tiktok_screen` (`classifier.py`) để ép bỏ qua popup khi tab Feed đang active.
- **Hậu quả tai hại nếu sửa ngọn:** Các modal popup và bottom sheet THẬT xuất hiện đè lên feed (ví dụ: Bottom sheet *"Đã follow chung (1)"* trong **Case M43**) sẽ bị nuốt chửng. Runner tưởng feed sạch nên không gọi bộ đóng popup mà cố vuốt feed $\rightarrow$ gây kẹt máy hàng loạt.

### QUY TRÌNH SỬA TẬN GỐC (Root-Cause Fix Contract):
1. **Vá chính xác tại `_find_follow_friends_semantic_close_control` (`benign_popup.py`)**:
   - Loại trừ tuyệt đối mọi phần tử có `text` hoặc `content-desc` là `"tìm kiếm"` hoặc `"search"`.
   - Siết chặt nhánh fallback $600\text{px}$: BẮT BUỘC có nhãn đóng tường minh (`text`/`desc` chứa *"Đóng"*, *"Close"*, *"✕"*, *"x"* hoặc resource-id chứa `c3t`, `e63`, `e8c`). Không cho phép `ImageView` vô danh lọt vào làm nút đóng.
2. **Bổ sung từ khóa nhận diện Tab Bạn bè rỗng (`feed_swipe_smoke.py`)**:
   - Mở rộng `_FRIENDS_FEED_CONTENT_TERMS` thêm: `"Follow bạn"`, `"Follow lại"`, `"Follow bạn bè của bạn"`.
   - Khi runner phát hiện tab Bạn bè không có video, tự động kích hoạt `fallback_to_for_you` để chuyển ngay về FYP lướt tiếp mà không làm gián đoạn phiên.
3. **Bộ kiểm chứng Focused Regression Tests**:
   - `test_mutual_follow_bottom_sheet_is_detected_and_close_button_identified` (Case M43) $\rightarrow$ Bắt buộc **PASS**.
   - Màn hình M5 thực tế: `detect_follow_friends_suggestion_popup(root)` $\rightarrow$ Bắt buộc trả về **`False`**, màn hình phân loại đúng `friends` với `manual_needed=False`.

---

## 3. Chốt Giảm Xóc Chống Khóc Lóc Cho Mechanical Regression Gate (Compulsion Gate)
Khi xây dựng Gate cơ học chặn sửa ngược hằng số (như Case 162 USB timeout $\ge 20s$, Case 161 Follow limit $\le 0$):
- **Nguy cơ:** Nếu chỉ ném `GuardEngine DENY` + `sys.exit(1)`, agent sẽ rơi vào phản xạ phòng thủ tâm lý, coi là bị bắt lỗi và quay sang viết sớ phân trần theo Rule 8 thay vì hành động tiếp.
- **3 Chốt giảm xóc bắt buộc:**
  1. **Message DENY chuẩn Enum đóng + Lệnh điền sẵn path O(1):** Chỉ in duy nhất `REQUIRED_NEXT_ACTION`: `REVERT_EXACT -> git checkout -- "<file>"` hoặc `JUSTIFIED_BYPASS -> sol_repair`. Cấm in text mô tả mơ hồ.
  2. **Auto-Quarantine O(1) qua `git stash`:** Gate tự động chạy `git stash push --keep-index -- "<file>"` đưa file về trạng thái sạch ngay lập tức.
  3. **3-Strike Mechanical Handoff:** Nếu vi phạm cùng 1 rule 3 lần trong phiên $\rightarrow$ Tự động mở ticket vào `sol_repair_queue.jsonl`, cấm agent phân trần, chỉ cho phép báo User: `"Đã mở ticket #ID cho Sol Repair"`.

---

## 4. Va Chạm Quota Claude CLI (85% Ceiling) & Kích Hoạt Tier 2 Agy Worker
- Khi Claude CLI chạm ngưỡng an toàn $85\%$ (5h quota), `claude_quota_guard.py` kích hoạt chặn cứng (`exit code 20`).
- **Khóa cơ học:** AI Coordinator bị cấm tuyệt đối tự chạy `claude_quota_guard.py allow` (`is_automated_agent_caller()` bắt lỗi).
- **Quy trình kích hoạt Worker Fallback:**
  - Chuyển sang **Tier 2 Worker: Antigravity CLI (`ag_cli.py fix`)** chạy model **`gemini-3.8-flash-medium`**.
  - Tận dụng pool 28 tài khoản Google One Pro cục bộ (0 token Anthropic, 100% quota OmniRoute).
