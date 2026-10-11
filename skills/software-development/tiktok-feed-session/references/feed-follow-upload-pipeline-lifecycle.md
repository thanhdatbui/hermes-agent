# Feed-Follow-Upload Pipeline Lifecycle & Post-Feed Hook Architecture

## 1. Kiến Trúc Chu Trình Nuôi Acc Tuần Tự (Pipeline Architecture)
Trong repo `tiktok-luot nuoi acc`, luồng nuôi tài khoản trên từng máy được thiết kế thành **Pipeline tuần tự khép kín**, hình thành từ commit gốc `f732220` (ngày 16/08/2026):
- **Không chạy cron rời rạc:** Follow chéo và Upload video không chạy như cron độc lập ngoài hệ điều hành, mà được tích hợp thành **subprocess hooks** kích hoạt ở cuối phiên Feed của từng máy trong `multi_machine_feed_session.py`.
- **Thứ tự thực thi trên từng máy:**
  ```text
  [1. Preflight Proxy/Wi-Fi]
          ↓
  [2. Feed Session (Lướt video, thả tim, đọc comment)]
          ↓
  [3. Post-Feed Follow Hook (_run_follow_hook)]
          ↓
  [4. Post-Feed Upload Hook (_run_upload_hook)]
          ↓
  [5. Teardown (Đóng app, clear recent apps, về Home)]
  ```

---

## 2. Cơ Chế Fail-Closed Sensitive Guard (Gating Giữa Feed và Follow)
Để ngăn chặn tình trạng tài khoản bị TikTok gắn cờ bot hoặc nhả follow hàng loạt khi app đang gặp sự cố, hệ thống áp dụng **Sensitive Guard**:
- **Điều kiện mở cổng Follow:**
  1. Phiên lướt Feed hoàn thành thành công (`success` hoặc `degraded`).
  2. HOẶC phiên lướt Feed đã hoàn thành tối thiểu $\ge 3$ lượt vuốt video (`completed_swipes >= 3`, đủ độ ấm telemetry).
  3. HOẶC nick đã có ít nhất 1 phiên lướt Feed thành công trước đó trong cùng ca (`_has_prior_successful_feed_session_in_shift`).
- **Điều kiện kích hoạt hủy an toàn (Sensitive Skip):**
  - App gặp lỗi bảo mật/tài khoản nặng: `_SENSITIVE_ACCOUNT_WORDS` (`checkpoint`, `banned`, `suspended`, `logged_out`, `captcha`, `login`, `account_mismatch`, `wrong_account`...).
  - App bị mất focus, kẹt splash/ad lúc khởi động không vuốt qua được, hoặc tài khoản sau khi chuyển profile không khớp với workbook (`_SENSITIVE_STOP_WORDS`).
  - Khi dính một trong các điều kiện trên, hệ thống lập tức hủy lượt follow của máy đó và ghi nhận:
    `status: "skipped", reason: "sensitive-skip-<final_status>"`

---

## 3. Phân Biệt Các Mã Token Kỹ Thuật (Raw Runner Tokens)
- **`sensitive-skip-failed`:** Phiên Feed bị lỗi (ví dụ: mở TikTok thất bại, không focus được package TikTok sau launch). Không thể vào được app nên hủy bước follow.
- **`sensitive-skip-manual_needed`:** Phiên Feed cần can thiệp thủ công (ví dụ: mất focus app khi bấm vào Profile, kẹt quảng cáo splash, hoặc username trên Profile không khớp với tài khoản chỉ định). Hủy follow để tránh bấm nhầm tài khoản khác.

---

## 4. Chuẩn Hóa Nhãn Hiển Thị Trên Báo Cáo Telegram (Watchdog Mapping)
Trong file `scripts/feed_session_watchdog.py`, toàn bộ các lý do bỏ qua chứa chuỗi `sensitive` được tự động ánh xạ sang nhãn tiếng Việt thân thiện:
- **Nhãn hiển thị:** **`Feed chưa ổn định (N máy)`** (ví dụ: `+ Bỏ qua (71): Đang dưỡng sinh (21); Cooldown nhả follow (25); Feed chưa ổn định (4)`).
- **Mục đích:** Loại bỏ các token kỹ thuật (`sensitive-skip-failed`, `sensitive-skip-manual_needed`) khỏi báo cáo Telegram để người vận hành nắm bắt ngay lý do mà không bị hoang mang.

---

## 5. Kỷ Luật Phản Hồi Khi Người Vận Hành Chất Vấn Kiến Trúc
Khi người vận hành hỏi *"Ai cho phép chế ra rule X? Code trước đã có chưa?"*:
- **CẤM đoán mò hoặc nhận vơ:** Tuyệt đối không tự nhận là mình mới thêm nếu chưa tra cứu Git.
- **BẮT BUỘC tra cứu Git lịch sử:** Dùng `git log -S "<tên_hàm>" --oneline` hoặc `git log -p` để tìm commit SHA gốc, tác giả và ngày tạo.
- **Giải thích có bằng chứng:** Trích dẫn rõ commit SHA, ngày tháng ra đời và tài liệu kiến trúc để người vận hành thấy rõ đây là logic nền tảng đã chạy ổn định từ trước.
