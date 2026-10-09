# Quy Chuẩn Định Dạng Báo Cáo Watchdog & Từ Ngữ Báo Cáo (Farm Taadaa)

## 1. Yêu Cầu Cốt Lõi Từ User (2026-10-02)
- **CẤM DÙNG TỪ "LŨY KẾ":** Không dùng các thuật ngữ hành chính kế toán gây khó hiểu, rườm rà như "Lũy kế hôm nay", "Lũy kế đợt này".
- **CẤM TÁCH HAI DÒNG ĐẾM GÂY HIỂU NHẦM:** Cấm in song song 2 dòng kiểu:
  ```text
  • Đã dọn đợt này: 0 máy
  • Lũy kế hôm nay: 74 máy
  ```
  Cách báo cáo này khiến user tưởng bot chạy fail hoặc không dọn được máy nào ở đợt retry.
- **QUY TẮC ĐƠN GIẢN HÓA ("Ghi đơn giản v thôi"):**
  Chỉ hiển thị rõ ràng, trực diện:
  * `• Đã hoàn tất: <N> máy`
  * `• Lỗi (<N>): <list máy lỗi kèm lý do>` (hoặc `• Lỗi (0)`)

## 2. Tiêu Chuẩn Cho Các Watchdog / Báo Cáo Cronjob
- **Dọn Cache TikTok (`cron_clear_tiktok_cache.py`):**
  ```text
  [BÁO CÁO DỌN DẸP CACHE TIKTOK]
  • Đã hoàn tất: 125 máy

  🏢 【FARM KIBE - MÁY 1-80】
  • Đã hoàn tất: 72 máy (01, 02, 03, ...)
  • Lỗi (3): 14, 52, 56
    - Máy 14: Timeout

  🏢 【FARM ADMIN - MÁY 201-280】
  • Đã hoàn tất: 53 máy (201, 202, ...)
  • Lỗi (0)
  ```
- **Nuôi Feed / Follow / Upload / Reg Gmail:**
  Thống nhất dùng `• Đã hoàn tất:` thay vì `• Success:` hay `• Lũy kế:`.
  Thống nhất dùng `• Lỗi:` thay vì `• Fail:`.
- **Silent Watchdog:**
  Đợt quét chạy bù (retry tick) nếu không có thêm máy nào thành công (`s_count == 0`), script BẮT BUỘC im lặng (`return 0`, stdout rỗng), tuyệt đối không in báo cáo "0 máy" ra Telegram.

## 3. Tách Bạch Lỗi Nền Tảng (Platform) vs Lỗi Script (Automation)
- **Chỉ thị của Sếp:** "Lỗi script phải phân loại khác lỗi nền tảng chứ" — CẤM TUYỆT ĐỐI gộp lỗi script và lỗi nền tảng vào chung một số đếm `Fail`.
- **Phân định rạch ròi:**
  * **Lỗi nền tảng (Platform / Google / Network):** `phone_verify`, `account_creation_error`, proxy ban, rate limit, captchas. Đây là lỗi do bên thứ ba hoặc thuật toán chống bot; hướng xử lý là xoay IP hoặc cho máy nghỉ ngâm.
  * **Lỗi script / kỹ thuật (Script / Automation Errors):** `failed_cleanup` (lỗi thao tác UI Android gỡ nick), timeout do tìm sai element, script crash, parse error. Đây là lỗi code automation cần fix ngay, cấm đổ vạ cho nền tảng.
  * **Bỏ qua an toàn (Safe Skip):** Máy đủ slot hoặc chưa tới kỳ dọn; tách riêng khỏi nhóm Lỗi.
- **Mẫu hiển thị báo cáo chuẩn:**
  ```text
  [BÁO CÁO CHUỖI SAU CA TRƯA] [LANE GMAIL]
  - Thời gian: 15:15 -> 15:33 (18 phút)

  - Phase 1 (Reg Gmail - Code 0):
    • Đã hoàn tất: 7 máy
    • Bỏ qua an toàn: 3 máy (đầy slot)
    • Lỗi nền tảng (5): phone_verify: 5
    • Lỗi script: 0
  ```
