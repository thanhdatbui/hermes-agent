# Kỷ Luật Nghiệm Thu & Khắc Phục Bại Liệt Não Auto-Resume

## 1. Bẫy Quên Đính Kèm Ảnh Nghiệm Thu Profile Sau Khi Hoàn Tất (Missing Proof Trap)
- **Hiện tượng:** Sau khi runner cập nhật Bio, ghim video hoặc đổi avatar xong, Coordinator chỉ thông báo suông bằng chữ "Đã xong" hoặc báo tiến trình nền kết thúc mà quên đính kèm thẻ `MEDIA:<path_anh_nghiem_thu>`, khiến User phải gắt: *"Hình sau khi làm xong trên nick đó đâu"*, *"Hình đâu???"*.
- **Kỷ luật thực thi:** Báo DONE bắt buộc phải có bằng chứng nghiệm thu thực tế. Sau khi hoàn tất runner trên thiết bị, BẮT BUỘC chụp màn hình Profile thật (`screencap`), kéo về máy (`pull`), chạy WinRT OCR lấy fresh receipt và gửi ảnh kèm thẻ `MEDIA:` ngay trong turn, tuyệt đối không để User phải đòi hỏi hình ảnh.

## 2. Bẫy Bại Liệt Não Sau Reconnect & Kỷ Luật Auto-Resume Tiếp Tục Làm Việc Dở Dang
- **Hiện tượng:** Khi phiên làm việc bị gián đoạn do PC reboot hoặc gateway restart, Coordinator khôi phục phiên nhưng mất toàn bộ đà làm việc. Thay vì kiểm tra hiện trường xem bước nào chưa xong để thi công tiếp, Coordinator lại phát tin nhắn hành chính chào hỏi rỗng tuếch: *"Phiên làm việc đã được khôi phục... Anh muốn làm gì tiếp theo?"* trong khi User đang chờ làm tiếp nick. User cực kỳ bức xúc và nổi giận: *"Hồi chiều t fix cái auto resume này 1 lần r sao h vẫn bị lại vào hỏi bại liệt não đkm đang làm dở thì làm tiếp hỏi cái lồn. Lí do hỏi mà đéo làm tiếp?"*.
- **Căn nguyên kỹ thuật & Bẫy trôi code:**
  1. Trong `D:/Taadaa/Hermes/gateway/run.py` (dòng ~19081), `_auto_continue_task` chỉ gán `True` khi `_reason == "restart_interrupted"`. Khi Gateway tự restart (watchdog, timeout), lý do là `"restart_timeout"` hoặc `"shutdown_timeout"`, làm `_auto_continue_task` rơi về `False`.
  2. Nhánh `else` tiêm System Note bắt LLM phải bỏ việc dở dang và hỏi User (*"Report to the user that the session was restored successfully and ask what they would like to do next..."*).
  3. Bẫy trôi code: Đã từng sửa chiều nay nhưng file `gateway/run.py` chưa commit vào git, sau đó bị subagent/tool git checkout đè ngược lại làm mất code fix.
- **Hành động bắt buộc:**
  1. Đã mở rộng `_auto_continue_task = (not message) and _reason in ("restart_interrupted", "restart_timeout", "shutdown_timeout")`.
  2. Bắt buộc commit git cứng (`7f04bc84f`) vào repo Hermes để chống trôi code khi subagent làm việc.
  3. Khi phiên vừa khôi phục, CẤM chào hỏi hỏi ngược lại User, bắt buộc inspect ngay hiện trường thiết bị và chạy tiếp runner đang dở.

## 3. Kỷ Luật Xử Lý Lỗi Provider Upstream / Transient Error
- Khi gặp lỗi upstream `The model provider failed after retries...`, đây là lỗi mạng/provider upstream tạm thời, KHÔNG phải lỗi hệ thống farm.
- Coordinator phải kiểm tra health `:20129`, giữ bình tĩnh và báo cáo trung thực, tuyệt đối không hoảng loạn hoặc viện cớ để bỏ dở nhiệm vụ.
