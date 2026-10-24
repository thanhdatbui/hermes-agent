# Closed-Loop Inline Recovery & Continuous Auto-Fix Architecture (Taadaa Phone Farm)

> Thống nhất từ tư vấn kiến trúc của **Advisor Sol** và **Claude CLI Sonnet** (24/10/2026).
> Đáp ứng yêu cầu chuyển đổi hệ thống sang tự vận hành (Human-on-the-loop, Operator chỉ đọc Daily Digest).

---

## 1. INLINE RECOVERY TRONG CA CHẠY (CIRCUIT BREAKER PER-DEVICE)

- **Vấn đề gốc:** Trước đây các primitive phục hồi (`probe_device`, `recover_device`, `farm_idle_screen_and_app_healer.py`) chỉ chạy trước ca hoặc sau ca. Giữa ca gặp lỗi máy đơ hoặc app văng thì bị dồn toa và ngâm timeout.
- **Giải pháp Inline:** Chèn decorator/hook mỏng vào vòng lặp thao tác của từng thiết bị trong mọi runner flow (Nuôi acc, 2FA TikTok, Change Hotmail).
- **Ladder 3 bước tại chỗ (Cap = 3 lần/máy/ca):**
  1. *Lần 1:* ATX kill + Clear background popups / notification shade (< 3s).
  2. *Lần 2:* Force-stop app + Relaunch từ Home screen (< 8s).
  3. *Lần 3:* Soft reboot device / Preempt device lock (< 35s).
- **Xử lý vượt ngưỡng:** Quá 3 lần fail $\rightarrow$ Đánh dấu `QUARANTINE`, ngắt riêng máy đó ra khỏi batch. **Batch vẫn chạy tiếp bình thường trên các máy còn lại (Zero-crash batch).**

---

## 2. PHÂN LOẠI LỖI VẬT LÝ vs PHẦN MỀM (ZERO-TOUCH TRIAGE)

- **Lỗi vật lý (Hardware / USB / Power):**
  - Dấu hiệu: `adb devices` trả về `offline` hoặc biến mất hoàn toàn khỏi bus USB, sụt nguồn hub (nhiều máy chung hub rớt cùng lúc).
  - Hành động: **CẤM** gọi LLM suy luận hay retry vô hạn. Lập tức gắn nhãn `PHYSICAL_QUARANTINE`, ghi vào danh sách cắm lại dây của Daily Report.
- **Lỗi phần mềm / UI drift / Selector:**
  - Dấu hiệu: Máy vẫn online ADB nhưng app crash, kẹt XML, hoặc selector không tìm thấy phần tử sau 3 lần probe.
  - Hành động: Đóng gói Incident Envelope và chuyển sang Pipeline Sửa Code Tự Động.

---

## 3. CONTINUOUS AUTO-FIX SCRIPT CHO MỌI CRON JOB

Áp dụng đồng bộ cho **tất cả** cron job vận hành (Nuôi acc, Change Info Hotmail, Add 2FA TikTok, Avatar, Bio, Rename, Upload...):

1. **Incident Envelope O(1):**
   - Đóng gói qua `sol_payload_guard.py`:
     - File lỗi + dòng lỗi duy nhất (`grep -c == 1`).
     - Raw UI XML dump + screencap hiện trường.
     - Stack trace và failing input.
     - Lệnh test tái hiện (focused test).
   - Ghi vào hàng đợi file-based: `guardgate/sol_repair_queue.jsonl`.
2. **Autonomous Dispatch & Closeout Loop:**
   - Watcher nền đọc queue $\rightarrow$ Gọi `dispatch_worker.py` (Tier 1 Sol Web free $\rightarrow$ Tier 2 Agy CLI $\rightarrow$ Tier 3 Haiku).
   - Ngân sách sửa: Bắt buộc $\le 30$ dòng diff, $\le 2$ files.
   - **Giữ nguyên 100% các Gate hiện có (Không bypass, chỉ tự động hóa trigger):**
     1. Chạy focused test offline/mocked (< 30s).
     2. Canary Gate (`canary_runner.py` trên tài khoản/máy thử nghiệm).
     3. Closeout Gate (`closeout_gate.py`, Reviewer chấm $\ge 85$ điểm).
     4. Done Gate (`done_gate.py` kiểm tra canary receipt).
   - Tự động commit `[auto-heal]` và merge. Cron job kế tiếp tự chạy trên code mới.
   - Nếu fail 3 lần liên tiếp: Đóng băng file đó, ném vào mục "Cần Operator Quyết Định" của Daily Digest.

---

## 4. DAILY EXECUTIVE DIGEST (ĐỌC 30 GIÂY)

Script tổng hợp chạy 23h30 hàng ngày, thuần túy Read-Only (rủi ro bằng 0), đọc ledger và gửi Telegram:
- **Tổng quan sức khỏe:** Số máy online / offline / tổng lượt tự phục hồi inline thành công.
- **Script đã tự sửa:** Commit SHA + Tên cron + Link bằng chứng Canary.
- **Máy cần cắm lại dây:** Danh sách máy mất ADB/USB vật lý.
- **Case cần quyết định nghiệp vụ:** Rủi ro tài sản hoặc checkpoint 3-strike.
