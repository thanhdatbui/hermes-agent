# Case Study & Pitfalls: M261 Fake Password vs Canary Row Selection Trap (2026-10-26)

## 1. Context & Incident Summary
- **Alert Incident:** Phiên `row-0-060043` báo lỗi M261 "Lệch Profile/Nick TikTok".
- **Cluster:** Admin (Máy 261, Serial: `ce021602a92d1a0d04`, Remote ADB: `192.168.110.119:5037`).
- **Mục tiêu phiên:** Account Row 2 trong ca chạy (`thuthanh2911`, email `e6ahwg7.2911.tooct@hotmail.com`).
- **Hiện trường M261:** TikTok đang đăng nhập nick Row 1 (`lamhongloan1907`).

## 2. Failure Patterns & Operator Corrections

### Pitfall 1: False-Positive Canary (Test Nhầm Account Có Sẵn)
- **Sai lầm:** Khi chạy `canary_runner.py`, Coordinator truyền `--row 1`. Trên M261 đã đăng nhập sẵn nick Row 1 (`lamhongloan1907`), dẫn đến bước `profile_preflight` đánh giá `already matched` và lướt feed thành công mà **hoàn toàn không kích hoạt luồng login bù**.
- **Hậu quả:** Báo "Canary PASSED" đối phó, trong khi lỗi thật (thiếu nick Row 2 `thuthanh2911`) chưa hề được kiểm chứng hay xử lý.
- **Kỷ luật:** Khi Canary tái hiện lỗi thiếu nick / mismatch, **BẮT BUỘC** tra đúng `--row <N>` của tài khoản vắng mặt.

### Pitfall 2: Premature Canary Timeout
- **Sai lầm:** Đặt timeout 300s cho lệnh Canary trên máy remote Admin.
- **Hậu quả:** Chu trình login TikTok qua remote ADB kết hợp OTP Graph API mất từ 300–450s, lệnh bị ngắt non bởi `CANARY_TIMEOUT`.
- **Kỷ luật:** Mọi lệnh Canary / test login trên dàn remote Admin bắt buộc đặt `--timeout >= 720s`.

### Pitfall 3: Cột PASS Điền Bậy Chuỗi Mật Khẩu Ảo (Data Governance)
- **Sai lầm:** Nick `thuthanh2911` được đăng ký qua luồng Hotmail Outlook (email-only) chưa qua bước tạo mật khẩu thật trên TikTok. Kịch bản reg cũ khi xuất file Excel đã sinh chuỗi ngẫu nhiên `A6SpYQZm#W` rồi ghi vào cột PASS.
- **Hậu quả:** Runner tưởng nick đã có mật khẩu, điền vào form đăng nhập $\rightarrow$ TikTok báo đỏ `Mật khẩu sai` và dừng `AUTH_BLOCKED`.
- **Kỷ luật dữ liệu:**
  1. Chưa tạo pass trên TikTok thì cột PASS trong workbook **BẮT BUỘC ĐỂ `None` (RỖNG)**. CẤM tự ý sinh pass ảo ghi vào Excel.
  2. Khi gặp `Mật khẩu sai`: BẮT BUỘC tra cứu dữ liệu gốc trước. Nếu phát hiện là pass rác/chưa tạo pass, set cột PASS về `None`.
  3. Khi cột PASS là `None`, `tiktok_login_v1.py` nhận diện `has_pw = False`, không cố gõ mật khẩu mà chuyển thẳng sang lấy OTP qua Microsoft Graph API trên PC để đăng nhập an toàn.

### Pitfall 4: Stale Graph API OAuth Token Trap (`AADSTS70000`) & Recovery Email Domain API
- **Hiện tượng:** Sau khi xóa pass về `None`, TikTok chuyển sang màn hình gửi mã OTP về hòm thư `e6ahwg7.2911.tooct@hotmail.com`. Script gọi Graph API trên PC để lấy mã, nhưng Microsoft trả về lỗi:
  ```text
  AADSTS70000: The user could not be authenticated as the grant is expired. The user must sign in again.
  ```
- **Nguyên nhân:** Tài khoản Hotmail này được reg từ 12/09/2026. `refresh_token` trong `gmail_clean_v2.xlsx` đã quá hạn (>40 ngày không xoay vòng).
- **Bẫy kẹt điều phối & Thói quen "than thở/đùn việc" cần triệt tiêu**:
  * Khi mở GPM Profile để login lại bằng pass `datKHWa1N1bs`, Microsoft kích hoạt Security Challenge yêu cầu mã xác minh từ mail khôi phục (`e6ahwg7.2911.tooctdat@smvmail.com`).
  * Sai lầm nghiêm trọng của Agent: Dừng lại bảo "không có quyền truy cập smvmail.com nên không tự cứu được, cần user hỗ trợ".
  * **Sự thật kỹ thuật**: Mail khôi phục `smvmail.com` đã được mua sẵn kèm acc và có REST API công khai hoàn toàn:
    `GET https://api.smvmail.com/email?page=1&q=&email=e6ahwg7.2911.tooctdat%40smvmail.com`
    trả về JSON chứa toàn bộ email nhận được mà không cần đăng nhập hay password.
  * **Giải pháp phục hồi dứt điểm qua GPM Profile + smvmail API**:
    1. Mở GPM Profile (`a95dedbf-4170-495c-9249-4539c419a112`).
    2. Đăng nhập tại `https://login.live.com/` bằng pass `datKHWa1N1bs`.
    3. Nếu gặp prompt xác minh `smvmail.com`: Bấm gửi mã -> Gọi `https://api.smvmail.com/email?email=...` bóc mã OTP -> Điền vào form.
    4. Mở tab mới độc lập `page2 = context.new_page()` và điều hướng `https://outlook.live.com/mail/0/` để tránh lỗi đè điều hướng `Page.goto is interrupted by another navigation` từ trang `account.microsoft.com`.
    5. Đọc trực tiếp OTP TikTok từ web Outlook với bộ lọc `exclude_codes`.

### Pitfall 5: Do Dự & Hỏi Lặp Lại Khi User Đã Ra Lệnh Thực Thi ("Làm đi")
- **Sai lầm:** Khi đã chẩn đoán xong và user đã lệnh dứt khoát ("Làm đi", "Fix đi"), Agent lại dừng lại ở cuối turn để phân trần, tóm tắt lý thuyết hoặc hỏi xin phép lại ("Em làm nhé anh?").
- **Kỷ luật:** Khi đã có lệnh của user, Coordinator BẮT BUỘC thực thi dứt điểm bằng tool calls, sửa code, chạy lệnh kiểm chứng và chỉ báo cáo kết quả thực tế cuối cùng. CẤM dừng turn giữa chừng để hỏi lại điều user vừa phê duyệt.

