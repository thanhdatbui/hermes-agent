# Quy Chuẩn Nuôi 6 Acc/Máy, Vòng Đời 75 Ngày & Factory Reset Batch

## 1. Cấu Trúc Bố Cục 6 Dòng / Máy (480 dòng toàn farm 80 máy)
- Master workbook: `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`
  - Slot 1: `(m-1)*6 + 1` ➔ `Tik1.xlsx` (Ca 1 - Ngày Chẵn)
  - Slot 2: `(m-1)*6 + 2` ➔ `Tik2.xlsx` (Ca 2 - Ngày Chẵn)
  - Slot 3: `(m-1)*6 + 3` ➔ `tik3.xlsx` (Ca 3 - Ngày Chẵn)
  - Slot 4: `(m-1)*6 + 4` ➔ `Tik4.xlsx` (Ca 1 - Ngày Lẻ)
  - Slot 5: `(m-1)*6 + 5` ➔ `Tik5.xlsx` (Ca 2 - Ngày Lẻ)
  - Slot 6: `(m-1)*6 + 6` ➔ `Tik6.xlsx` (Ca 3 - Ngày Lẻ)

## 2. Chu Kỳ Vận Hành 75 Ngày (1k Follow / Mẻ)
- **14 ngày đầu (Warmup):**
  - Lướt feed For You 10-15 phút.
  - Tương tác tự nhiên: Like 2-4 video, follow 1-2 creator lớn/phiên.
  - Đăng video giãn cách 2 ngày/lần $\rightarrow$ Đạt mốc $\ge 5$ video để mở Video Gate.
  - Chưa bật follow chéo nội bộ.
- **Ngày 15 – 70 (Tăng Tốc):**
  - Đăng video 2 ngày/lần (tổng 30-40 video).
  - Bật follow chéo nội bộ (25-30 lượt/ngày hoạt động/acc).
  - Với farm 960 acc (hoặc 480 acc), bể tài khoản tự cung cấp đủ lượng follow chéo để đạt mốc 1,000 follow.
- **Ngày 71 – 75 (Xuất Xưởng & Làm Sạch):**
  - Kích hoạt 2FA dạng Secret Key (Google Authenticator) qua `tiktok-add-bao-mat-f2a`.
  - Xuất toàn bộ dữ liệu ra file Excel bàn giao.
  - Factory Reset máy về mặc định (hoặc reset sâu bằng script đổi toàn bộ Android ID, GSF, SSAID, Keystore) để tạo môi trường sạch 100% cho lô tiếp theo.
