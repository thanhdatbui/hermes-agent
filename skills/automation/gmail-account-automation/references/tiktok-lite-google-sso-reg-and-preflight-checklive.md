# Google SSO Preflight Check & TikTok Lite Device Ageing Runbook

## 1. Bản chất phân hóa: Hotmail Manual vs Google SSO trên TikTok Lite
- **Hotmail Manual (Gõ tay @hotmail.com):**
  - Luồng webmail gõ tay trên thiết bị đã cắm nhiều nick bị ByteDance Anti-Fraud xếp vào diện cày farm tự động.
  - Sau bước nhập DOB, TikTok server phát lệnh **Instant-Ban** ("Tài khoản của bạn đã bị cấm").
- **Google SSO ("Tiếp tục với Google"):**
  - Sử dụng API Google Sign-In bảo lãnh danh tính thật từ Google Play Services.
  - Vượt qua bộ lọc thiết bị cày farm, không cần tạo pass, vào thẳng Profile với trạng thái LIVE 100%.

## 2. Rủi ro Google Re-Authentication Challenge (24h Window)
- **Tài khoản mới reg tươi (trong vòng vài giờ):** Session Google Play Services trên máy còn tươi nguyên -> SSO 1 chạm vào thẳng hồ sơ.
- **Tài khoản reg sau ~24h:** Google Play Services có thể rơi vào trạng thái cần re-auth ngầm trên Android 8.0 (legacy OS), kích hoạt form "Xác minh danh tính của bạn" (yêu cầu gõ lại mật khẩu Google).
- **Quy tắc thời điểm:** Tốt nhất nên bấm SSO TikTok Lite ngay trong ca reg Gmail trên máy thật khi session Google còn tươi.

## 3. BẮT BUỘC: Preflight Check Live Gmail trước khi lấy reg/SSO
- **KHÔNG ĐƯỢC CHỦ QUAN:** Tuyệt đối không thấy có tên tài khoản trong `dumpsys account` là mang đi reg/SSO ngay.
- **Cơ chế Preflight qua GPM CDP / Google Sign-in Lookup:**
  - Kết nối Chrome qua profile proxy sạch (tránh dính IP blacklist).
  - Điều hướng tới `https://accounts.google.com/v3/signin/identifier?flowName=GlifWebSignIn&flowEntry=ServiceLogin`.
  - Nhập email mục tiêu và bấm `#identifierNext`.
  - **Phân loại kết quả:**
    - `Welcome` + Ô nhập Password: **LIVE 100%** -> Đủ điều kiện mang đi reg/SSO.
    - `Verify it's you` / `Confirm you're not a robot` / Challenge: **ĐANG BỊ TREO XÁC MINH** -> Bị chặn cấp quyền OAuth/SSO trên thiết bị, CẤM mang đi reg TikTok Lite.
    - `Couldn't find your Google Account`: **DIE / BỊ XÓA** -> Evict ngay khỏi hệ thống.

## 4. Kỷ luật tích hợp vào Pipeline Runner (Anti-Hang & Queue Timeout)
- **Tích hợp cứng vào `scripts/gmail_preflight_filter.py`:**
  - CẤM gọi checkmail.live hoặc web probe trực tiếp trong luồng chính không có cơ chế ngắt; trang check mail bên thứ 3 thường xuyên bị Cloudflare / Turnstile hoặc rớt mạng gây treo toàn bộ batch chạy.
  - Sử dụng mô hình `threading.Thread(daemon=True)` kết hợp `queue.Queue(maxsize=1)`.
  - Thiết lập timeout trần cứng (45s). Nếu quá thời gian, giải phóng luồng (`queue.Empty`) và fallback an toàn, tuyệt đối không làm tê liệt hay đóng băng runner farm.
  - Chỉ lọc bỏ (`[DIE-SKIP]`) và dọn sạch khi và chỉ khi kết quả trả về tường minh là `False` (DIE / Challenge confirmed). Mọi ngoại lệ timeout/mạng phải fallback giữ nguyên targets để không làm đứt gãy luồng vận hành chính.

## 5. Kỷ luật phản hồi và cơ chế chống bị chặn khóc lóc (Receipt Guard vs Veto Trap)
- **Bản chất bẫy "Bị chặn khóc lóc" (Whining & Paralysis Trap):**
  - Khi Coordinator gặp rào cản kỹ thuật (hết ngân sách sửa code T1 >500 dòng, Worker bị chặn pytest, hoặc rớt kết nối), phản xạ sai lầm tệ nhất là: **Mở mồm xin lỗi, văn vở, nhận lỗi sâu sắc ("Em nhận lỗi sâu sắc...") hoặc hứa suông ("Em bắt đầu triển khai ngay...")**.
  - **Receipt Guard Hook** ở gateway quét tin nhắn: nếu phát hiện lời khẳng định/nhận lỗi dông dài mà không có biên lai thực thi thật (`task_id / success receipt` trong cùng turn), hệ thống sẽ lập tức **đóng dấu đỏ cảnh báo vi phạm**: `⚠️ [HỆ THỐNG CẢNH BÁO — CHƯA CÓ WORKER NÀO CHẠY THẬT]`.
- **Kỷ luật ứng xử bắt buộc khi bị chặn:**
  - **CẤM TUYỆT ĐỐI văn xin lỗi/khóc lóc:** Không nhận lỗi dông dài, không giải thích lòng vòng, không hứa hẹn tương lai.
  - **Hành động ngay bằng lệnh/tool:** Bị chặn lệnh A thì lập tức leo thang đúng nấc sang phương án B (gọi Worker với scope chuẩn O(1), dùng script có sẵn, hoặc báo thẳng nguyên nhân gốc rễ bằng dữ liệu kỹ thuật trần trụi).
  - **Chỉ nói sau khi đã có bằng chứng:** Chỉ khẳng định "Đã làm xong" khi git commit / test log / diff thực tế đã xuất hiện.
