---
name: farm-account-ground-truth-audit
description: "Kỷ luật đối soát thực tế tài khoản Farm (Gmail, TikTok), chống ảo giác CSDL/Excel và khóa cơ học cấm báo cáo hoàn thành sớm."
---
# Farm Account Ground Truth Audit & Premature Done Gate

Quy chuẩn vận hành áp dụng cho mọi thao tác tra cứu, cấp phát, nghiệm thu tài khoản Gmail / TikTok trên Taadaa Farm.

## 1. Bẫy Ảo Giác Từ CSDL / File Quản Lý (Database Hallucination Trap)
- **Hiện tượng:** Coordinator chỉ query SQLite (`farm_master.db`) hoặc file Excel (`gmail_clean_v2.xlsx`, `master_gmail_manager.xlsx`), thấy cột `twofa_secret != ''` thì phán bừa "Gmail đã bật 2FA", hoặc thấy không có trong bảng `gemini-web` thì phán "Chưa có gói Pro".
- **Hậu quả thực tế:**
  1. Cấp acc `dinhlan` bị User phát hiện đã có gói Google AI Pro 5 TB từ tháng 8/2026 (thuộc pool Antigravity).
  2. Cấp acc `nathan` bị bên bán báo lỗi chưa bật 2FA (do mã 2FA trong DB thực chất là của nick TikTok `yabsley1990` bị migrate nhầm sang cột `twofa_secret` của mailboxes).
- **Quy tắc cơ học O(1):**
  - CSDL chỉ là **Metadata gợi ý (Lookup Index)**, TUYỆT ĐỐI không được coi là Ground Truth bằng chứng cuối cùng.
  - Trước khi cấp Gmail cho bất kỳ tác vụ quan trọng / mua gói / giao dịch: **BẮT BUỘC khởi động profile GPM qua CDP, mở trực tiếp `one.google.com/storage` và `myaccount.google.com/signinoptions/two-step-verification`**. Chụp ảnh màn hình + chạy WinRT OCR kiểm chứng tận mắt quota (15 GB vs 5 TB) và trạng thái 2FA (Đã bật Authenticator thật hay chưa).

## 2. Bẫy Copy Chéo 2FA TikTok Sang Mailboxes (Cross-Copy Drift)
- Khi migrate từ Excel sang SQLite: Các tài khoản TikTok có bật 2FA dễ bị bốc nhầm Secret Key gán sang bảng `mailboxes` của Gmail/Hotmail liên kết.
- Với Hotmail: Không bao giờ dùng TOTP (chỉ dùng OAuth/Pass).
- Với Gmail: Nếu `mailboxes.twofa_secret == tiktok_accounts.twofa_secret`, 99% đó là mã của TikTok, Google Account thật chưa từng bật Authenticator.
- Phải phân định rạch ròi 2 Secret Key khác nhau khi bật Google 2FA thật trên S7/GPM.

## 3. Kỷ Luật Khóa Tuyên Bố "Hoàn Thành" (Anti-Premature Done Gate)
- **Triệu chứng:** Cứ xong một lệnh terminal hay update DB là agent hô hào "Xong 100% rồi bác", trong khi giao dịch thực tế ngoài đời (bên bán kích gói, User add MoMo, cancel subscription) vẫn đang dang dở.
- **Quy tắc phát ngôn bắt buộc:**
  - CẤM TUYỆT ĐỐI dùng từ "Xong rồi", "Hoàn thành 100%" khi phụ thuộc vào bên thứ ba / tác vụ thực tế chưa về đích.
  - Chỉ được báo: `PHÍA NỘI BỘ: READY` (Đã chuẩn bị xong dữ liệu / bật xong 2FA / túc trực) và `TIẾN ĐỘ THỰC TẾ: WAITING_EXTERNAL` (Đang đợi bên bán / đang theo dõi kết quả).

## References
- Chi tiết toàn bộ quy trình, case study và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.
