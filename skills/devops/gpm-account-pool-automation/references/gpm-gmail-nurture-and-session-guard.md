# Hướng Dẫn Nuôi Gmail Trên GPMLogin & Kiểm Soát Session Guard

Tài liệu chuẩn hóa kiến trúc nuôi tự động Gmail trên GPMLogin qua Playwright CDP, cơ chế kiểm soát token session Google, chống nghẽn hàng đợi (Selection Loop Choke) và tối ưu công suất nuôi cho farm.

---

## 1. Cơ Chế Preflight Cookie Guard & Chống Nghẽn Tuyển Chọn (Selection Loop Choke)

### Vấn đề cốt lõi
Khi script nuôi Gmail (`cron_gpm_gmail_nurture.py`) được trang bị **Preflight Cookie Guard**:
- Script kiểm tra các cookie xác thực cốt lõi của Google (`SID`, `SSID`, `HSID`, `SAPISID`).
- Nếu số lượng session token < 2, script hiểu là profile chưa login hoặc đã mất session Google, lập tức đóng profile và gán cờ `NEEDS_LOGIN` vào state file để tránh lãng phí tài nguyên và tránh lộ profile trắng.

### Bẫy ngầm (Critical Pitfall - Selection Loop Choke)
- Nếu hàm tuyển chọn ứng viên (`due_profiles`) chỉ sắp xếp theo `last_nurtured` tăng dần mà **không kiểm tra cờ trạng thái**:
  - Những profile chưa bao giờ được nuôi có `last_nurtured = 0`.
  - Các profile chưa login (`NEEDS_LOGIN`) cũng có `last_nurtured = 0`.
  - **Hậu quả**: Cứ mỗi tick cron, script luôn bốc đúng các profile chưa login này lên đầu danh sách $\rightarrow$ mở ra $\rightarrow$ phát hiện 0 token $\rightarrow$ đóng ngay và báo `FAIL`. Quá trình này lặp lại vô tận ở mọi tick, làm nghẽn toàn bộ hàng đợi nuôi, khiến 80-100 profile đã login phía sau không bao giờ được nuôi!

### Giải pháp bắt buộc
1. **Lọc loại trừ trước khi enqueue**:
   ```python
   # Trong hàm lọc ứng viên:
   for p in candidates:
       em = p["email"]
       info = state.get(em, {})
       # BẮT BUỘC loại trừ profile đang chờ login
       if info.get("status") == "NEEDS_LOGIN":
           continue
       last_nurtured = info.get("last_nurtured", 0)
       if (now_ts - last_nurtured) >= NURTURE_INTERVAL_SECONDS:
           due_profiles.append((last_nurtured, p))
   ```
2. **Cập nhật mốc kiểm tra cho profile lỗi/chưa login**:
   Khi phát hiện `NEEDS_LOGIN` hoặc lỗi nghiêm trọng, gán `last_attempt = now_ts` và áp dụng cooldown (ví dụ: chỉ thử lại sau 24h hoặc nhường quyền kích hoạt cho watchdog login chuyên trách), tuyệt đối không để `last_nurtured = 0` đứng đầu hàng đợi.

---

## 2. Tính Toán Công Suất Nuôi & Nhịp Độ Chu Kỳ (Throughput & Cadence Sizing)

### Nguyên tắc nhịp độ
- Chu kỳ nuôi Google hợp lý cho tài khoản live là **2 - 4 ngày/lần** (không nuôi quá dày gây tốn proxy/băng thông, không nuôi quá thưa gây nguội cookie).
- **Công thức tính dung lượng**:
  $$\text{Target Cycle (ngày)} = \frac{\text{Tổng Profile Sẵn Sàng Nuôi}}{\text{Số Lần Chạy / Ngày} \times \text{Limit / Lần}}$$

### Bẫy "Mắc kẹt ở cấu hình Canary"
- Khi thử nghiệm ban đầu (Canary), thường cấu hình `--limit 2` để quan sát an toàn.
- Nếu quên nâng limit sau khi Canary ổn định:
  - Với 100 profile và 7 khung giờ/ngày $\rightarrow 100 / (7 \times 2) \approx 7.1$ ngày mới đi hết 1 vòng (quá dài, tài khoản bị nguội).
- **Cấu hình tối ưu cho PC Dual Xeon & Proxy 4G**:
  - `--limit 6` đến `--limit 8` mỗi đợt.
  - `--concurrency 2` (2 worker so le, giãn cách `--stagger 45` - 60s). Mỗi worker gắn với 1 cổng proxy 4G riêng biệt.
  - Tốc độ: $7 \text{ lần/ngày} \times 6 \text{ acc} = 42 \text{ lượt/ngày} \rightarrow$ Hoàn tất trọn vòng 100 acc chỉ trong **2.3 ngày**, hoàn toàn khớp với nhịp tự nhiên.

---

## 3. Quản Lý Tab Tuần Tự & Đóng Profile Sạch Sẽ

1. **Tab tuần tự (Chỉ duy nhất 1 Tab)**:
   - Khi chuyển từ YouTube sang Google News hoặc Search: đóng tab cũ trước khi mở tab mới, hoặc điều hướng trực tiếp trên tab hiện tại.
   - Tuyệt đối không để 2-3 tab chạy nền cùng lúc vì Playwright + Chromium ngốn nhiều RAM và CPU.
2. **Đóng 3 lớp an toàn**:
   - Lớp 1: `context.close()` / `browser.close()`.
   - Lớp 2: Gọi GPM API `/api/v3/profiles/close/{id}` (hoặc `/stop/{id}`).
   - Lớp 3: Kiểm tra tasklist sau 2s, nếu tiến trình Chrome của profile còn sót thì force kill dứt điểm để giải phóng Taskbar.

---

## 4. Kỷ Luật Báo Cáo Cron & Nhãn Trạng Thái (Status Semantics)

1. **Minh bạch nhãn trạng thái (Status Semantics)**:
   - Tránh báo chung chung `FAIL` khi profile bị dừng do Preflight Cookie Guard.
   - Báo cáo và state file phải phân biệt rõ:
     + `OK`: Nuôi thành công trọn vẹn kịch bản.
     + `CHƯA_LOGIN (NEEDS_LOGIN)`: Profile trắng, chưa login Google hoặc mất session (<2 cookies SID/SSID/HSID/SAPISID). Dừng nuôi bảo vệ tài nguyên.
     + `FAIL (<reason>)`: Lỗi runtime thực sự (START_FAILED, timeout CDP, proxy die, crash).

2. **Chống Rác Farm Alert**:
   - Tác vụ nuôi thường quy chạy nhiều lần trong ngày (7-8 lần/ngày).
   - **Quy tắc**:
     - Cronjob nuôi định kỳ BẮT BUỘC cấu hình `deliver='local'` (hoặc stdout chỉ in khi có sự cố hệ thống cấp P0).
     - Không gửi thông báo thường quy `Hoàn tất nuôi X/Y profile` lên Telegram Farm Alert để tránh gây loãng thông tin vận hành quan trọng của Phone Farm.

---

## 5. BẢO TOÀN PROFILE GPM & TÀI KHOẢN VER SỐ (INVARIANT: CẤM TỰ XÓA PROFILE KHI GMAIL DIE)

### Vấn đề thực tế & Rủi ro
Nhiều profile GPM được tạo từ Gmail ban đầu đã được dùng để đăng ký các dịch vụ phụ trợ quan trọng:
- **Tài khoản OpenAI / ChatGPT / Codex**: Đã tốn tiền nạp SIM (5sim / SMS OTP) để verify số điện thoại thành công.
- Lưu session, cookies, refresh token của các công cụ AI và nền tảng thứ ba.

### Nguyên tắc bất biến
1. **Gmail Die KHÔNG đồng nghĩa Profile GPM là rác**:
   - Dù Gmail bị Google vô hiệu hoá hoặc đổi mật khẩu, tài khoản OpenAI/ChatGPT tạo bằng email/pass đó vẫn hoạt động và đăng nhập bình thường (farm dùng Email + Password riêng, tuyệt đối không dùng Google SSO).
   - Session đăng nhập trong profile GPM vẫn còn hiệu lực. Nếu script tự động xóa profile GPM, toàn bộ tiền thuê số verify và tài khoản AI/Codex sẽ bị mất trắng.
2. **Kỷ luật trong script đồng bộ vòng đời (`sync_gpm_lifecycle.py`)**:
   - **CẤM TUYỆT ĐỐI** gọi API xóa profile GPM (`/profiles/delete/{id}`) đối với các Gmail trạng thái `DIE`, `BAN`, `SUSPENDED`.
   - Script chỉ thực hiện:
     + Đọc danh sách profile hiện có từ SQLite DB (`profile_data.db`) để tránh tạo trùng cho Gmail `LIVE` mới.
     + Bỏ qua hoàn toàn hành vi xóa profile DIE.
3. **Quản lý trạng thái & Lưu trữ (Source of Truth)**:
   - File vận hành `gmail_clean_v2.xlsx`: Có thể bỏ qua mail die để máy S7 không chạy batch nuôi mail.
   - Sổ cái `master_gmail_manager.xlsx` (Sheet `Master_All`): BẮT BUỘC giữ nguyên vẹn 100% dòng thông tin của cả mail `LIVE` và `DIE` (đổi cột `Trạng Thái` sang `DIE`, giữ nguyên Password, 2FA, SDT, Proxy, Tên Profile GPM). Tuyệt đối không xóa dòng trong Master.
