# Quy Chuẩn Đối Soát Tỉ Lệ Sống/DIE & Điều Phối Reg Gmail Dual-Farm

**Ngày cập nhật:** 2026-10-12  
**Chỉ thị từ Operator:**
- "Tỉ lệ die đâu? R farm admin có chạy reg chưa"
- "Fix gọi luôn farm admin"

---

## 1. Kỷ Luật Báo Cáo Tỉ Lệ Reg Gmail (Bắt Buộc Kèm Tỉ Lệ Sống / DIE)
Khi Operator yêu cầu *"kiểm tra tỉ lệ reg Gmail"*, báo cáo **TUYỆT ĐỐI KHÔNG ĐƯỢC** chỉ đưa ra con số thành công ở khâu tạo nick ban đầu (Creation Rate). Bắt buộc phải chia làm 2 chỉ số rạch ròi:

### A. Tỉ lệ Tạo Thành Công (Creation Success Rate):
- **Bản chất:** Số máy tạo thành công / tổng số máy chạy trong batch.
- **Mức chuẩn:** Dao động **33% – 53%** (trung bình ~40.0% khi hệ thống ổn định trên dải proxy 4G S7 không gắn SIM).
- **Phân loại lỗi chuẩn:**
  * Lỗi nền tảng (Google): `phone_verify` (chiếm ~28%), `account_creation_error` (chiếm ~9%).
  * Lỗi script/hạ tầng: `failed_other`, ADB offline, rớt cáp USB (chiếm ~17%).

### B. Tỉ lệ Sinh Tồn Sau Ngâm (Post-Creation Survival Rate / Tỉ Lệ DIE):
- **Bản chất:** Đánh giá độ bền thực tế của tài khoản sau thời gian ngâm tĩnh trên S7 trước khi đưa lên GPMLogin PC.
- **Nguồn đối soát Canonical (Source of Truth):**
  * `D:/CodexRuntime/codex_gmail_debug-register-gmail/logs_parallel_*/results/*.success.json`: Tổng tài khoản đã tạo thành công theo từng batch.
  * `D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx`: Sổ cái tài khoản đang LIVE còn lưu trữ trên farm.
  * `D:/OneDrive/TaadaaData/kibe/gmail_die_tong.txt`: Danh sách tài khoản đã xác nhận DIE qua `checkmail.live` / Google checkpoint.
- **Quy luật sinh tồn theo chu kỳ:**
  * **Trong 48h – 72h đầu (Acc mới reg):** Tỉ lệ sống giữ **~100%** (0% DIE) nếu không bị ép thao tác hay login chéo IP.
  * **Sau $\ge 14$ ngày (Acc ngâm tĩnh trên S7):** Tỉ lệ sống duy trì ở mức **~53.1%**, tỉ lệ DIE do Google quét checkpoint là **~46.9%**.
  * Báo cáo phải đối soát theo tháng: Acc tháng mới reg (tháng 10) vs Acc tháng trước (tháng 9) để Operator thấy bức tranh toàn diện.

---

## 2. Kiến Trúc Điều Phối Reg Gmail Dual-Farm (Kibe & Admin)
- **Hiện trạng trước đây:**
  * Phase 1 (Reg Gmail): `post_noon_chain_watchdog.py` chỉ gọi cục bộ trên cụm Farm Kibe (Máy 1–80).
  * Phase 2 (Add 2FA TikTok): Đã gọi đồng thời cả Kibe (Máy 1–80) và Admin (Máy 201–280 qua SSH `admin-farm`).
- **Yêu cầu mở rộng gọi Farm Admin cho Phase 1:**
  * **Farm Admin:** Gồm 80 máy (201 đến 280), kết nối từ máy Kibe qua SSH host `admin-farm`.
  * **Workbook Admin:** Cấu hình proxy tại `D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx` và sổ cái tài khoản tại `D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx`.
  * **Cơ chế SSH chạy nền tương tự Phase 2:** Sử dụng PowerShell `EncodedCommand` qua `ssh -o ConnectTimeout=10 admin-farm` để thực thi launcher `run_all.ps1` hoặc `run_parallel.ps1` trên cụm Admin.
  * **Telemetry phân tách:** Báo cáo watchdog Telegram phải tách rõ:
    ```text
    - Phase 1 (Reg Gmail - Code 0):
      • Farm Kibe (Máy 1-80): Đã hoàn tất X máy | Lỗi Y
      • Farm Admin (Máy 201-280): Đã hoàn tất Z máy | Lỗi W
    ```

---

## 3. Kỷ Luật Subagent Dispatch: Guard Contract Cho Task Điều Tra (Investigate)
Khi Coordinator dispatch Worker làm nhiệm vụ đọc/kiểm tra/điều tra hiện trường từ xa:
1. **Bắt buộc có `FAIL_FAST:` trong prompt/context:**
   - Hook guard `INVESTIGATE_MISSING_FAIL_FAST` chặn đứng nếu thiếu chỉ thị dừng khẩn cấp.
   - Cú pháp chuẩn: `FAIL_FAST: Nếu trong <= 3 iterations đầu không thể kết nối hoặc không tìm thấy mục tiêu, PHẢI DỪNG NGAY (ABORT) và trả về báo cáo thất bại, cấm đốt hết budget.`
2. **Giới hạn ngân sách cứng (Budget Cap):**
   - Hook guard `INVESTIGATE_BUDGET_EXCEEDED` quy định task điều tra/đọc tối đa **<= 5 tool calls**. Không được đặt 6 hay 15 calls cho task thuần kiểm tra hiện trường.
