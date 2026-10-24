# Phân Định Root Cause: Account Switcher Anchor Tap Failure vs Mapping Drift (Lệch Nick Thực Tế vs Excel)

**Ngày ghi nhận:** 11/10/2026  
**Ngữ cảnh:** Cảnh báo `[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found`.

---

## 1. Tránh Bẫy Suy Diễn "Lỗi Code / Lỗi Tọa Độ" (Anti-Assumption Pitfall)
- **Sai lầm phổ biến:** Khi thấy `ACCOUNT_MISSING`, agent thường vội vàng cho rằng:
  - Menu Switcher không mở được do tọa độ tap lệch.
  - Resource ID của anchor bị đổi (ví dụ `t_3` trên TikTok v47.x).
  - Vội vàng đề xuất sửa code `account_switcher.py` hoặc nới ratio tọa độ.
- **Thực tế hiện trường:** Trong nhiều trường hợp, **Menu Switcher ĐÃ MỞ THÀNH CÔNG** (như trong ảnh `soft-reboot-account_switcher-before.png`), nhưng tài khoản mong đợi (theo file Excel `taikhoan_run_safe.xlsx` hoặc DB) **KHÔNG HỀ TỒN TẠI TRÊN MÁY**.
  - Ví dụ: Excel chỉ định Tik 1 chạy `muyduyen4589`, nhưng thực tế trên máy ở vị trí Tik 1 lại đang đăng nhập nick `samnga2403`.
  - Script vuốt 3 lần qua danh sách không thấy `muyduyen4589` nên văng `ACCOUNT_MISSING`.

---

## 2. Quy Trình Điều Tra 2 Bước Bắt Buộc (OCR Switcher Trực Tiếp)

Trước khi kết luận lỗi anchor hay văng nick:
1. **Trích xuất ảnh chụp trạng thái Switcher:**
   - Kiểm tra ảnh `soft-reboot-account_switcher-before.png` hoặc `account-switcher-profile.png` trong thư mục run.
2. **Chạy OCR đọc danh sách nick thực tế:**
   - Dùng WinRT OCR hoặc inspect ảnh để lấy toàn bộ danh sách username đang nằm trong Bottom Sheet Switcher.
   - **Đối soát với DB/Excel:**
     - Nếu trong danh sách **CÓ** nick mục tiêu nhưng script không chọn được -> Lỗi selector/matching.
     - Nếu trong danh sách **HOÀN TOÀN KHÔNG CÓ** nick mục tiêu, nhưng có một nick lạ (như `samnga2403`) -> **MAPPING DRIFT (Lệch dữ liệu mapping máy)**, không phải lỗi code hay văng acc.
     - Nếu màn hình là trang Profile cá nhân, menu chưa mở -> Mới là lỗi anchor tap (`account-switcher-not-open`).

---

## 3. Kỷ Luật Phản Hồi User & Chống Bẫy Evidence First Gate
- **CẤM trả lời văn bản suông dài dòng, triết lý hoặc đưa ra giả định code khi chưa đối soát OCR danh sách nick.**
- **Bẫy Gate Hook:** Nếu Agent đưa ra kết luận hoặc kết thúc lượt mà không đính kèm thẻ `MEDIA:<path>` đã được verify, hook an toàn sẽ ngắt lời và đè thông báo lỗi gate (`[FAIL-CLOSED VIOLATION]` / `[UNVERIFIED MEDIA]`), làm User ức chế.
- **Quy tắc:** Mọi nhận định về nick sống/chết/lỗi BẮT BUỘC phải đi kèm OCR text thực tế + ảnh `MEDIA:` chứng minh danh sách nick trong Switcher.
