# TikTok Video Upload Buffering & Submission Verification Mechanics

## Hiện tượng Loading % trên Profile Grid (Samsung / Farm Android UI)
Khi quan sát giao diện máy farm qua mirror tool (Huanwei / VNC / Scrcpy) ngay sau khi đăng video:
1. **Loading Overlay (ProgressBar)**:
   - Ngay sau khi bấm nút **Đăng (Post)**, TikTok client tạo một `ProgressBar` / loading overlay dạng vòng tròn phần trăm (ví dụ: `96%`) đè tạm lên vị trí đầu tiên (`position 0` trong RecyclerView của tab Profile).
   - Đây là cơ chế hiển thị tiến độ upload/transcode nền của TikTok client **trước khi** danh sách feed/grid profile kịp refresh để đẩy video cũ sang bên phải và chèn video mới vào.
   - Nếu ô đầu tiên hiển thị số view cũ (ví dụ `173 views`) kèm vòng loading `%`, đó là tile cũ đang bị overlay loading của video mới đè lên tạm thời, không phải video cũ bị lỗi.

## Cơ chế Đợi & Bảo vệ Tiến trình trong Upload Workflow (`state_machine.py`)
Quy trình upload được thiết kế chặt chẽ, không bao giờ ngắt tiến trình đột ngột khi vừa tap nút Đăng:
1. **Submission Acceptance (`_wait_for_post_submission`)**:
   - Vòng lặp poll UI (tối đa 15s) chờ cho đến khi nút Đăng và composer biến mất khỏi màn hình.
   - Xác nhận trạng thái `post_submission_state = "ACCEPTED"`.
2. **Verification Gate (`_handle_verify_post` & `PostVerifier`)**:
   - Chờ video xuất hiện trên feed/own surface hoặc profile tile count tăng lên (`current > baseline`).
   - `PostVerifier` có timeout 120s bắt các sự kiện publish/mute/error.
3. **Background Process & Sandbox Isolation**:
   - Sau khi bấm Đăng, file media đã được nạp vào sandbox nội bộ của TikTok (`/data/data/com.ss.android.ugc.trill/...`).
   - Giai đoạn release (`_handle_release` và `_handle_post_cache_cleanup`) **tuyệt đối không force-stop app TikTok**, chỉ đóng Recent apps về Home.
   - Background Service của TikTok tiếp tục chạy nền để hoàn tất upload các chunk dữ liệu còn lại lên CDN qua proxy/VPN an toàn.
