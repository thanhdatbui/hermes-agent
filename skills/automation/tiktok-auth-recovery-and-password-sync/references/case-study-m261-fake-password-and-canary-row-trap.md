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

### Pitfall 4: Stale Graph API OAuth Token Trap (`AADSTS70000`)
- **Hiện tượng:** Sau khi xóa pass về `None`, TikTok chuyển sang màn hình gửi mã OTP về hòm thư `e6ahwg7.2911.tooct@hotmail.com`. Script gọi Graph API trên PC để lấy mã, nhưng Microsoft trả về lỗi:
  ```text
  AADSTS70000: The user could not be authenticated as the grant is expired. The user must sign in again.
  ```
- **Nguyên nhân:** Tài khoản Hotmail này được reg từ 12/09/2026. `refresh_token` trong `gmail_clean_v2.xlsx` đã quá hạn (>40 ngày không xoay vòng).
- **Bẫy kẹt điều phối:** Trong code `social_reg_v1.py` (dòng 7521), vì thấy mail CÓ token trong Excel nên hệ thống tuân thủ luật "cấm mở Outlook app trên điện thoại", từ chối fallback sang app di động. Kết quả: cả hai kênh đều không đọc được OTP, runner kẹt chờ hết 120s và chạm trần timeout ca chạy 720s.
- **Kế hoạch phục hồi:** Hoặc cấp lại `refresh_token` tươi trên PC qua GPM/browser, hoặc chủ động clear `refresh_token` thành `None` trong file Excel để script giải phóng fallback mở app Outlook với mật khẩu gốc.
