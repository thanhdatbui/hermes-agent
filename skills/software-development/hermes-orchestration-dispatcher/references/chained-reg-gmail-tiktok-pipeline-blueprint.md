# Architecture Blueprint: Chained Reg Gmail → Reg TikTok Pipeline

## Tổng Quan Kiến Trúc
Pipeline tự động hóa ban đêm: Chạy batch Reg Gmail -> Lấy danh sách Gmail mới chuyển tiếp sang Reg TikTok -> Dừng an toàn trước Ca 1 nuôi acc (06:00).

## 1. Timeline & Khung Giờ
- **01:30:** Khởi động Master Pipeline.
- **Phase 1 (Reg Gmail):** Chạy `gmail_reg_v10.py` / `run_all.ps1` trên các máy rảnh có VPN. Chỉ ghi nhận mail sẵn sàng khi đã vào Inbox.
- **Phase 2 (Bridge / Gate):** `_detect_clean.py` đọc `gmail_clean_v2.xlsx`, lọc danh sách Gmail mới chưa tạo TikTok và khớp nối với máy chưa đủ 6 acc.
- **Phase 3 (Reg TikTok):** Gọi `_run_all_targets.py` chạy trên số lượng máy tương ứng với số mail mới có sẵn.
- **04:45 (Drain Window):** Ngừng nhận máy mới, dành 15 phút cho các máy đang đợi OTP hoàn tất.
- **05:00 (Hard Deadline):** Ngắt toàn bộ tiến trình con quá hạn, kết thúc trước 05:00 để nhường máy cho Ca 1 nuôi acc (06:00).

## 2. Các Chốt Kỹ Thuật Bắt Buộc (Incorporated from Multi-Round Audit)
1. **VPN Preflight & Monitor trên thiết bị Android:**
   - Kế thừa `resolve_proxy_mapping_path()` từ `automation_core.preflight`.
   - Kiểm tra VPN trực tiếp qua ADB (`ip route` / `dumpsys connectivity`). Máy nào rớt VPN giữa chừng thì dừng riêng máy đó, không để TikTok reg qua direct IP.
2. **Single Instance Guard (PID Lockfile):**
   - Script tạo `.pipeline.lock` kiểm tra PID đang chạy để chống overlap cron.
3. **Data Integrity & File Naming:**
   - Giữ nguyên 100% tên file chuẩn đang dùng trên farm: `taikhoan_dat_v2_updated .xlsx` (có khoảng trắng).
   - Phase 2 chỉ lấy các Gmail có trạng thái hoàn tất rõ ràng, tránh lấy mail dở dang nếu Phase 1 bị ngắt giữa chừng.
4. **Không Cần Cleanup Riêng:**
   - Ca nuôi acc lúc 06:00 đã có sẵn preflight đóng app rác và chuẩn bị thiết bị.

## 3. Hermes Cron Setup
- **Job Name:** `farm-night-reg-chain-gmail-tiktok`
- **Schedule:** `30 1 * * *` (01:30 sáng hàng ngày)
- **Type:** `no_agent: true` (Script thuần, 0 token LLM)
- **Output:** Gửi đúng 1 tin nhắn tóm tắt kết quả (Số Gmail tạo được, số TikTok reg thành công, danh sách máy hoàn tất) về Telegram khi chuỗi kết thúc.
