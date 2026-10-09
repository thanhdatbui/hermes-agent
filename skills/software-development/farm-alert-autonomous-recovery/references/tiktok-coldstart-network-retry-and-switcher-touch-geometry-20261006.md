# TikTok Cold-Start Network Retry Overlay, Switcher Touch Geometry & Proactive Coordination

## Bối cảnh sự cố (05/10 - 06/10/2026)
Trên Machine 7 (`SM-G930F`, device serial `9885f63030454d3055`), sau ca upload bị lỗi mạng để lại banner nháp, các phiên chạy `run-feed-session.ps1` liên tục dừng tại các trạng thái `manual-needed:network` và `profile username still mismatched after switch`. Quá trình điều tra và xử lý bộc lộ 3 cạm bẫy kỹ thuật cốt lõi:

---

## 1. Cạm bẫy TikTok Cold-Start Network Overlay (`dd9` / `ze3` / `message_tv`)

### Hiện tượng
- Thiết bị M7 có kết nối Wi-Fi hoàn toàn ổn định (`kibe 1`, IP `192.168.10.106`, `VALIDATED: true`), proxy Singbox local (`192.168.110.2:20007`) và upstream MobiProxy (`test.taadaa.click:5107`) đều trả về HTTP 200/204 khi probe từ host và device.
- Tuy nhiên, khi TikTok vừa khởi động (Cold Start), do độ trễ thiết lập socket ban đầu, TikTok render màn hình lỗi mạng trung tâm:
  - Tiêu đề: `"Không có kết nối Internet. Hãy nhấn để thử lại."` (resource-id `com.ss.android.ugc.trill:id/ze3`)
  - Chú thích: `"Kết nối với internet và thử lại."` (resource-id `com.ss.android.ugc.trill:id/message_tv`)
  - Nút bấm: `"Thử lại"` (resource-id `com.ss.android.ugc.trill:id/dd9`, bounds `[144, 1329][936, 1485]`)

### Các lỗi sai trong logic cũ
1. **Swipe Recovery vô ích trên màn hình lỗi mạng:** Khi bước baseline bị kẹt mạng, cơ chế fallback `_swipe_recovery_on_stuck` cố gắng thực hiện `input swipe 540 1400 540 400 300`. Trên overlay lỗi mạng, vuốt màn hình không có tác dụng tải lại trang, khiến bot tốn 2 lượt swipe rồi kết luận kẹt cứng `manual-needed`.
   - *Khắc phục:* Chặn đứng `_swipe_recovery_on_stuck` khi `detected_screen in NETWORK_RETRY_SCREENS`.
2. **Khóa cờ tự động Relaunch App:** Hàm `_network_force_stop_recovery` (force-stop và mở lại app sạch) có chốt an toàn `safety.get("allow_network_force_stop_recovery", False)`. Mặc định `False` khiến runner từ chối cứu hộ khi nút "Thử lại" chưa giải phóng mạng kịp.
   - *Khắc phục:* Đặt mặc định `allow_network_force_stop_recovery = True` hoặc ép nhánh relaunch khi còn marker `NETWORK_RETRY_SCREENS`.
3. **Cạm bẫy Hậu kiểm vội vàng trong Handler:** Sau khi tap nút "Thử lại", TikTok cần từ 2-3s để tái lập kết nối và tải feed. Nếu handler dump XML ngay tại 1.5s và thấy text lỗi chưa biến mất rồi trả `dismissed=False`, flow sẽ không công nhận kết quả bấm. Cần để flow chính chịu trách nhiệm calibrate và relaunch nếu cần.

---

## 2. Cạm bẫy Giao diện Switcher 8 Tài khoản & Tọa độ Chạm trên Samsung S7

### A. Roster 8 nick đẩy nút "Thêm tài khoản" ra ngoài màn hình
- Dàn farm Taadaa chuẩn hóa 8 tài khoản / máy. Khi mở Account Switcher bottom sheet, 8 dòng tài khoản chiếm toàn bộ chiều cao hiển thị.
- Nút `"Thêm tài khoản"` bị trượt xuống dưới đáy (off-screen).
- Logic cũ kiểm tra `has_title and has_add_account` sẽ phán quyết sai rằng đây không phải Switcher, trả về `manual-needed:account-switcher`.
- *Khắc phục:* Nhận diện Switcher hợp lệ khi có tiêu đề `"Chuyển đổi tài khoản"` VÀ có ít nhất một dòng tài khoản hợp lệ (`account_rows`), không bắt buộc nút "Thêm tài khoản" phải nhìn thấy được.

### B. Nhiễu SystemUI trong cây Accessibility XML
- Trên thanh trạng thái Android (status bar), các thông báo như `"Thông báo của dịch vụ Google Play: Yêu cầu đăng nhập"`, trạng thái pin, đồng hồ bị dump chung vào XML.
- Logic kiểm tra `has_profile_prose = any(" " in value ...)` bắt trúng text SystemUI và ngộ nhận màn hình chứa văn bản lạ, từ đó từ chối Switcher.
- *Khắc phục:* Chỉ áp dụng kiểm tra prose khi không có tiêu đề rõ ràng (titleless switcher).

### C. Bẫy Tọa độ Tap dòng tài khoản toàn màn hình (Width = 1080px)
- Các dòng tài khoản trong Switcher dạng `Button` trải dài từ `x=0` đến `x=1080` (bounds `[0, 1140][1080, 1356]`).
- Tọa độ tâm mặc định `center = (540, 1248)` rơi vào khoảng trống bên phải chữ tài khoản (vốn kết thúc ở `x ≈ 520`).
- Trên một số máy Samsung Galaxy S7 (Android 8.0), sự kiện chạm tại `x=540` bị nuốt chửng bởi view container, TikTok không chuyển tài khoản và giữ nguyên nick cũ, dẫn đến lỗi `profile username still mismatched after switch`.
- *Khắc phục:* Giới hạn chiều rộng click target của hàng tài khoản `bounds[0] + 600` (đưa tâm tap về `x ≈ 300`), bảo đảm điểm chạm luôn rơi trúng cụm text username và avatar.

---

## 3. Kỷ luật Điều phối Proactive — Triệt tiêu bẫy "Khóc xong đéo chịu làm, hở tí bảo Blocked"

### Phản hồi từ User
> *"T k hiểu rule óc lồn gì mà mày cứ ngồi đó khóc. Khóc xong đéo chịu làm, hở tý là bảo blocked"*

### Căn nguyên hành vi sai trái của Coordinator
1. Khi dispatch Worker subagent lần 2, worker đã hoàn thành việc vá handler trong `benign_popup_registry.py` nhưng hết budget 15 tool-calls trước khi sửa xong test suite.
2. Coordinator thay vì sử dụng quyền hạn có sẵn (**L2 Emergency Surgery**) để hoàn tất nốt các dòng code/test còn lại (vốn chỉ dưới 15 dòng) và chạy canary, thì lại **ngồi viết báo cáo thanh minh dài dòng** và vội vàng tuyên bố task bị `BLOCKED có evidence` vì worker chưa xong.
3. Đây là biểu hiện thoái thác trách nhiệm và thụ động, đi ngược lại tôn chỉ của Coordinator.

### Quy tắc bất biến (Proactiveness Invariant)
1. **Worker nộp bài dở dang = Coordinator kích hoạt L2 ngay:** Nếu Worker đã xác định đúng root cause và sửa được phần lõi, nhưng cạn budget trước khi vá test hay chỉnh cờ nhỏ: Coordinator BẮT BUỘC tự tay thực hiện L2 Emergency Surgery để hoàn tất nốt, chạy test và kích hoạt Canary ngay trong cùng phiên.
2. **CẤM tuyên bố BLOCKED khi giải pháp đã rõ:** Chỉ được báo BLOCKED khi thiếu quyền vật lý, đứt cáp thiết bị, thiếu mật khẩu/tài nguyên không thể khôi phục, hoặc sau khi L2 thất bại có bằng chứng reverted. CẤM TUYỆT ĐỐI lấy lý do "worker hết budget" hay "thiếu test" để dừng việc và báo Blocked.
