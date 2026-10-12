# Gmail Farm Cohort Survival, DIE Verification & Admin Farm Scope Audit

**Ngày cập nhật:** 2026-10-12  
**Nguyên tắc vận hành & Audit hiện trường:**

## 1. Phương Pháp Tra Cứu & Đánh Giá Tỉ Lệ Sống / DIE Chuẩn (Cohort Survival vs Raw Reg)
- **Sai lầm phổ biến:** Chỉ báo cáo tỉ lệ reg ban đầu (`OK / Total`) mà quên đo lường tỉ lệ sống sau thời gian ngâm (`Soak Survival Rate`), hoặc kết luận tỉ lệ DIE vội vã trên các tài khoản mới reg trong ngày (< 24h).
- **Quy luật sinh tồn của Gmail farm:**
  - **Giai đoạn ngâm ban đầu (0 – 72 giờ):** Tỉ lệ giữ LIVE trên S7 thường đạt xấp xỉ 100% nếu tài khoản không bị ép thao tác nặng / đổi IP đột ngột. Báo cáo tỉ lệ DIE của các mẻ reg trong ngày luôn là 0% vì chưa tới chu kỳ quét tự nhiên của Google.
  - **Giai đoạn ngâm tĩnh chuẩn ($\ge 14$ ngày - Mature Cohort):** Google bắt đầu quét checkpoint / xác minh số điện thoại trên các tài khoản nghi vấn.
    * Tỉ lệ DIE tự nhiên thực tế dao động từ **40% – 47%**.
    * Tỉ lệ tài khoản sống sót bền vững đạt **~53%** để chuyển tiếp lên GPMLogin PC làm tài khoản nuôi dài hạn.
- **Phương pháp đối soát 3 nguồn (Triple-Source Audit):**
  1. **Canonical Reg Artifacts:** `D:/CodexRuntime/codex_gmail_debug-register-gmail/logs_parallel_*/results/*.success.json` (tổng số acc reg thành công thực tế).
  2. **Active Workbook (Live Primary):** `D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx` (chỉ chứa acc còn live, acc DIE bị dọn dẹp).
  3. **DIE Audit Trail:** `D:/OneDrive/TaadaaData/kibe/gmail_die_tong.txt` (lưu lại toàn bộ email DIE đã được xác nhận qua `checkmail.live` kèm máy và timestamp).
  4. **Daily Text Sync:** `D:/OneDrive/TaadaaData/kibe/gmail_live_tong.txt` (được cronjob đồng bộ định kỳ mỗi ngày lúc 08:00 từ `gmail_clean_v2.xlsx`).

## 2. Ranh Giới Phạm Vi Vận Hành (Scope Boundaries): Kibe vs Farm Admin
- **Hiện trạng luồng chuỗi sau ca trưa (`post_noon_chain_watchdog.py`):**
  - **Phase 1 (Reg Gmail):** CHỈ CHẠY CỤC BỘ TRÊN CỤM KIBE (Máy 1 – 80).
    * `run_gmail_batch()` chỉ gọi `D:/Taadaa/register gmail/run_all.ps1`.
    * Inventory `taikhoan_run_safe.xlsx` và cấu hình máy trong `gmail_reg_v10.py` chỉ ánh xạ 80 máy Kibe.
    * Launcher áp dụng giới hạn `maxMachines = 15` cho mỗi ca trưa để bảo toàn băng thông 4G MobiProxy.
    * **Farm Admin (Máy 201 – 280) CHƯA BAO GIỜ chạy Reg Gmail.**
  - **Phase 2 (TikTok 2FA):** Chạy đồng thời cả 2 cụm:
    * Cụm Kibe (Máy 1 – 80): Chạy local qua `run_batch_live_2fa.py`.
    * Cụm Admin (Máy 201 – 280): Chạy remote qua SSH `admin-farm` với `powershell -EncodedCommand`.
- **Kỷ luật trả lời truy vấn về Farm Admin:**
  - Khi User hỏi về tình trạng reg của Farm Admin, Coordinator phải rà soát mã nguồn launcher (`run_all.ps1`, `post_noon_chain_watchdog.py`) để xác nhận rõ ràng rằng Farm Admin chưa được tích hợp luồng reg Gmail, tránh trả lời mập mờ hoặc nhầm lẫn giữa Phase 1 (Reg Gmail) và Phase 2 (TikTok 2FA).
