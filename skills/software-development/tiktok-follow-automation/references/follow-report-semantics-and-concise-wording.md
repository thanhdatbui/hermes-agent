# Follow report semantics and concise operator wording

## Trigger
Use when a follow-session report shows `Success (0)` and the operator asks whether any machine actually ran, was released, or caused an IP lock.

## Interpretation
`Success (0 máy)` means zero completed successful cross-follows without release. It does **not** prove zero attempts or zero follows executed:
- `Follow chéo (X lượt follow)`: Tổng số lượt follow tích lũy được trong phiên (ví dụ 14 lượt).
- `Thành công (0 máy)`: Không có máy nào hoàn tất phiên mà giữ sạch cờ — mọi máy đều dứt điểm bằng `FOLLOW_FAILED` (bị nhả ở lượt cuối).
- `Nhả follow` / `Nhả liền`: Machines that attempted and were released before a successful count was recorded, hoặc follow được một số lượt (ví dụ M1 được 2 lượt, M18 được 12 lượt) rồi bị nhả ở lượt kế tiếp và rơi vào diện `Nhả follow`.
- `Bỏ qua`: Safe skips such as cooldown, organic rest, eligibility, or circuit-breaker protection (`Khóa IP do máy cùng IP nhả`).
- `Khóa IP`: Proxy/IP circuit-breaker events and protected machines.

Do not collapse attempted, successful, released, skipped, and protected into one number. If the report lacks an explicit attempt count, say that the attempt count is not directly shown rather than inventing it.

## Compact Telegram Circuit Breaker & Released Formatting (User Correction)
### 1. Cầu Dao Tự Ngắt IP (Ultra-Concise 1 Line)
Operator yêu cầu khóa IP chỉ ghi số lượng kèm máy partner được cứu, tuyệt đối KHÔNG liệt kê danh sách cổng rườm rà:
- Có máy partner được cứu:
  ```text
  ⚡ Cầu dao tự ngắt IP (X proxy đã khóa): Khóa cứu Y máy (M78, M75, M8)
  ```
- Không có máy partner cần cứu:
  ```text
  ⚡ Cầu dao tự ngắt IP (X proxy đã khóa)
  ```

### 2. Định Dạng Máy Nhả Follow Kèm Số Lượt Thực Tế
Khi máy đạt được một số lượt follow thành công rồi mới bị nhả ở lượt cuối (`Nhả ở Hồi phục 1/2`, `Nhả ở Cấp Khỏe`), BẮT BUỘC ghi rõ số lượt đã đạt được cạnh tên máy:
```text
  + Nhả follow (25 máy | 100.0%):
    - Nhả liền (0 lượt | 92.0%): (M3, M4, M9, M16, ...)
    - Nhả ở Hồi phục 1 (1 - 4 lượt | 4.0%): (M1: 2 lượt)
    - Nhả ở Cấp Khỏe (10+ lượt | 4.0%): (M18: 12 lượt)
```
Tuyệt đối không in trơ trọi tên máy `(M1)` hay `(M18)` khiến operator hiểu lầm là máy bị nhả trắng 0 lượt như nhóm `Nhả liền`.

## Compact wording
Preferred shorthand: `Nhả → khóa IP`.

When a little more context is needed:
```text
Follow chéo: 0 lượt thành công
Nhả liền: X máy, 0 lượt thành công
Khóa IP: Y IP
```

## Operator Triage: "Sao report không báo cáo phiên follow?" (Tri-Channel & Forum Topic Pitfall)
Khi operator phản ánh "sao report không báo cáo phiên follow" hoặc "ca trưa không chạy follow à":
1. **Kiểm tra kênh tiếp nhận (Tri-Channel Split):**
   - Báo cáo chính stdout của cron watchdog gửi về `Tiktok Luot Nuoi Acc` (`-5377611430`) **đã bị cắt bỏ hoàn toàn mục Follow chéo** để gửi riêng về nhóm `Tiktok Follow` (`-5127276494`).
   - Nếu operator chỉ xem nhóm Luot Nuoi Acc, họ sẽ thấy hoàn toàn không có dòng nào về follow.
2. **Kiểm tra Forum Topics (General Topic Blackhole):**
   - Nhóm `Tiktok Follow` (`-5127276494`) bật chế độ diễn đàn/topic (`has_topics_enabled: true`).
   - Nếu lệnh dispatch `sendMessage` gửi thiếu `message_thread_id`, tin nhắn báo cáo follow rơi vào topic `General` thay vì topic làm việc của phiên, khiến operator không thấy thông báo.
3. **Phân biệt "Không chạy" với "Dừng an toàn / Nhả liền tại lượt 0":**
   - Ca trưa (Row 4) phần lớn là nick non (Rookie).
   - ~33% nghỉ Dưỡng sinh, proxy bẩn bị Cầu dao IP 48h chặn trước cửa app (`CIRCUIT_BREAKER_SKIPPED`), các nick được vào cày bấm anchor thì bị TikTok nhả ngay tức thì (`FOLLOW_FAILED` sau swipe).
   - Cơ chế Fail-Closed lập tức ngắt phiên tại lượt 0 để bảo vệ nick khỏi bị cấm tính năng vĩnh viễn ➔ Thống kê ghi nhận 0 lượt thành công nhưng toàn bộ hệ thống đã kích hoạt bảo vệ 100%.

## Answer style
Answer the operator's direct question first, in Vietnamese, with no speculative theory. Explain only the distinction needed to prevent the common misread that `Success (0)` equals “no machine ran.”
