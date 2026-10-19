# Hotmail -> GPM -> ChatGPT -> Codex Lifecycle Supervisor & Reporting Discipline

## 1. Bản chất sự cố và Bài học điều phối

Khi vận hành supervisor đa giai đoạn (`HOTMAIL_LOGIN` -> `CHATGPT_REG` -> `CODEX_OAUTH` -> `WAIT_7D` -> `CHANGE_INFO`):
- **Lỗi Starvation do thiếu Failure Cooldown:** Khi một giai đoạn (như Codex OAuth) thất bại hàng loạt (ví dụ hết số dư 5SIM, bot-check OpenAI), nếu supervisor tự động unblock tài khoản sau thời gian ngắn (30 phút) mà không áp dụng per-account failure cooldown (tối thiểu 6h):
  + Hàng trăm tài khoản lỗi sẽ chiếm trọn 100% worker slots ở mọi tick cron.
  + Các tài khoản ở giai đoạn đầu phễu (`HOTMAIL_LOGIN`, `CHATGPT_REG`) bị bỏ đói (starvation), hoàn toàn không được chạy.
  + Số lượt chạy fail tăng vọt (hàng trăm lượt/6h), đốt tài nguyên proxy và CPU vô ích.

## 2. Quy tắc Supervisor Cooldown & Unblock
1. **Per-Account Failure Cooldown:**
   - Tài khoản thất bại ở bất kỳ stage nào (`HOTMAIL_LOGIN`, `CODEX_OAUTH`) bắt buộc phải có thời gian ngâm cooldown tối thiểu **6 giờ** trước khi được thử lại.
   - Ghi nhận `retry_count` và timestamp thất bại rõ ràng (`at`).
   - CẤM unblock mù quáng chỉ dựa trên trạng thái tổng thể hoặc sau 30 phút.
2. **Fallback an toàn cho timestamp:**
   - Khi kiểm tra cooldown, nếu `last_result.at` là `None` (do state cũ hoặc khởi tạo), BẮT BUỘC fallback sang `updated_at` của profile. Tuyệt đối không để `fail_time is None` dẫn đến tài khoản bị kẹt vĩnh viễn không bao giờ được unblock.
3. **Fair Scheduling (Chống bỏ đói):**
   - Phân bổ candidate cân bằng giữa các giai đoạn hoặc ưu tiên giải quyết các tài khoản đầu phễu (`HOTMAIL_LOGIN`) trước khi tái thử thách các tài khoản đã fail nhiều lần.

## 3. Tiêu chuẩn Báo cáo Vòng đời (6H Lifecycle Report Discipline)
User không thể nắm bắt được tiến độ nếu báo cáo nhảy cóc chỉ nói về ngọn mà bỏ quên gốc:
- **Chống Báo Cáo Tích Lũy Tù Mù (Time-Window Delta vs Cumulative Snapshot Invariant):**
  + Báo cáo định kỳ (6H / 12H / 24H) TUYỆT ĐỐI CẤM chỉ xuất số tổng tích lũy (Cumulative Lifetime Snapshot như `676/1037 login`, `155/1037 done`). Nếu chỉ có số tổng, User hoàn toàn không biết trong 6h qua farm có chuyển động hay không, tốc độ xử lý ra sao, hay đang bị đóng băng.
  + BẮT BUỘC có khối **⚡ BIẾN ĐỘNG & TIẾN ĐỘ 6H QUA (Time-Window Activity & Throughput)** đặt ở vị trí nổi bật:
    * Lọc theo timestamp sự kiện: `cutoff = now - timedelta(hours=6)` dựa trên `last_result.at`, `hotmail_login_at`, `chatgpt_registered_at`.
    * Tổng lượt xử lý trong 6h: `N` accounts (bóc tách rõ từng Farm: Kibe: `k` | Admin: `a`).
    * Tăng trưởng delta dương: `+X` Login Hotmail mới, `+Y` Reg ChatGPT mới, `+Z` Đổi pass DONE mới.
    * Thất bại / Cooldown mới trong 6h: `+W` accounts (ghi rõ lý do chính).
    * Bằng chứng máy/acc vừa hoàn tất: Liệt kê các máy tiêu biểu vừa finish (ví dụ: `Admin: M218, M220, M226...`).
    * Cảnh báo trạng thái ca: Cảnh báo ngay nếu 1 farm có 0 hoạt động (ví dụ: "Kibe tạm dừng xử lý do 47 port đang ngâm cooldown IP 24h").
- **Đầy đủ phễu từ Gốc đến Ngọn:** Bảng tổng quan tích lũy bắt buộc có đủ:
  + Hotmail Login (Thành công / Tổng, Kẹt / Thất bại).
  + ChatGPT Reg (Thành công / Tổng).
  + Codex OAuth (Thành công / Tổng, Tỉ lệ thành công 6h).
  + Các giai đoạn ngâm (WAIT_24_48H, WAIT_7D).
  + Change Info & Hoàn thành (DONE).
- **Minh bạch trạng thái Cooldown:** Báo cáo rõ số lượng tài khoản đang ngâm cooldown chờ thử lại của từng giai đoạn (ví dụ: "Đang cooldown chờ thử lại OAuth: 214", "Đang cooldown chờ thử lại Login: 17").
- **Chi tiết lỗi rõ ràng:** Không dùng text fallback chung chung kiểu "Login / Auth thất bại". Phải ghi rõ nguyên nhân (sai pass, thiếu token, khóa bảo mật, hết số 5SIM, connection refused).
