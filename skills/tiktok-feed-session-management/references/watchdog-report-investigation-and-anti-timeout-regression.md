# Kỷ Luật Xử Lý Báo Cáo Ca Nuôi & Chống Bẫy Vòng Lặp Timeout ADB (Anti-Regression)

## 1. Phản Xạ Bắt Buộc Khi User Ném Báo Cáo / Alert Vào Chat

### Sai Lầm Cấm Kỵ (Paraphrasing / Đọc Lại Báo Cáo)
Khi User forward hoặc ném một báo cáo watchdog ca chạy (ví dụ `Cronjob Response: tiktok-feed-session-watchdog`) hoặc Farm Alert vào chat:
- **CẤM TUYỆT ĐỐI:** Ngồi chép lại, tóm tắt, diễn giải bằng lời các con số đã có sẵn trong bản tin (như *"Farm Kibe fail 50 máy, Admin 16 máy, nguyên nhân là..."*) rồi đưa ra lời khuyên lý thuyết suông (*"script không cần sửa, chờ ca sau"*).
- **Hành vi này bị coi là trốn việc và lải nhải**, trực tiếp gây bức xúc cho người vận hành.

### Quy Trình Điều Tra Hiện Trường O(1) Bắt Buộc
Báo cáo ném vào chat **LÀ MỆNH LỆNH ĐIỀU TRA KỸ THUẬT NGAY LẬP TỨC**:
1. **Truy vết Manifest O(1):** Mở trực tiếp file `run_manifest.json` và `log.jsonl` tại thư mục live của phiên vừa chạy (`D:/Taadaa/runtime/<cluster>/live/<YYYY-MM-DD>/row-<row>-<HHMMSS>/<run_id>/`).
2. **Đối soát Thực Tế qua ADB:** Chạy ngay `python D:/Taadaa/tools/inspect_machine.py <N>` trên các máy lỗi đại diện để lấy hiện trường phần cứng (Pin, Wi-Fi IP, Proxy, Màn hình, Current Focus).
3. **Bóc tách Bản chất Kỹ thuật:**
   - **Mất kết nối vật lý thật:** `inspect_machine` báo `device not found`, USB bus mất kết nối hoàn toàn.
   - **Rớt giả do Code Preflight:** Máy vẫn online trên ADB server, pin/màn hình bình thường nhưng script preflight đánh rớt (ví dụ: `adb.shell(check=False)` không retry khi stderr có connection-lost marker).
   - **Kẹt App / Popup / UI:** Màn hình dừng ở Splash, Edit Name subpage, hoặc LMK kill package.
4. **Hành Động Khắc Phục (Code-First):**
   - Thấy bug code logic/retry/localization: Chủ động sửa ngay (L1/L2) kèm focused test < 30s.
   - Thấy lỗi vật lý: Báo cáo danh sách cụ thể các máy cần cắm lại nguồn/cáp hub USB.

---

## 2. Chống Bẫy Vòng Lặp Timeout ADB (Anti-Regression: Case 162 vs Timeout)

### Hiện Tượng Bẫy Vòng Lặp
1. Thấy một số máy bị mất kết nối vật lý ngâm chạy tới khi cạn deadline (50 phút) và báo `Timeout`.
2. Agent vội vã hạ `connection_wait_timeout` của `AdbClient` xuống thấp (ví dụ 4.0s) hoặc giảm số lần retry vì nghĩ rằng làm vậy sẽ "fail-fast nhanh, không bị ngâm lâu".
3. **HẬU QUẢ TAI HẠI (REGRESSION):** Phá vỡ hoàn toàn cơ chế chống micro-drop USB Hub đã được đúc kết tại **Case 162**. Khi USB hub công nghiệp bị sụt tải tức thời (micro-drop 5–10s), thiết bị chưa kịp re-enumerate trên bus USB thì ADB client đã ném lỗi và khai tử máy sống $\rightarrow$ gây ra đợt sập batch hàng loạt ở phiên kế tiếp!

### Invariant Bất Biến Về ADB Connection Timeout
1. **Tuân thủ Tuyệt đối Case 162:** `connection_wait_timeout` mặc định là **20.0 giây** và `connection_retry_attempts = 3` (kèm backoff) là con số vàng để cứu các thiết bị micro-drop thoáng qua. **CẤM TUYỆT ĐỐI tự ý giảm timeout này trên các luồng batch feed session**.
2. **Bản chất của việc "ngâm 50 phút":**
   - Khi thiết bị bị mất điện / tuột cáp hoàn toàn (không còn trên bus USB), các lệnh ADB con liên tiếp ném `device not found`.
   - Các hàm recovery trong luồng nuôi acc nuốt exception để thử các phương án phục hồi khác nhau (thử Back, thử Monkey, thử chụp ảnh lại...). Chuỗi thử lặp qua nhiều bước nên tổng thời gian cộng dồn mới chạm trần deadline 50 phút.
   - Đây là cơ chế fail-closed an toàn của hệ thống khi phần cứng đứt hẳn. Giải pháp duy nhất là can thiệp vật lý (cắm lại nguồn/cáp), không được can thiệp hạ timeout phần mềm.
