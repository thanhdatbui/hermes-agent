# TikTok Feed Profile Verification Lag & Direct Download Fallback

## 1. Lag chuyển trang Profile gây False Identity Mismatch
- **Hiện tượng:** Sau khi kết thúc chuỗi lướt video (`feed-session-smoke`), script bấm vào nút *Hồ sơ* để đối soát lại tài khoản (`_verify_profile_after_session`), nhưng TikTok chuyển trang chậm -> dump XML lần đầu chưa kịp render node username `@...` (mới chỉ hiện một phần text như `"Thêm tiểu sử"`), khiến script đánh giá nhầm là `profile account mismatch` và kích hoạt báo động dừng phiên oan.
- **Quy tắc xử lý bắt buộc:** Không được kết luận `mismatch` ngay ở lần đọc XML đầu tiên. BẮT BUỘC `time.sleep(1.5)` và chụp lại XML lần 2 (`_capture_xml_text`) trước khi đánh giá cuối cùng.
- **Code áp dụng:** `python_runner/flows/feed_swipe_smoke.py` (`_verify_profile_after_session`).

## 2. TikTok Direct Download Fallback (TikWM API)
- **Hiện tượng:** Khi tải video gốc theo Niche (`download_by_niche.py`), yt-dlp cào danh sách video từ profile TikTok được nhưng khi tải từng file mp4 lẻ bị TikTok chặn bot (`Unexpected response from webpage request`).
- **Giải pháp:** Tích hợp fallback direct download qua TikWM API (`https://tikwm.com/api/?url=...`) để lấy stream MP4 trực tiếp và lưu vào đĩa khi yt-dlp trả về rỗng.

## 3. Quy trình Up Avatar Dọn Dẹp Thiết Bị
- **Quy tắc:** Sau khi cập nhật avatar thành công và chụp màn hình bằng chứng xác nhận (`screencap`), BẮT BUỘC thực hiện đóng ứng dụng TikTok (`am force-stop com.zhiliaoapp.musically; am force-stop com.ss.android.ugc.trill`) và gửi lệnh `keyevent 3` đưa máy về màn hình chính (Home) để giải phóng tài nguyên.
