# Empty Friends Feed Suggestion Grid & Benign Stop Triage (Bẫy Gợi Ý Bạn Bè Khi 0 Clip)

## 1. Triệu Chứng (Symptoms)
- Watchdog báo cáo nuôi TikTok: `Trạng thái TikTok lạ/chưa hỗ trợ (1): M5`.
- Chi tiết trong `summary.txt` / `log.jsonl`:
  - `stop_reason: unknown TikTok state`
  - `reason: manual review required during feed-session-smoke`
  - Vị trí dừng: Sau khi chuyển sang tab Bạn bè (`switch_friends_<N>_navigation_confirm`) và thực hiện một số lượt swipe (ví dụ swipe 11).

## 2. Bản Chất Hiện Trường & Phân Tích Root Cause (UI XML & OCR)
- **Màn hình gợi ý kết bạn thay vì video:**
  Khi tài khoản chưa có bạn bè đăng video gần đây, tab "Bạn bè" (Friends) không render container phát video dọc, mà hiển thị `RecyclerView` danh sách gợi ý người dùng / follower:
  - Text OCR / XML đặc trưng: `"Follow bạn"`, nhãn tab `"Cộng đồng"`, `"Bạn bè"`.
  - Các nút hành động: `"Follow lại"` (`resource-id="...:id/u_f"`), `"Xóa"` (`resource-id="...:id/ubh"`).
- **Phân loại nhầm & Kích hoạt Safety Stop:**
  - Bộ kiểm tra popup mù phát hiện `follow_friends_suggestion_popup` (`manual-needed:popup`).
  - Sau swipe recovery, runner không tìm thấy container video nên chuyển sang `detected_screen: unknown` và dừng feed với `unknown TikTok state` để bảo vệ tài khoản.

## 3. Quy Trình Triage O(1) Cho Coordinator
1. **Kiểm tra tính liên tục của Pipeline trong `log.jsonl`:**
   - Dừng sớm ở pha lướt feed do cạn video bạn bè **KHÔNG** làm hủy bỏ toàn bộ chuỗi nhiệm vụ.
   - Coordinator bắt buộc kiểm tra các hook phía sau trong `log.jsonl`:
     + `follow-hook`: Đã chạy và ghi nhận `result: ok`, `status: OK` (ví dụ `followed: 3`).
     + `upload-hook`: Đã chạy và ghi nhận `result: ok`, `status: success` (video đã render và post thành công).
     + `cleanup_close_all`: Recent apps đã đóng sạch và trở về Android Home screen.
   - Nếu cả 2 hook kế tiếp đều thành công: Đánh giá đây là **Benign Early Stop (Dừng an toàn do cạn feed Bạn bè)**, không phải lỗi crash app hay blocker hệ thống.

2. **Quy tắc phân bổ Feed phòng ngừa (Preflight & Feed Distribution):**
   - Tương tự invariant Empty Following Feed: với các tài khoản mới hoặc tài khoản chưa có bạn bè đăng video, cấu hình phân bổ feed (`feed_distribution`) nên gán trọng số 100% cho FYP ("Dành cho bạn"), tránh chuyển sang tab "Bạn bè" để không kích hoạt lưới danh sách gợi ý này.
