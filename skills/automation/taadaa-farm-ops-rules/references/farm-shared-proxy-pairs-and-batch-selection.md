# Farm Shared Proxy Pairs & Anti-Overlap Batch Selection Rules

## 1. Cấu trúc Proxy Pairs trên Farm Taadaa (80 máy)
Từ kiểm tra `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` ngày 2026-08-18:
Toàn bộ farm được ánh xạ proxy theo các cặp dùng chung port (khoảng cách lệch 38 máy):
- Cặp `[1, 39]`: `test.taadaa.click:5101:mobi1:admin@1`
- Cặp `[2, 40]`: `test.taadaa.click:5102:mobi2:admin@1`
- Cặp `[3, 41]`: `test.taadaa.click:5103:mobi3:admin@1`
- Cặp `[4, 42]`: `test.taadaa.click:5104:mobi4:admin@1`
- Cặp `[5, 43]`: `test.taadaa.click:5105:mobi5:admin@1`
- Cặp `[6, 44]`: `test.taadaa.click:5106:mobi6:admin@1`
- Cặp `[7, 45]`: `test.taadaa.click:5107:mobi7:admin@1`
- Cặp `[8, 46]`: `test.taadaa.click:5108:mobi8:admin@1`
- Cặp `[9, 47]`: `test.taadaa.click:5111:mobi11:admin@1`
- Cặp `[10, 48]`: `test.taadaa.click:5112:mobi12:admin@1`
- Cặp `[11, 49]`: `test.taadaa.click:5113:mobi13:admin@1`
- Cặp `[12, 50]`: `test.taadaa.click:5114:mobi14:admin@1`
- Cặp `[13, 51]`: `test.taadaa.click:5115:mobi15:admin@1`
- Cặp `[14, 52]`: `test.taadaa.click:5116:mobi16:admin@1`
- Cặp `[15, 53]`: `test.taadaa.click:5117:mobi17:admin@1`
- Cặp `[16, 54]`: `test.taadaa.click:5118:mobi18:admin@1`
- Cặp `[17, 55]`: `test.taadaa.click:5121:mobi21:admin@1`
- Cặp `[18, 56]`: `test.taadaa.click:5122:mobi22:admin@1`
- Cặp `[19, 57]`: `test.taadaa.click:5123:mobi23:admin@1`
- Cặp `[20, 58]`: `test.taadaa.click:5124:mobi24:admin@1`
- Cặp `[21, 59]`: `test.taadaa.click:5125:mobi25:admin@1`
- Cặp `[22, 60]`: `test.taadaa.click:5126:mobi26:admin@1`
- Cặp `[23, 61]`: `test.taadaa.click:5127:mobi27:admin@1`
- Cặp `[24, 62]`: `test.taadaa.click:5128:mobi28:admin@1`
- Cặp `[25, 63]`: `test.taadaa.click:5131:mobi31:admin@1`
- Cặp `[26, 64]`: `test.taadaa.click:5132:mobi32:admin@1`
- Cặp `[27, 65]`: `test.taadaa.click:5133:mobi33:admin@1`
- Cặp `[28, 66]`: `test.taadaa.click:5134:mobi34:admin@1`
- Cặp `[29, 67]`: `test.taadaa.click:5135:mobi35:admin@1`
- Cặp `[30, 68]`: `test.taadaa.click:5136:mobi36:admin@1`
- Cặp `[31, 69]`: `test.taadaa.click:5137:mobi37:admin@1`
- Cặp `[32, 70]`: `test.taadaa.click:5138:mobi38:admin@1`
- Cặp `[33, 71]`: `mirotik1.taadaa.click:10001:admin@1:admin@1`
- Cặp `[34, 72]`: `mirotik1.taadaa.click:10002:admin@1:admin@1`
- Cặp `[35, 73]`: `mirotik1.taadaa.click:10003:admin@1:admin@1`
- Cặp `[36, 74]`: `mirotik1.taadaa.click:10004:admin@1:admin@1`
- Cặp `[37, 75]`: `khoalee.duckdns.org:16001:Gyx4k1:RzI0fc3o`
- Cặp `[38, 76]`: `khoalee.duckdns.org:16002:5ns08q:AmLmaMJ0`
- Các máy không gán proxy (Direct IP): Máy 77, 78, 79.

## 2. Nguyên nhân gốc rễ Google Die / TikTok Block khi chạy Batch
Khi chạy 1 batch gồm nhiều máy (ví dụ 30 máy):
- Nếu danh sách máy có cả 2 máy trong cùng 1 cặp (ví dụ vừa chọn Máy 4 vừa chọn Máy 42), hoặc Máy 4 chạy ngay sau Máy 42 mà IP proxy chưa đổi:
- Cả 2 máy sẽ thực hiện đăng ký Google / TikTok từ **CÙNG 1 ĐỊA CHỈ IP WAN**.
- Hệ thống bảo mật của Google và TikTok phát hiện 1 IP tạo nhiều tài khoản trong thời gian ngắn $\rightarrow$ lập tức kích hoạt cơ chế checkpoint "Xác minh danh tính của bạn" hoặc chặn mã OTP.

## 3. Quy tắc bắt buộc khi tạo Batch
1. **Tuyệt đối không chọn 2 máy cùng cặp proxy trong cùng 1 batch**.
2. Khi lọc máy cho batch N máy:
   - Gom nhóm máy theo proxy.
   - Mỗi nhóm proxy chỉ lấy tối đa 1 máy (ưu tiên máy có cooldown dài hơn).
3. **CẤM gọi lệnh xoay IP proxy** (user rule 2026-08-18: chỉ lọc duy nhất 1 máy / cặp proxy, không xoay proxy).
4. **Preflight `pm clear`**: Dùng `pm clear com.google.android.gm` trước khi reg để làm sạch hoàn toàn cache rác/session cũ của app Gmail.
5. **Dọn mail die**: Sau khi gỡ mail die, BẮT BUỘC close recent apps (`keyevent 187` -> tap Đóng tất cả -> `keyevent 3` về HOME) và gỡ device-lock ngay.
