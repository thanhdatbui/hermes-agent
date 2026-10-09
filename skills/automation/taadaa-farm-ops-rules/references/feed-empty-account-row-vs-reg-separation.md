# Feed Empty Account Row vs Reg Separation Policy

## Triệu chứng & Chữ ký
- Signature: `script-blocker:account row <N> is empty (no username) for machine <device>, skipping`
- Phát sinh khi: Runner nuôi feed (`tiktok-luot nuoi acc`) đọc workbook (`taikhoan_run_safe.xlsx`) theo row_index (1..8) nhưng ô username trống.

## Nguyên tắc cốt lõi (Invariant)
1. **Không inline auto-reg:** Ca nuôi feed (`feed_session`) tuyệt đối KHÔNG tự động kích hoạt flow đăng ký (`Tiktok_Reg`) khi phát hiện row trống.
   - Lý do: Flow reg can thiệp sâu vào device lock, thay đổi proxy/IP, có nguy cơ timeout làm treo tiến trình batch feed (3000s).
   - Hành vi đúng: Runner phân loại thành `config_errors` và skip máy đó, giải phóng luồng để tiếp tục phục vụ các máy có tài khoản.
2. **Kênh tự động của Reg:**
   - Việc bổ sung và đăng ký tài khoản cho các máy thiếu acc được phân tách thành pipeline riêng biệt, chạy qua cron job ban đêm: `night-chain-reg-pipeline` (01:00 AM) hoặc batch reg có chủ đích qua launcher `D:/Taadaa/Tiktok_Reg/_run_all_targets.py`.
3. **Audit nhanh trước khi trả lời:**
   - Kiểm tra `_detect_clean.py` tại `D:/Taadaa/Tiktok_Reg/` để xác nhận inventory các máy thiếu acc và nguồn mail đã sẵn sàng hay chưa.
