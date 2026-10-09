# Cascading UI Selector Drift on TikTok App Updates (v46.x+)

## 1. Bản Chất Hiện Tượng (Cascading Drift)
Khi ứng dụng TikTok cập nhật phiên bản lớn (ví dụ `v46.9.3`), các mã định danh Resource-ID và cấu trúc UI không đổi đơn lẻ mà đổi theo chuỗi liên hoàn (cascading) từ màn hình ngoài vào các thành phần bên trong:

1. **Tầng 1 - Cửa vào & Khung danh sách (Container Level):**
   - Tiêu đề tab Follower/Following: Bổ sung các nhãn tiếng Việt mới như `"Đang follow [N]"`, `"Đang theo dõi [N]"` (cần regex bao quát).
   - Container danh sách: RecyclerView đổi từ `id/uvz`, `id/u5r` sang mã mới `id/uzs` (`com.ss.android.ugc.trill:id/uzs`).
2. **Tầng 2 - Phần tử tương tác bên trong (Item & Action Level):**
   - Nút quan hệ trong danh sách ("Follow", "Bạn bè", "Follow lại"): Đổi sang `com.ss.android.ugc.trill:id/u68` (trước đó là `id/u2f`, `id/tcj`, `id/tvn`, `id/tum`).
   - Nếu tầng 1 vừa fix xong, bot mở bung được danh sách thì ở ca chạy tiếp theo sẽ lập tức vấp phải lỗi tầng 2: `MANUAL_REVIEW: follower row không có nút follow semantic`.

---

## 2. Kỷ Luật Điều Phối Dành Cho Coordinator (Phòng Ngừa Lỗi Kép)
Để tránh tình trạng ca trước vừa sửa xong thì ca sau lại phát Farm Alert diện rộng do đụng tiếp selector tầng trong:

- **Rà soát toàn diện XML dump:** Khi lấy được live XML dump từ thiết bị canary/inspect sau khi fix tầng 1, Coordinator BẮT BUỘC phải soi luôn các node con bên trong RecyclerView:
  - Nút bấm hành động có thuộc danh sách `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS` hay không.
  - Tên hiển thị (display name) và handle có nằm đúng `FOLLOWER_USERNAME_RESOURCE_ID` / `FOLLOWER_DISPLAY_NAME_RESOURCE_ID` không.
- **Fail-Closed là bắt buộc:** Việc hệ thống dừng lại khi thiếu nút semantic là đúng thiết kế để chống tap bừa hỏng nick/dính cờ phạt. Nhưng Coordinator cần chủ động nạp selector tầng sâu ngay trong cùng phiên xử lý thay vì đợi Farm Alert ca sau mới vá tiếp.
