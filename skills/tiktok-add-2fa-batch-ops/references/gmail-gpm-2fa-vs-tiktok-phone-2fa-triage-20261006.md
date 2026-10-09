# Triage Bẫy Nhầm Lẫn Giữa Cron 2FA Gmail Sáng (GPM) vs Cron Add 2FA TikTok Trưa (Phone Farm) & Phân Biệt Màn TikTok Security Check (06/10/2026)

## 1. Hiện tượng & Câu hỏi thường gặp từ Operator
Operator thấy màn hình điện thoại dừng ở trang TikTok "Kiểm tra bảo mật" (có dòng "Xác minh 2 bước") và thắc mắc:
> *"Này là màn xác minh 2 bước mà, do có cron đang chạy add 2fa tiktok hay sao v? Mà tao đéo thấy report chạy add 2fa tiktok vì sao?"*

---

## 2. Bản chất hai hệ thống Cron 2FA độc lập trong Farm

| Tiêu chí | Cron Sáng: `post-morning-gmail-2fa-watchdog` | Cron Trưa: `post-noon-chain-watchdog` |
| :--- | :--- | :--- |
| **Mục tiêu** | Bật 2FA Google Authenticator cho **Gmail trên GPMLogin (PC)** | Chuỗi 2 Phase trên **Android Phone Farm**: Phase 1 (Reg Gmail) $\rightarrow$ Phase 2 (**Add 2FA TikTok**) |
| **Khung giờ** | **08:30 – 11:30** (Sáng) | **14:00 – 17:30** (Sau ca trưa) |
| **Thiết bị tác động** | Trình duyệt GPM Chrome trên máy tính Kibe | Dàn điện thoại Android (máy 1–80) qua ADB / ViChanger / TikTok app |
| **Delivery kênh tin** | `deliver: local` (Chỉ ghi state, **KHÔNG gửi Telegram**) | `deliver: telegram:-5373649734` (Gửi report kết quả về Telegram) |
| **File state** | `D:/Taadaa/runtime/kibe/cron-state/post_morning_gmail_2fa_state.json` | `D:/Taadaa/runtime/kibe/cron-state/post_noon_chain_state.json` |
| **Nguyên nhân mất report** | Thiết kế mặc định là local silent, chỉ chạy ngầm GPM. | (1) Chưa đến khung giờ (chưa tới 14:00); hoặc (2) Phase 1 Reg Gmail bị fail (`lane_status: failed`) khiến Phase 2 Add 2FA bị skip hoàn toàn. |

---

## 3. Nhận diện Màn hình TikTok "Kiểm tra bảo mật" (Security Check)

1. **Ý nghĩa giao diện:**
   - Tiêu đề: **"Kiểm tra bảo mật"** (Security check).
   - Nội dung: Gợi ý các lớp bảo mật gồm *Điện thoại*, *Xác minh 2 bước*, *Passkey*, *Email*.
   - **Biểu tượng chấm than tròn xám:** Thể hiện tính năng đó **ĐANG TẮT** (chưa được thiết lập). Chỉ khi có dấu tích xanh (như dòng Email) thì lớp bảo mật đó mới được kích hoạt.
2. **Không đồng nghĩa với tiến trình đang chạy:**
   - Màn hình này có thể xuất hiện khi app TikTok mở trang quản lý bảo mật tài khoản, hoặc do người dùng/script trước đó dừng lại tại đây.
   - Nó **KHÔNG phải là bằng chứng** cho thấy worker Add 2FA đang thao tác.
   - Để khẳng định có worker chạy hay không, bắt buộc kiểm tra 3 điểm O(1):
     1. Lệnh `python D:/Taadaa/tools/inspect_machine.py <N>`: xem `mCurrentFocus` và trạng thái màn hình.
     2. Thư mục lock: `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json`. Nếu không có file lock hoặc `owner_active: false`, máy hoàn toàn không có tiến trình chạy.
     3. Tiến trình hệ thống: `ps -ef | grep 2fa` hoặc kiểm tra cron scheduler state.

---

## 4. Checklist phản hồi dứt khoát cho Operator

Khi Operator hỏi về việc màn hình hiện xác minh 2 bước và thiếu report:
1. **Khẳng định ngay màn hình:** Đây là màn hình gợi ý bảo mật tĩnh của TikTok, icon chấm than xám xác nhận 2FA vẫn đang TẮT.
2. **Chỉ rõ khung giờ:** Cron Add 2FA TikTok chỉ chạy sau 14:00 (`post-noon-chain-watchdog`). Buổi sáng chỉ có cron bật 2FA cho Gmail trên GPM (chạy local, không đẩy Telegram).
3. **Kiểm tra dependency chain:** Đọc ngay `post_noon_chain_state.json` để kiểm tra xem hôm trước chuỗi có bị kẹt ở Phase 1 (Reg Gmail) hay không. Nếu Phase 1 fail, giải thích rõ Phase 2 không được kích hoạt nên không có report.
