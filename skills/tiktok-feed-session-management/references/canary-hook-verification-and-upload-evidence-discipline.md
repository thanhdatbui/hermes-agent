# Canary Hook Verification & Upload Evidence Discipline

## 1. Bài học xương máu: Tránh bẫy "Canary chạy mù" và "Bằng chứng lệch pha"
Trong các phiên sửa code tích hợp hook (ví dụ: `upload-hook`, `follow-hook`, `login-recovery` lồng trong ca nuôi feed `multi_machine_feed_session.py`):

1. **Bẫy Canary mù (Hook bị bypass im lặng):**
   - Chạy lệnh canary mặc định (`canary_runner.py`) chỉ chạy lướt feed 2 swipe cơ bản (`recovery-test-swipes 2`).
   - Nếu không truyền đúng cờ hook (ví dụ `--allow-upload-hook`) hoặc không có cơ chế auto-detect từ Git diff, luồng hook vừa sửa HOÀN TOÀN KHÔNG ĐƯỢC CHẠM TỚI.
   - Thêm vào đó, nếu sổ cái ca chạy (`shift_upload_history.json`) ghi nhận tài khoản đã đăng video trong ngày, hàm hook sẽ tự động `SKIP` (`already_uploaded_in_shift`), hoàn toàn không kích hoạt subprocess upload thực tế.
   - **Kỷ luật cơ giới hóa:** Bắt buộc cập nhật `canary_matrix.json` và `canary_runner.py` để tự động soi Git diff (`canary_plan.py`), nếu thấy sửa file luồng hook thì tự động gán cờ hook tương ứng (`any("upload" in r.get("hook") for r in reqs)`). Tuyệt đối cấm dựa vào `memory` để dặn LLM nhớ cờ.

2. **Bẫy Bằng chứng hình ảnh lệch pha (False Visual Receipt):**
   - Runner sau khi chạy xong ca feed thường quay về màn hình chính Home / For You.
   - `canary_runner.py` chụp ảnh màn hình kết thúc ca chạy -> Bốc trúng video đang phát trên For You (ví dụ: video nấu ăn của kênh người khác) thay vì chụp màn hình kết quả của hành động vừa thực hiện.
   - Việc lấy ảnh For You dán nhãn "bằng chứng đăng video" là sai bản chất và bị người dùng phản ứng gay gắt.
   - **Kỷ luật bằng chứng thực tế:** Bằng chứng đăng video (`post-published-surface.png` hoặc `profile-grid-verify_post-*.png`) bắt buộc phải lấy từ thư mục runtime của module upload (`D:/CodexRuntime/tiktok-video/runs/run_<serial>_<timestamp>/`), nơi có ảnh xuất bản thật mang username nick đăng, nút "Bóc tem" và lưới video trên profile đã tăng số lượng.
