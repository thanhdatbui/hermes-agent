# Preflight MACHINE_FULL_8_ACCOUNTS Protocol & Coordinator Discipline

## 1. Bản chất sự cố
Khi tiến trình Preflight (`ensure_row_accounts.py <row>`) quét farm trước ca chạy và phát hiện một số máy thiếu tài khoản ở Row đó, nó tự động khởi tạo luồng reg bù. Tuy nhiên, khi vào thiết bị lại văng:
`RuntimeError: [04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok`
(Ẩn nút "Thêm tài khoản" do TikTok chạm trần 8 nick).

## 2. Quy trình phân loại & xử lý O(1)
Không được scan đĩa hay thử lại mù quáng. Kiểm tra trực tiếp file chụp Switcher `_03_dropdown_*.png` hoặc dump UI XML `fail_04_add_account_*.xml`:

1. **Nhánh 1: Lệch Excel / Displaced Account:**
   - Nick thực tế trên máy là nick chính chủ của máy đó (được reg từ trước và có file `tracking_result_stt<N>_*.json` khớp serial).
   - Do lỗi đồng bộ trước đây, nick bị ghi đè vào máy khác trên file Excel, để trống dòng Row của máy hiện tại.
   - **Xử lý:** Backfill lại tài khoản vào đúng Row của máy trên `taikhoan_dat_v2_updated .xlsx`, xóa ô duplicate ở máy bị ghi nhầm về `None`, và chạy `sync-safe-workbook.py`.

2. **Nhánh 2: Nick Ký Sinh (Parasite Account - Log chéo):**
   - Nick thứ 8 trên máy thực chất thuộc về máy khác (chính chủ máy khác).
   - **Xử lý:** Chờ máy rảnh (0 active lock trong `.codex/device-locks`), giành lock và chạy:
     `python D:/Taadaa/tools/do_logout_account.py <machine_id> <parasite_username> <serial>`
   - BẮT BUỘC chụp ảnh nghiệm thu Switcher sau khi logout (`CAPTURE-BEFORE-CLEANUP`) xác nhận:
     + Nick ký sinh đã biến mất.
     + Còn lại đúng 7 nick.
     + Nút *"Thêm tài khoản"* đã hiển thị trở lại.
   - Sau đó force-stop TikTok, đưa máy về Home an toàn.

## 3. Kỷ luật Coordinator chống hỏi thừa (Anti-Indecision)
- Khi nhận Farm Alert `[PREFLIGHT REG BÙ ROW N]`:
  - **CẤM TUYỆT ĐỐI** Coordinator hỏi user: *"Bạn muốn ưu tiên xử lý máy nào trước?"*, *"Làm cái nào trước?"*.
  - Hỏi như vậy vi phạm nguyên tắc Proactiveness, thể hiện sự do dự và sẽ bị user chấn chỉnh (`???`, `Xử lý đi`, `Thì làm nốt đi`).
  - Coordinator phải tự động phân tích O(1), xác định rõ máy nào cần Backfill Excel, máy nào cần Logout nick ký sinh, báo cáo ngắn gọn và chủ động dispatch worker xử lý trọn gói.
