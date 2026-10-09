# Chuẩn Đoán & Khắc Phục Video Kẹt Upload Dở Dang (60% - 70%) Trên TikTok Profile

## 1. Cơ chế Upload của TikTok Client
Tiến trình đăng video trên ứng dụng TikTok diễn ra qua 2 giai đoạn kỹ thuật chính:
1. **0% đến ~60% (Local Video Transcoding & Packaging)**:
   - TikTok nén video, ghép audio, render filter/sticker và tạo file tạm trong `/data/data/com.ss.android.ugc.trill/cache`.
   - Giai đoạn này thực thi offline hoàn toàn trên thiết bị (Samsung S7 SoC/GPU). Do đó hầu như luôn đạt đến mốc ~60%.
2. **~60% đến 100% (Chunked Streaming Upload qua TTNet)**:
   - Bắt đầu từ mốc 60%–70% (thường gặp nhất là **67%** hoặc **65%**), client mở socket TCP/HTTP đẩy các chunks dữ liệu lên CDN/Ingress Server của ByteDance.
   - Khi thanh tiến trình đứng yên ở mốc **67%**, điều đó khẳng định: **Render nội bộ đã xong, nhưng luồng stream dữ liệu mạng bị ngắt hoặc server từ chối nhận tiếp**.

## 2. Nguyên nhân cốt lõi gây kẹt 67%
- **Proxy Timeout / Drop Connection / IP Rotation**:
  - Máy farm kết nối qua HTTP Proxy cục bộ (ví dụ: `192.168.110.2:<PORT>`).
  - Khi tải video lên, luồng stream chiếm băng thông liên tục. Nếu proxy bị timeout, rớt kết nối hoặc xoay IP giữa chừng, server ngắt luồng tải nhưng client chưa kịp nhận mã lỗi đóng kết nối (FIN/RST), khiến UI giữ nguyên trạng thái đóng băng 67%.
- **Automation ngắt tiến trình quá sớm (Về HOME / Switch Account sớm)**:
  - Nếu kịch bản automation bấm phím HOME, force kill app, hoặc gọi switcher chuyển sang tài khoản khác trước khi video hoàn tất 100%, hệ điều hành Android sẽ đóng băng process hoặc hạ băng thông network nền của TikTok, làm video kẹt lại thành Ghost Upload Task.
- **Server Audio Copyright / Action Cooldown Rejection**:
  - Tại thời điểm client gửi metadata và chunk audio đầu tiên (~65%), hệ thống kiểm duyệt TikTok có thể lập tức reject do bản quyền nhạc hoặc tài khoản đang bị hạn chế đăng video (Action Limit).
- **Ghost Upload Task trong SQLite nội bộ**:
  - Task tải lên dở dang bị kẹt trong cache/database của TikTok. Ngay cả khi mạng phục hồi, app không tự động resume mà hiển thị ô video mờ kèm phần trăm dở dang trên lưới Profile.

## 3. Quy trình xử lý & Khôi phục
1. **Xử lý nhanh trên UI**:
   - Chạm vào ô video đang tải dở (67%) trên màn hình Profile -> Pop-up thông báo *"Tải lên không thành công"* xuất hiện -> Chọn **Xóa (Delete)** hoặc **Lưu vào Bản nháp (Drafts)** để giải phóng ô bị treo.
   - Nếu UI đơ, chạy lệnh buộc dừng:
     `adb -s <SERIAL> shell "am force-stop com.ss.android.ugc.trill"`
     rồi mở lại ứng dụng.
2. **Kỷ luật Automation**:
   - Mọi script upload video bắt buộc phải có bước poll đợi UI xác nhận: hoặc thanh tiến trình đạt 100%, hoặc video xuất hiện trong grid với lượt xem (▷ 0/view).
   - Tuyệt đối không cho phép thoát app hay switch nick khi chưa có tín hiệu hoàn tất upload.
