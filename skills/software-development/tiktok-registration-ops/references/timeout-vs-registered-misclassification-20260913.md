# TikTok Reg: Timeout vs Registered Misclassification & Master 8-Row Invariant (2026-09-13)

## 1. Sự Cố Misclassification "Tất cả email đã có TK TikTok"
- **Hiện tượng:** Khi chạy batch reg TikTok qua `_run_all_targets.py` / `social_reg_v1.py`, script quăng ngoại lệ:
  `RuntimeError: [07] Tat ca 1 email cua STT X da co TK TikTok`
  dù email vừa mới mua 100% chưa từng đăng ký TikTok.
- **Nguyên nhân cốt lõi:**
  1. Sau khi gõ email và bấm "Tiếp tục", mạng hoặc TikTok bị lag xoay loading quá 12s.
  2. Hàm `detect_after_continue()` timeout và trả về `"unknown"`.
  3. Hàm `fill_email_and_next()` rơi vào unknown fallback. Do không tìm thấy từ khóa OTP hoặc lỗi mạng rõ ràng trên UI, vòng lặp kết thúc.
  4. Đoạn cuối hàm hardcode câu quăng lỗi mặc định `raise RuntimeError(f"[07] Tat ca {len(candidates)} email cua STT {stt} da co TK TikTok")`.
- **Hệ quả:** Gây hiểu nhầm nghiêm trọng là hệ thống đã đăng ký tài khoản từ trước nhưng không ghi lại thông tin vào Excel.
- **Giải pháp chuẩn:**
  1. Thêm cờ `had_timeout_error = True` khi gặp timeout/unknown.
  2. Báo lỗi chính xác: `[07] Khong the xac dinh trang thai email cho STT X do timeout/mang cham khi bam Tiep tuc`.
  3. Cho phép hệ thống hoặc runner tự retry khi mạng ổn định (bằng chứng: cùng mail đó sang đợt sau 01:22 mạng nhanh đã đăng ký thành công 100%).

---

## 2. Invariant: Master Sheet Bắt Buộc Đủ 8 Hàng Vật Lý / Máy (80 Máy = 640 Hàng)
- **Cấu trúc:** Master sheet `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` (sheet `Tài Khoản`) quản lý 80 máy, mỗi máy nuôi tối đa 8 accounts (Row 1..8).
- **Pitfall:** Nếu máy chỉ có 6 hàng (như từng xảy ra với M76..M79), khi chạy reg bù cho Ca 0h (Row 7) hoặc Ca 0h chẵn (Row 8), hàm `apply_results(row=7)` sẽ không tìm thấy slot thứ 7 để ghi thông tin credential vào, khiến tài khoản reg thành công bị bỏ sót không sync sang `taikhoan_run_safe.xlsx`.
- **Quy tắc:**
  1. Luôn bảo đảm đủ 8 hàng vật lý cho mỗi máy.
  2. Sau khi ghi kết quả vào master sheet, BẮT BUỘC gọi script:
     `TAADAA_ALLOW_OVERWRITE_TOKEN="taadaa-writer-3c47f89f35e44795a79267e09fbcc72d" python "D:\Taadaa\tiktok-luot nuoi acc\scripts\sync-safe-workbook.py" --source "D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx" --output "D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx"`
