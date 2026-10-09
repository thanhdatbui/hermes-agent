# Feed Empty Account Row vs Auto-Reg Separation

## Triệu chứng & Chữ ký
- Signature: `script-blocker:account row <N> is empty (no username) for machine <device>, skipping`
- Nơi phát sinh: `python_runner/core/feed_session_workbook.py:354`
- Nguyên nhân: Trong ca nuôi feed ở Row thứ `N` (1..8), ô username trong `taikhoan_run_safe.xlsx` để trống (`expected_username is None`).

## Nguyên tắc cốt lõi & Quy trình
1. **Không inline auto-reg:**
   - Flow nuôi feed (`feed_session`) tuyệt đối KHÔNG tự động nhảy sang reg tài khoản khi thấy slot trống.
   - Tránh tranh chấp device lock, tránh làm lệch cấu hình mạng/proxy, và không làm treo timeout ca nuôi chung của fleet (3000s).
   - Hành vi đúng: Runner phân loại thành `config_errors` và skip an toàn máy đó.
2. **Kênh Reg tự động:**
   - Việc bổ sung acc trống được thực hiện qua batch job độc lập ban đêm: cron job `night-chain-reg-pipeline` (01:00 AM) chạy chuỗi Reg Gmail -> Reg TikTok -> Bật 2FA.
3. **Audit nhanh khi nhận alert:**
   - Chạy `python _detect_clean.py` tại `D:/Taadaa/Tiktok_Reg/` để xác nhận danh sách target máy đang thiếu và sẵn sàng cho đợt reg.
