# Canonical Tooling, Zero Re-invent & Parasite Account Audit Discipline (2026-09-25)

## 1. Bối cảnh & Các Lỗi Vận Hành Bị Phạt Nặng
Trong các đợt vận hành Farm (đặc biệt là Preflight Reg bù phát hiện `MACHINE_FULL_8_ACCOUNTS`):
1. **Lỗi Re-invent (User Phạt: "Chứ có script sao mày còn đi viết nx"):**
   - Coordinator dispatch worker với lệnh viết lại script Python tạm từ đầu (`logout_<nick>.py`, `logout_m<N>.py`).
   - Subagent mất 10-15 tool calls để viết code, debug selector, thiếu xử lý biên (như atx-agent port 7912, cuộn switcher, popup logout), dẫn tới timeout (600s) làm đứt gãy phiên làm việc.
   - Farm đã có sẵn bộ công cụ chuẩn hóa được test kỹ lưỡng trong `D:/Taadaa/tools/`.
2. **Lỗi Kết Luận Ảo & Logout Nhầm Tài Sản (User Phạt: "Làm lol có chuyện nick trên máy mà k có trong data, tra lại cho tao"):**
   - Khi thấy một nick nằm trên thiết bị thật nhưng tìm nhanh trong `taikhoan_dat_v2_updated .xlsx` sheet Tài Khoản không thấy, Agent vội vàng gán nhãn *"Nick lạ không rõ nguồn gốc / Nick rác"* và thực hiện logout.
   - Thực tế: Đó là nick chính chủ được tạo từ Gmail/Hotmail của Farm, nhưng do cơ chế Purge Mail DIE tự động (`die_purge`) hoặc lỗi uncommitted tracking khi reg đêm nên chưa kịp ghi vào Excel. App TikTok trên máy vẫn lưu phiên sống 100%!

---

## 2. Danh Mục Script Canonical Bắt Buộc Dùng Sẵn (Zero Re-invent)

Trước khi thực hiện bất kỳ thao tác nào, Coordinator & Worker BẮT BUỘC kiểm tra và gọi trực tiếp các script sau:

### A. Gỡ / Logout Nick Ký Sinh (Nhả trần 8 Slot TikTok)
1. **Logout đơn lẻ theo máy:**
   ```bash
   python D:/Taadaa/tools/do_logout_account.py <machine_id> <username> <serial>
   ```
   - Cơ chế: Tự động dùng `atx-agent` (port 7912) dump UI, cuộn switcher tìm đúng `<username>`, chuyển nick, vào Menu -> Cài đặt & Quyền riêng tư -> Đăng xuất -> Xác nhận popup tại `(540, 1662)`.
   - Có tự động kiểm chứng và chụp ảnh nghiệm thu `D:/Taadaa/reports/m<machine_id>_verified_logout.png`.

2. **Logout hàng loạt đối soát danh sách:**
   ```bash
   python D:/Taadaa/tools/run_logout_all.py
   ```
   - Chạy hàng loạt các máy bị phát hiện nick ký sinh theo batch an toàn.

### B. Kiểm Tra & Giám Sát Thiết Bị
- **Trích xuất hiện trường O(1) qua ADB:**
  ```bash
  python D:/Taadaa/tools/inspect_machine.py <N>
  ```
- **Kiểm tra trạng thái lock per-device:**
  ```bash
  cat C:/Users/Kibe/.codex/device-locks/machine_<N>.lock.json
  ```

### C. Dữ Liệu & Đồng Bộ Workbook
- **Đồng bộ bảng tính an toàn sang runtime farm:**
  ```bash
  D:/Taadaa/python-envs/automation/Scripts/python.exe "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py"
  ```
- **Mua bổ sung Hotmail Zin OAuth2:**
  ```bash
  D:/Taadaa/python-envs/automation/Scripts/python.exe D:/Taadaa/tools/buy_hotmail.py --append-kibe <N> --target-machines <targets>
  ```

### D. Thẩm Định Chốt Phiên (Closeout Gate)
- **Reviewer độc lập chấm điểm:**
  ```bash
  D:/Taadaa/python-envs/automation/Scripts/python.exe D:/Taadaa/tools/closeout_gate.py --repo <repo> --base HEAD~1 --json-output
  ```

---

## 3. Quy Trình 4 Bước Tra Cứu Ngược Bắt Buộc (Reverse Audit Protocol)

**CẤM TUYỆT ĐỐI logout bất kỳ nick nào trên máy khi chưa hoàn tất 4 bước tra cứu:**

1. **Bước 1 — Tra cứu kho Backup Purge Mail (`backup_clean_v2_before_die_purge*`):**
   - Mở và tìm kiếm prefix username trong `D:/OneDrive/TaadaaData/kibe/backup_clean_v2_before_die_purge_*.xlsx` và `master_gmail_manager*.xlsx`.
   - Lưu ý: TikTok tự sinh username từ prefix email (ví dụ: `an.nhuan.work64541@gmail.com` -> TikTok tự sinh username `@annhubvqttr`).
2. **Bước 2 — Tra cứu lịch sử cấp phát mail theo STT Máy:**
   - Lọc xem máy đó trong quá khứ từng được cấp phát những email nào trong `gmail_clean_v2*.xlsx` và `social_reg_log.txt`. Email nào thừa ra so với các nick đã biết chính là chủ sở hữu của nick trên app!
3. **Bước 3 — Tra cứu các file Backup Workbook Data (`taikhoan_dat_v2_updated.bak*`):**
   - Quét các bản backup của `taikhoan_dat_v2_updated` xem dòng slot đó trong quá khứ đã từng có dữ liệu chưa, hay bị ghi đè nhầm ở máy khác (như Máy 61 và 76 bị ghi nhầm sang Máy 28 và 36).
4. **Bước 4 — Phân loại & Quyết định:**
   - **Nick chính chủ bị sót tracking / Mail bị purge:** Lấy thông tin (Gmail, Pass, 2FA, DOB) từ file backup để **Backfill vào ô trống của máy trên Excel**. TUYỆT ĐỐI CẤM logout!
   - **Nick ký sinh thực sự từ máy khác:** Đã đối soát xác minh nick chính chủ ở máy gốc an toàn -> mới tiến hành logout trên máy hiện tại theo canonical tool `do_logout_account.py`.

---

## 4. Quy Tắc Dispatch Worker Cho Tác Vụ Thiết Bị (Action Plan)
1. **Rule #1:** CẤM dispatch goal dạng "viết script để logout". BẮT BUỘC dispatch goal dạng: "Gọi `python D:/Taadaa/tools/do_logout_account.py <M> <user> <serial>` và nghiệm thu ảnh".
2. **Rule #2:** Budget tối đa cho worker gọi script có sẵn là <= 3 tool calls, hoàn thành dưới 2 phút.
3. **Rule #3:** Luôn bọc trong Device Lock (`acquire_device_lock`) khi tác động lên thiết bị live.
