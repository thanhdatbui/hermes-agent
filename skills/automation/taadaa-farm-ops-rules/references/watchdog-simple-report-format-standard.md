# Quy Chuẩn Định Dạng Báo Cáo Watchdog & Cron Farm (Đơn Giản Hóa)

> **User directive (2026-10-02):** "Đã hoàn tất / Lỗi / Ghi đơn giản v thôi". CẤM dùng các thuật ngữ hành chính/kế toán gây lú lẫn như "Lũy kế".

---

## 1. Nguyên Tắc Cốt Lõi
- Mọi báo cáo tự động từ Watchdog / Cronjob gửi lên Telegram cho User phải tối giản, phản ánh đúng tình trạng thực tế chỉ qua 1 cái liếc mắt.
- **CẤM TUYỆT ĐỐI các từ ngữ:**
  - `Lũy kế`, `Lũy kế hôm nay`
  - `Đã dọn đợt này`, `Đã chạy đợt này`, `Đợt này: 0 máy`
- Tránh việc in 2 dòng đếm số lượng cùng lúc (vừa đợt này vừa hôm nay) gây trùng lặp thừa thãi ở lần chạy đầu, hoặc gây hoang mang ở các nhịp retry bù (báo "0 máy" dù trước đó đã xong 95%).

---

## 2. Bộ Cặp Nhãn Bắt Buộc & Tách Bạch Lỗi (Platform vs Script)
Báo cáo toàn farm hoặc theo từng cụm (Kibe / Admin) bắt buộc dùng các nhãn chuẩn sau:

- **Thành công:**
  - `• Đã hoàn tất: <N> máy`
  - Kèm danh sách số máy nếu cần: `• Đã hoàn tất: 72 máy (01, 02, 03, ...)`
- **Bỏ qua an toàn (nếu có máy đầy slot hoặc skip an toàn):**
  - `• Bỏ qua an toàn: <N> máy (đầy slot)` (TUYỆT ĐỐI CẤM gom vào lỗi)
- **TÁCH BẠCH 2 NHÓM LỖI (BẮT BUỘC - Operator Invariant):**
  - "Lỗi script phải phân loại khác lỗi nền tảng chứ" (CẤM gom chung!).
  - **Lỗi nền tảng (Platform / Partner / Anti-bot):**
    - `• Lỗi nền tảng (<N>): <chi_tiết>` (Ví dụ: `phone_verify: 5`, `proxy_die`, `captcha_block`, `account_creation_error`)
    - Khi không có lỗi: `• Lỗi nền tảng: 0`
  - **Lỗi script (Automation / UI / Crash):**
    - `• Lỗi script (<N>): <chi_tiết>` (Ví dụ: `failed_cleanup: 1`, `WIDGET_MISS: 2`, `element not found`, `syntax_error`)
    - Khi không có lỗi: `• Lỗi script: 0`
- **Từng máy lỗi cụ thể (kèm phân loại):**
  - `  - Máy XX [Nền tảng]: Phone verification`
  - `  - Máy YY [Script]: Gỡ tài khoản cũ thất bại (REMOVE_FAILED)`

---

## 3. Mẫu Chuẩn Cho Watchdog / Cron (Ví dụ Cron Clear Cache):
```text
[BÁO CÁO DỌN DẸP CACHE TIKTOK]
• Đã hoàn tất: 125 máy

🏢 【FARM KIBE - MÁY 1-80】
• Đã hoàn tất: 72 máy (01, 02, 03, 04, ...)
• Lỗi (3): 14, 52, 56
  - Máy 14: Timeout
  - Máy 52: cache row not found on storage screen
  - Máy 56: Timeout

🏢 【FARM ADMIN - MÁY 201-280】
• Đã hoàn tất: 53 máy (201, 202, 203, ...)
• Lỗi (5): 208, 213, 230, 231, 243
  - Máy 208: WIDGET_MISS
  - Máy 213: Timeout
  - Máy 243: could not confirm cache size after clear
```
