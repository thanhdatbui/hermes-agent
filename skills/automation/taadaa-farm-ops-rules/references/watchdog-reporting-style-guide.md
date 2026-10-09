# Watchdog & Cronjob Reporting Style Guide (Taadaa Farm)

## User Frustration & Context (2026-10-02)
- Khi nhận báo cáo dọn cache TikTok:
  ```text
  [BÁO CÁO DỌN DẸP CACHE TIKTOK]
  • Đã dọn đợt này: 125 máy
  • Lũy kế hôm nay: 125 máy
  ...
  • Fail (3): 14, 52, 56
  ```
- User phản ánh: "Luỹ kế hôm bay là cái éo gì v", và chỉ thị dứt khoát:
  > "Ok sửa đi. Đã hoàn tất. Lỗi. Ghi đơn giản v thôi"

## Quy chuẩn từ khóa báo cáo (BẮT BUỘC)
1. **CẤM thuật ngữ kế toán / cộng dồn rườm rà:**
   - CẤM dùng `"Lũy kế"`, `"Lũy kế hôm nay"`.
   - CẤM tách đôi `"Đã dọn đợt này"` và `"Lũy kế"` nếu nội dung gây trùng lặp hoặc gây hiểu nhầm (nhất là các đợt retry báo `0 máy`).
2. **CẤM chêm từ tiếng Anh lẻ tẻ:**
   - Thay `"Fail"` -> dùng `"Lỗi"`.
   - Thay `"Success"` -> dùng `"Đã hoàn tất"`.
3. **Mẫu chuẩn hóa báo cáo farm / watchdog:**
   ```text
   [BÁO CÁO DỌN DẸP CACHE TIKTOK]
   • Đã hoàn tất: 125 máy

   🏢 【FARM KIBE - MÁY 1-80】
   • Đã hoàn tất: 72 máy (01, 02, ...)
   • Lỗi (3): 14, 52, 56
     - Máy 14: Timeout
     - Máy 52: cache row not found on storage screen
     - Máy 56: Timeout

   🏢 【FARM ADMIN - MÁY 201-280】
   • Đã hoàn tất: 53 máy (201, 202, ...)
   • Lỗi (5): 208, 213, 230, 231, 243
     - Máy 208: WIDGET_MISS
     ...
   ```
4. **Quy tắc Silent Watchdog:**
   - Nếu đợt quét retry không hoàn tất thêm được máy nào (`s_count == 0`), script BẮT BUỘC thoát im lặng (`return 0`, `stdout` rỗng), không in báo cáo "0 máy" lên Telegram.

5. **Quy chuẩn tách bạch: Lỗi nền tảng vs Lỗi script (Operator Invariant 2026-10-02):**
   - **Chỉ thị từ Sếp:** "Lỗi script phải phân loại khác lỗi nền tảng chứ" và "Báo cáo chuẩn hoá theo chưa".
   - **Bản chất nghiệp vụ:**
     + **Lỗi nền tảng (Platform Errors):** Do Google, TikTok, SMS Gateway hoặc Proxy/IP chặn (`phone_verify`, `account_creation_error`, captcha, risk checkpoint). Không phải do script hỏng, xử lý bằng xoay IP hoặc cooldown.
     + **Lỗi script / kỹ thuật (Script Errors):** Do automation hoặc tương tác UI (`failed_cleanup` do lệch màn hình, không tìm thấy nút, crash/exception, exit code bất thường). Đây là lỗi kỹ thuật nội bộ, cần báo động đỏ để sửa code ngay, CẤM gom chung vào lỗi nền tảng hoặc nuốt vào nhóm skip an toàn.
     + **Bỏ qua an toàn (Safe Skip):** Máy bận, đã đủ trần 5 acc/máy chưa có acc lên GPM để gỡ (`skip_safe`, `skip_device_locked`).
   - **Cấu trúc mẫu báo cáo chuẩn hóa:**
     ```text
     [BÁO CÁO CHUỖI SAU CA TRƯA] [LANE GMAIL]
     - Thời gian: 15:15 -> 15:33 (18 phút)

     - Phase 1 (Reg Gmail - Code 0):
       • Đã hoàn tất: 7 máy
       • Bỏ qua an toàn: 3 máy (đầy slot)
       • Lỗi nền tảng (5): phone_verify: 5
       • Lỗi script: 0
     ```
