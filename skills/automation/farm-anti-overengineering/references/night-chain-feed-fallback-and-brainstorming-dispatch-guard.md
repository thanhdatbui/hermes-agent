# Night Chain Feed Fallback, Brainstorming Dispatch Guard & Closeout Staged Parity (Taadaa Phone Farm)

Đúc kết từ phiên vận hành ngày 07/09/2026: mở rộng trần 8 acc/máy, tích hợp fallback nuôi feed Row 7/8 vào chuỗi đêm 01:00 AM, và bài học về phân biệt thảo luận ý tưởng vs lệnh thực thi.

---

## 1. BẪY VỘI VÃ DISPATCH KHI USER ĐANG THẢO LUẬN Ý TƯỞNG (BRAINSTORMING DISPATCH GUARD)

### Hiện tượng & Sự cố
User đưa ra phản biện / ý tưởng thăm dò:
> *"K cần rườm rà v. Nếu v thêm 1 cron nuôi feed acc 7,8 vào buổi khuya. Và nới rộng tiktok reg lên cho reg tối đa 8 nick"*

Coordinator hiểu nhầm câu trao đổi ý tưởng thành mệnh lệnh thực thi, lập tức gọi `delegate_task` dispatch worker subagent đi sửa code `Tiktok_Reg`. Worker chạy ngâm 35 tool calls gần 1 tiếng đồng hồ trong khi user chưa hề chốt giải pháp. Khi subagent xong, user phản ứng bức xúc: `?????`.

### Quy tắc bất biến (Anti-Overengineering)
1. **Phân biệt rõ hai trạng thái giao tiếp:**
   - **Thảo luận / Brainstorming / Thăm dò:** Câu chứa các từ khóa giả định ("Nếu vậy...", "Hay là...", "Liệu có nên...", "Có bị ban không?", "Ý là...").
     -> **HÀNH ĐỘNG:** Chỉ phân tích ưu/nhược điểm, đánh giá tính khả thi, hỏi ý kiến xác nhận hoặc đề xuất hướng đi tối ưu. **CẤM TUYỆT ĐỐI dispatch subagent sửa code hay can thiệp git.**
   - **Mệnh lệnh thực thi (Execution Trigger):** User ra chỉ thị dứt khoát ("Làm đi", "Làm luôn", "Chốt phương án này", "Tiến hành đi").
     -> **HÀNH ĐỘNG:** Lúc này mới chính thức dispatch worker subagent hoặc thực thi.
2. **Kỷ luật turn giao tiếp khi trao đổi kiến trúc:**
   - Trả lời ngắn gọn: 1) Đánh giá rủi ro/khả thi, 2) Phương án đề xuất, 3) Câu hỏi xác nhận trước khi làm.

---

## 2. KIẾN TRÚC CHUỖI ĐÊM 01:00 AM (NIGHT CHAIN PIPELINE FALLBACK)

### Mô hình 3 Phase linh hoạt trong `D:/Taadaa/Tiktok_Reg/scripts/run_night_chain_pipeline.py`:
1. **Phase 1: Reg Gmail** (`run_all.ps1`).
2. **Phase 2: Linh hoạt Reg TikTok hoặc Nuôi Feed Row 7/8:**
   - Chạy `_run_all_targets.py`.
   - Nếu còn target: Thực hiện đăng ký tài khoản TikTok như bình thường.
   - Nếu **hết target** (`Total targets: 0` do toàn farm đã đủ 8 nick hoặc không còn mail pending):
     * Tính ngày theo múi giờ Hồ Chí Minh (`ZoneInfo("Asia/Ho_Chi_Minh")`).
     * **Ngày chẵn:** Chạy nuôi feed **Row 8**.
     * **Ngày lẻ:** Chạy nuôi feed **Row 7**.
     * Gọi launcher: `run-feed-session.ps1 -Row $row -Preset full -LocalRun -RecoveryTestSwipes 2 -MaxWorkers 40 -Run` (timeout 3600s kèm cơ chế `taskkill /T /F /PID` diệt sạch process-tree nếu timeout).
3. **Phase 3: Add 2FA TikTok LUÔN LUÔN CHẠY SAU PHASE 2:**
   - **User Rule (2026-09-07):** *"Phase 3 add 2fa sao bỏ. Nó nằm sau phase 2. Phase 2 là tiktok reg hoặc là tiktok nuôi chứ"*.
   - Kể cả Phase 2 chuyển sang nuôi feed thì Phase 3 vẫn phải chạy bình thường để rà soát bật 2FA cho các nick còn sót trên farm.

### Bóc tách báo cáo chi tiết cho ca nuôi feed (`parse_feed_details`):
- Trích xuất `run_manifest.json` từ marker `Artifacts:\s*([^\r\n]+)` trong output hoặc fallback tìm folder run mới nhất trong `.ai-runs`.
- **Cơ chế chống Stale Manifest Ingestion:** Fallback tìm thư mục trong `.ai-runs` BẮT BUỘC kiểm tra timestamp khởi tạo (`st_mtime >= feed_start_ts - 10`) để tránh bốc nhầm manifest của ca nuôi cũ khi phiên hiện tại bị abort/crash.
- Phân loại rõ ràng 3 nhóm máy trong `[BÁO CÁO CHUỖI ĐÊM]`:
  * `Success`: Các máy lướt feed thành công (`final_status in {"success", "degraded"}`).
  * `Chưa có acc`: Các máy chưa nạp nick ở slot 7/8 (`account row X is empty, skipping`).
  * `Fail`: Các máy gặp lỗi UI / thiết bị thật sự.

---

## 3. MỞ RỘNG SAFE WORKBOOK & FEED SESSION LÊN 8 SLOTS (ROW 1..8)

1. **Launcher `run-feed-session.ps1`:**
   - Tham số `$Row` mở rộng từ `[ValidateRange(1, 6)]` thành `[ValidateRange(1, 8)]`.
2. **Synchronizer `sync-safe-workbook.py`:**
   - Nâng cấp trần từ 6 lên 8 entries/máy (`while len(entries) < 8`, `entries[:8]`, `range(8)` cho `EXTRA_MACHINES`).
   - Sinh đúng **640 dòng** (80 máy x 8 slots) vào `taikhoan_run_safe.xlsx`.
3. **Bảo toàn tương thích ngược cho Ca ngày (Row 1..6):**
   - Runner `feed_session_workbook.py` đọc theo `row_index - 1`. Thứ tự 6 slot đầu giữ nguyên 100% (byte-identical), slot 7 và 8 chỉ append vào cuối.
   - Các máy chưa có nick ở slot 7/8 được runner tự động skip an toàn mà không gây crash hay chọn nhầm nick.

---

## 4. CẠM BẪY LỆCH STAGED DIFF KHI CHẠY CLOSEOUT_GATE.PY

### Nguyên nhân gây Review REJECT oan:
`closeout_gate.py` ưu tiên trích xuất staged diff (`git diff --cached`) nếu trong git index có bất kỳ file nào được staged.
- Nếu agent chạy `git add <file>` ở bước trước, sau đó phát hiện cần chỉnh sửa tiếp trong working tree nhưng **quên `git add` lại**.
- Khi chạy `closeout_gate.py`, tool bốc đúng diff staged cũ gửi lên OmniRoute.
- AI Reviewer nhìn thấy diff cũ chứa lỗi chưa sửa và tiếp tục trả về `VERDICT: REJECTED`.

### Quy tắc bắt buộc:
- Sau mọi chỉnh sửa trong working tree, BẮT BUỘC chạy `git add <file>` cập nhật lại git index.
- Kiểm tra `git diff --cached` bảo đảm khớp 100% các thay đổi mong muốn trước khi kích hoạt `closeout_gate.py`.
- Trong code Python bọc regex qua JSON/tool calls: Cẩn thận với chuỗi `r"Artifacts:\s*([^\r\n]+)"` tránh để escaping biến `\r` và `\n` thành literal carriage return / newline gây vỡ cú pháp.
