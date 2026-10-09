# Chiến Lược Nuôi Trust Tài Khoản Starter Bằng Natural Spillover Trong OmniRoute

Tài liệu quy chuẩn xử lý các tài khoản Google mới đăng ký (Starter/Free), cấp quyền OAuth Antigravity và bố trí định tuyến trên OmniRoute (port 20129) mà không gây gián đoạn cụm tài khoản Pro.

---

## 1. Bối Cảnh & Vấn Đề Thực Tế
- **Hiện tượng**: Khi nạp thêm các tài khoản Gmail mới (sau khi đăng nhập GPM và bật 2FA Authenticator) vào OmniRoute để lấy token Antigravity, nếu xếp ở tier thấp thì hầu như không có traffic nào chạm tới (do dàn tài khoản Pro ở đầu đã xử lý hết request).
- **Câu hỏi phát sinh từ người vận hành**: 
  - *"Có nên đưa acc mới lên đầu combo chính để chạy trước không?"*
  - *"Có nên tạo combo phụ/lặt vặt hoặc dùng cron định kỳ bơm request nhẹ để warm-up tăng trust acc không?"*

---

## 2. Bản Chất Bảo Mật Telemetry Của Google Cloud Code (Antigravity)
1. **Bản chất Token Antigravity**:
   - Token Antigravity là token sinh ra từ Google Cloud Code IDE extension dành cho lập trình viên.
   - Toàn bộ telemetry gửi về Google upstream phản ánh hành vi coding (đọc code, giải thích bug, sinh test, tóm tắt transcript làm việc).
2. **Cạm bẫy "Bơm Request Giả Lập" (Bot Signature Trap)**:
   - Nếu dùng cron định kỳ (ví dụ cứ mỗi 30 phút gửi 1 prompt vu vơ, chào hỏi, tóm tắt linh tinh):
     - **Lệch Intent**: Token IDE lập trình nhưng toàn gửi câu hỏi chat phổ thông.
     - **Tính chu kỳ máy móc (Temporal Periodicity)**: Request xuất hiện chính xác theo giây/phút cố định.
     $\rightarrow$ Hệ thống Abuse Detection của Google sẽ phát hiện chữ ký tự động hóa (bot pattern), dẫn đến tụt trust score, kích hoạt checkpoint `VALIDATION_REQUIRED` hoặc bắt xác minh lại thiết bị.
3. **Cấp quyền OAuth để ngâm (Idle) có bị phạt không?**:
   - **HOÀN TOÀN KHÔNG**. Hàng triệu lập trình viên cài extension, cấp quyền OAuth rồi để đó cả tháng mới bắt đầu dùng.
   - **0 request = 0 rủi ro**: Không gửi request nghĩa là không phát sinh telemetry, không có burst token, không dính 429. Tài khoản càng để lâu càng có độ "ngâm" (aged account) tự nhiên.

---

## 3. Quy Tắc Chống Over-Engineering Trong Cấu Hình Routing
1. **CẤM đưa tài khoản Starter/Free lên đầu combo chính (`ag-worker`, `ag-gemini-pool-3`)**:
   - Acc mới có hạn mức RPM/TPM thấp và context window nhạy cảm.
   - Khi Coordinator/Worker dispatch subagent chạy các prompt lớn (50K – 150K tokens), đưa acc mới lên đầu sẽ làm nổ 429 hoặc dính checkpoint ngay lập tức, làm tê liệt luồng điều phối của cả farm.
2. **CẤM tạo combo rác/lặt vặt (`ag-warmup`, `ag-light-worker`)**:
   - Tạo thêm combo con chỉ để phục vụ việc nén ngữ cảnh (1–2 lần/ngày) hoặc tác vụ nhỏ làm phân mảnh kiến trúc routing, Coordinator phải mất công rẽ nhánh chọn model, dễ sinh lỗi `ALL_TARGETS_SKIPPED`.

---

## 4. Giải Pháp Chuẩn: Natural Spillover Tier (Tràn Tải Tự Nhiên)
Quy trình chuẩn hóa 3 bước để tận dụng và nuôi trust tài khoản mới:
1. **Nạp OAuth & Gán Proxy 1:1 Cố Định (Quy tắc N:1 giữa Gmail và Máy S7/Port Proxy)**:
   - Một máy Samsung S7 và một cổng proxy 4G vật lý (ví dụ Port 5111, Port 5124, Port 5107...) có thể đăng ký và quản lý **nhiều tài khoản Gmail** qua các đợt reg khác nhau.
   - **BẮT BUỘC**: Gmail nào được reg từ máy S7 nào và cổng proxy nào thì khi mở GPM Profile cấp quyền OAuth, khi duyệt Google Prompt trên S7, và khi gán proxy trong OmniRoute (`PUT /api/settings/proxies/assignments`) phải gán chuẩn xác **đúng máy S7 và đúng cổng proxy vật lý đó**. Tuyệt đối cấm gán nhầm cổng của máy khác hoặc chạy direct IP.
   - Cấp quyền OAuth Antigravity trong GPM Profile qua Playwright.
   - Gán đúng Proxy 4G theo cổng máy farm (`5101..5140`) qua `PUT /api/settings/proxies/assignments` (`scope: account`).
   - Đồng bộ danh mục model qua `POST /api/providers/{id}/sync-models`.
2. **Xếp Toàn Bộ Vào ĐUÔI (Tail) Của Combo Chính (`ag-gemini-pool-3`)**:
   - Dàn tài khoản Pro (trả phí / trust cao) giữ nguyên ở các vị trí đầu (`pool-1` đến `pool-18`).
   - Các tài khoản mới được nối tiếp vào đuôi danh sách (`pool-19`, `pool-20`...).
3. **Cơ Chế Tràn Tải Hoạt Động**:
   - Trong điều kiện bình thường: Dàn Pro gánh trọn vẹn request của hệ thống.
   - Khi cao điểm: Nhiều subagent chạy song song, dàn Pro chạm trần `maxConcurrent` hoặc gặp 429 tạm thời $\rightarrow$ OmniRoute tự động tràn (spillover) một vài request thật xuống các tài khoản ở đuôi.
   - **Kết quả**: Tài khoản starter được "nuôi trust" hoàn toàn bằng prompt công việc thật, đi qua đúng IP proxy 4G cố định, tăng trust hữu cơ 100% mà không tốn công quản lý thêm bất kỳ combo phụ nào.

---

## 5. Kỷ Luật Tuyệt Đối CẤM Đổi Tên Combo Khi Cập Nhật Targets (`ag-gemini-pool-3`)
- **Cảnh báo từ người vận hành ("Là sao đừng có đổi tên combo k lỗi hết model đó")**:
  Khi mở rộng hoặc nối thêm target accounts vào combo, **TUYỆT ĐỐI KHÔNG ĐƯỢC THAY ĐỔI TRƯỜNG `name` CỦA COMBO** (ví dụ cấm đổi thành `ag-gemini-pool-3-v2`, `ag-pool-new`...).
- **Hệ quả nếu đổi tên combo**:
  - Toàn bộ các cấu hình client, Hermes Agent (`config.yaml`), subagent dispatcher (`delegate_task`), model aliases (`mitmAlias`), fallback chains (`auxiliary.compression.fallback_chain`) và các combo cha lồng ghép (`review`, `ag-worker`) đều đang bind cứng vào chuỗi định danh `"ag-gemini-pool-3"`.
  - Thay đổi tên combo sẽ làm gãy toàn bộ đường dẫn gọi API, router trả về `404 Not Found` hoặc `ALL_TARGETS_SKIPPED`, làm tê liệt và sập toàn bộ các AI Agent đang chạy trên farm!
- **Quy tắc thao tác chuẩn**:
  - Giữ nguyên `name: "ag-gemini-pool-3"`.
  - Chỉ append thêm các target mới vào mảng `models` với nhãn thứ tự tăng dần (`label: "pool-19"`, `"pool-20"`...).

---

## 6. Khắc Phục Bẫy Lỗi 500 Khi Exchange OAuth Antigravity (`/api/oauth/antigravity/exchange`)
- **Hiện tượng**:
  Trình duyệt Playwright đã đăng nhập Google và bấm "Cho phép" cấp quyền OAuth thành công 100%, bắt được Authorization Code (`4/0ATsMZq...`), nhưng khi gọi `POST /api/oauth/antigravity/exchange` lên OmniRoute thì server trả về lỗi `500 Server Error: Internal Server Error`.
- **Nguyên nhân gốc rễ**:
  1. *Single-Use Authorization Code & Redirection Loop*: Mã authorization code của Google là **dùng 1 lần (single-use)**. Nếu network listener trên Playwright bắt được URL `/callback` 2 lần do redirect loop hoặc script gọi exchange 2 lần liên tiếp, lượt gọi thứ 2 sẽ bị Google từ chối với lỗi `invalid_grant: Bad Request`. OmniRoute bắt exception này và ném 500 ra ngoài.
  2. *Bẫy Mismatch PKCE Code Verifier*: Provider `antigravity` trong OmniRoute dùng `flowType: "authorization_code"` (không phải PKCE). `buildAntigravityAuthUrl` không đưa `code_challenge` vào URL. Nếu script client gửi kèm `codeVerifier` sai lệch hoặc session authorize bị desync giữa các lần khởi tạo, Google token endpoint sẽ từ chối grant code.
- **Giải pháp chuẩn hóa**:
  1. **Dùng Runner Chuẩn Hóa `add_oauth_omniroute.py`**:
     - Sử dụng một instance `omni_client` duy nhất để lấy `auth_data` rồi mở persistent context của profile GPM tương ứng, đảm bảo `redirect_uri` và `state` khớp hoàn toàn.
  2. **Khóa Chặn Duplicate Exchange**:
     - Đặt cờ `code_exchanged = True` ngay sau lần exchange đầu tiên để không bao giờ gửi code trùng lặp.
  3. **Bắt Buộc Bóc Tách Log Response Chi Tiết**:
     - CẤM gọi `res.raise_for_status()` mù. Bắt buộc in rõ `res.status_code` kèm `res.text` để nhìn thấy thông báo lỗi thực tế từ Google (`invalid_grant`, `invalid_client`, timeout) thay vì chỉ thấy 500 chung chung.

