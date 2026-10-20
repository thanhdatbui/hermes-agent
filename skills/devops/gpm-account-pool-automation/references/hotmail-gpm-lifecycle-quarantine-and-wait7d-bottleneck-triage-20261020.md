# Hotmail -> GPM -> ChatGPT Lifecycle: Quarantine Triage, WAIT_7D Bottlenecks & Transparent 6H Reporting

## 1. Hiện Trường Sự Cố (2026-10-20)
Trong phiên kiểm tra định kỳ 6H của `cron_hotmail_gpm_lifecycle_6h_report.py`:
- Báo cáo bề mặt hiển thị: `Queue: 1037`, `WAIT_7D: 513`, `BLOCKED: 119`, `Farm idle (0 biến động trong 6h)`.
- Khi Coordinator truy vết trực tiếp vào state JSON (`batch_gpm_5profiles_supervisor_state.json`) ở Kibe và Admin, phát hiện 3 vấn đề nghiêm trọng bị báo cáo ẩn:
  1. **3 tài khoản Admin đã rơi vào QUARANTINE** (`login_retry_count >= 3`), chết cứng vĩnh viễn và Supervisor không bao giờ tự retry, nhưng báo cáo gom chung thành `BLOCKED: 35`.
  2. **127 tài khoản ở Admin đã ngâm QUÁ 7 ngày**, nhưng hàng đợi `CHANGE_INFO: 0` vì có **229 tài khoản Admin (gồm 20 nick đã đủ 7 ngày) bị thiếu tài khoản TikTok** (`has_tiktok: False`, `password: ''`). Chốt an toàn của Supervisor chặn không cho đổi pass mail khi chưa có TikTok, dẫn đến tắc nghẽn vô thời hạn mà không hiển thị trên báo cáo.
  3. **Delta ảo mâu thuẫn với Farm Idle**: Do snapshot kỳ trước thiếu số liệu `login_ok: 0`, báo cáo in `[+676]` ngay phía trên dòng `Không có biến động nào trong 6h qua (farm idle)`.

---

## 2. Quy Chuẩn Phân Loại Trạng Thái Lỗi (BLOCKED vs QUARANTINE)
- **BLOCKED (Cooldown 48h tạm thời):**
  - Tài khoản đăng nhập thất bại 1 hoặc 2 lần (`login_retry_count < 3`).
  - Được cách ly 48h tính từ `last_result.at`. Khi đủ 48h, supervisor tự động unblock về `PENDING` để retry.
  - Báo cáo phải thể hiện số lượng sắp đáo hạn cooldown (ví dụ: `< 6h`, `< 12h`, `> 24h`).
- **QUARANTINE (Chết cứng - Cần can thiệp người/Excel):**
  - Tài khoản đăng nhập thất bại $\ge 3$ lần (`login_retry_count >= 3`).
  - Supervisor cấm retry tự động để tránh khóa vĩnh viễn tài khoản Microsoft.
  - Bắt buộc bóc tách riêng khỏi mục BLOCKED, in rõ danh sách Machine, Email và lỗi chi tiết để quản trị viên đối soát mật khẩu với Excel nguồn (`taikhoan_dat_v2_updated .xlsx`).

---

## 3. Quy Tắc Bóc Tách Nút Thắt Hàng Đợi WAIT_7D (Bottleneck Observability)
Trong giai đoạn `WAIT_7D`, tài khoản ngâm 7 ngày trước khi đổi mật khẩu và thông tin bảo mật (`CHANGE_INFO`). Báo cáo định kỳ BẮT BUỘC bóc tách 3 nhóm con:
1. **Đang ngâm dưỡng (`still_soaking < 7d`):** Chưa đủ 7 ngày từ mốc `hotmail_login_at` / `chatgpt_registered_at`.
2. **Sẵn sàng chuyển đổi (`eligible >= 7d`):** Đã đủ $\ge 7$ ngày VÀ có đầy đủ cả tài khoản TikTok (`has_tiktok` hoặc `username + password`) lẫn ChatGPT (`has_chatgpt` hoặc `chatgpt_registered_at`).
3. **Bị chặn do thiếu điều kiện (`missing_prerequisite`):**
   - Đã ngâm đủ $\ge 7$ ngày nhưng `has_tiktok: False` hoặc `password: ''` (chưa reg/gán nick TikTok).
   - Chốt an toàn ngăn không cho đổi pass Hotmail để tránh mất liên kết asset.
   - Nhóm này phải được báo cáo định lượng để đưa vào hàng đợi reg TikTok Phone Farm gỡ nghẽn.

---

## 4. Giải Trình Nguyên Nhân Farm Idle & Lịch Đáo Hạn Cooldown (Actionable ETA)
- Khi toàn bộ hoặc một cụm Farm ở trạng thái `idle` (0 lượt xử lý trong 6h), cấm chỉ ghi dòng thông báo thụ động "Farm idle".
- Bắt buộc giải trình nguyên nhân hạ tầng:
  - Giãn cách an toàn IP 24h (`ip_action_history` trên proxy port).
  - Cooldown đăng nhập lỗi 48h.
- Cung cấp thời điểm dự kiến mở khóa (ETA) gần nhất để người vận hành biết hệ thống vẫn đang sống và đúng nhịp kiểm soát.

---

## 5. Phòng Chống Delta Ảo Khi Khởi Tạo / Nâng Cấp Snapshot
- Trong hàm tính delta `_fmt_delta(curr, prev)`:
  - Nếu `prev` không tồn tại, hoặc `prev == 0` trong khi `curr > 0` ngay sau khi chuyển đổi định dạng snapshot, cấm xuất delta `[+curr]` gây hiểu lầm là có tăng trưởng đột biến trong 6h qua.
  - Chỉ tính delta khi `prev_snapshot` hợp lệ và có cùng định dạng schema.
