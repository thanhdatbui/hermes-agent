# Đối Soát Follow Watchdog Web vs Script & Triage Bẫy Anchor Module 2

## 1. Hiện Tượng (Symptoms) Trong Báo Cáo Follow Session Watchdog
Trong bản tin báo cáo Telegram từ `tiktok-follow-session-watchdog`:
```text
📊 [TIKTOK FOLLOW] Ca 1 - Phiên 2/2 (Sáng) hoàn tất (Pool {1, 2, 7})
• Follow chéo (N lượt follow) [Module 2 (Anchor): ... | Module 1 (Bù): ...]:
  + Đối soát TikTok Web (+X Following thật | Lệch ±Y so với script báo Z):
    - M37 [Tik 1] (@ngc.trinh6472) : script 0 lượt - web 11 lượt - lệch (+11)
    - M39 [Tik 1] (@thanh.huyn4934) : script 11 lượt - web 14 lượt - lệch (+3)
    - M40 [Tik 1] (@charakrh768)   : script 3 lượt - web 0 lượt - lệch (-3)
  + Nhả follow (N máy | 100.0%):
    - Nhả liền (11 máy | 0 lượt): (M6, M11, M12, M20, M31, M44, M49, M55, M59, M76, M80)
    - Nhả ở Hồi phục 1 (1 máy | 1 - 4 lượt): (M40: 3 lượt)
  + Lỗi script/xác minh (2): follow-timeout (1: M37); Lệch layout nút Follow (1: M39)
  + Bỏ qua: Chưa đủ điều kiện (under-6-videos)
```

---

## 2. Bản Chất Kỹ Thuật Từng Dạng Lệch Đối Soát

### A. Lệch Dương Cực Lớn: Script Báo 0 Nhưng Web Tăng +N Lượt (Ví dụ: M37 lệch +11)
* **Nguyên nhân gốc rễ:** 
  1. Script thực thi (`follow_runner`) đã bấm follow thành công đầy đủ N nick và ghi nhận vào state (`follow_state_<M>_row_<R>.json` với `budget_used = N`).
  2. Tuy nhiên, ở cuối phiên (sau khi đã follow xong), tiến trình bị nghẽn mạng hoặc delay teardown chạm trần timeout 20 phút (`follow-timeout`).
  3. Tiến trình cha bắt `subprocess.TimeoutExpired` và ghi fallback khẩn cấp vào `follow_result.json` với:
     ```json
     {"status": "timeout", "reason": "follow-timeout", "followed_count": 0, "failed": 1}
     ```
  4. Watchdog khi đối soát với TikTok Web API thì thấy profile thật sự đã tăng +11 following $\rightarrow$ Báo lệch `script 0 - web 11 (+11)`.
* **Kết luận Triage:** Nick đã **follow thành công thật 100%**. Lỗi nằm ở cơ chế fallback ghi đè `followed_count: 0` khi chạm timeout sau khi đã chạy xong action.
* **Cách tra cứu O(1):** Đọc trực tiếp `D:/Taadaa/tiktok-follow/runs/state/follow_state_<M>_row_<R>.json`. Soi trường `followed` xem danh sách UID và timestamp ngày hôm đó để khẳng định số lượt thật.

### B. Lệch Âm: Script Báo Có Follow Nhưng Web Báo 0 (Ví dụ: M40 script 3 - web 0 lệch -3)
* **Nguyên nhân gốc rễ:** 
  1. Script bấm nút follow trên app TikTok thành công 3 lượt.
  2. Nhưng khi vuốt kiểm tra lại profile/sau phiên, TikTok kích hoạt cơ chế lọc ngầm (ghost/drop follow), không cộng dồn vào following công khai của nick.
  3. Script bắt được sự kiện này và ghi: `FOLLOW_FAILED: TikTok không nhận follow (profile vẫn chưa follow)`.
  4. TikTok Web API xác nhận 0 following mới $\rightarrow$ Nick bị nhả follow 100% ở đợt Hồi phục 1.

### C. Lệch Nhẹ & Lệch Layout Nút Follow (Ví dụ: M39 script 11 - web 14)
* **Nguyên nhân:**
  1. Script hoàn thành 10 lượt chéo + 1 lượt tự nhiên lúc lướt Feed = 11 lượt.
  2. Ở 1 nick kế tiếp, app TikTok đổi layout hoặc xuất hiện nút khác khiến selector không khớp tuyệt đối: `MANUAL_REVIEW: exact profile identity không khớp sau tap`. Script dừng an toàn (fail-safe) để chống bấm nhầm.
  3. Số lượt lệch (+3) trên Web là do TikTok đồng bộ trễ các lượt follow tự nhiên từ cữ feed trước đó.

---

## 3. Bản Chất Hiện Tượng "Nhả Liền" (0 Lượt Follow)
* **100% các máy bị "Nhả liền" (ví dụ: M6, M11, M12, M20, M31, M44, M49, M55, M59, M76, M80):**
  - Không phải lỗi crash script hay mất mạng.
  - Đây là cơ chế **Module 2 Anchor Test**: Trước khi cho nick đi follow chéo dàn nick chính, script bấm follow 1 nick anchor nội bộ farm để thử nghiệm.
  - Nếu vừa vuốt kiểm tra thấy follow không dính:
    `FOLLOW_FAILED: anchor @... bị nhả sau vuốt — dừng session`
  - Safety gate lập tức ngắt toàn bộ phiên follow với `followed_count = 0` để bảo vệ nick khỏi bị phạt nặng hơn.

---

## 4. Farm Admin 75 Máy Bị Bỏ Qua (Chưa Đủ Điều Kiện)
* **Nguyên nhân:** Toàn bộ nick trên cụm Admin là nick non mới tạo, chưa đạt trần $\ge 6$ video đăng tải.
* **Quy chuẩn:** Gate an toàn `under-6-videos-follow-disabled` tự động miễn nhiễm không cho chạy follow chéo. Đây là hành vi đúng thiết kế, không can thiệp.

---

## 5. Kỷ Luật Tra Cứu Hiện Trường Của Coordinator (Guard-Compliant)
- **CẤM:** Dùng `execute_code`, gọi `adb` trần không qua allowlist, hoặc viết script có `os.walk`, `glob(recursive=True)` để quét tìm file log.
- **CHUẨN O(1):**
  1. Trạng thái máy: `python D:/Taadaa/tools/inspect_machine.py <N>`.
  2. Kết quả máy cụ thể: `D:/Taadaa/runtime/kibe/live/<DATE>/<RUN>/machines/machine_<N>/<RUN>/follow_result.json`.
  3. Lịch sử follow & state: `D:/Taadaa/tiktok-follow/runs/state/follow_state_<N>_row_<R>.json`.
