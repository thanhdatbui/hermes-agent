# TikTok On-Demand Registration & Auto Hotmail Provisioning (2026-09-12)

## 1. Cơ chế On-Demand thay thế Batch Reg dồn đêm
- **Vấn đề cũ:** Chạy dồn 80 máy reg TikTok vào ban đêm gây nghẽn mạng, nóng máy, quota đếm sai và lãng phí acc.
- **Giải pháp mới:** Chia nhỏ theo từng Ca nuôi. Trước Phiên 1 của mỗi Ca chạy Row $R$:
  `python D:/Taadaa/tools/ensure_row_accounts.py <R>`
- Máy nào có đủ nick ở Row đó thì bỏ qua trong 1s. Máy nào thiếu nick thì tự động mua mail và reg bù ngay trên máy đó trước khi phiên nuôi bắt đầu.

## 2. Điểm cốt tử khi đếm Quota tài khoản (`scripts/tiktok_target_eligibility.py`)
- **Lỗi kinh điển:** `load_registered_mailboxes` đếm tất cả các dòng của máy trong tracking workbook (`taikhoan_dat_v2_updated .xlsx`), kể cả dòng trống `ID is None`. Khiến máy có 8 dòng nhưng chỉ có 6 nick thật bị bỏ qua không bao giờ được reg thêm.
- **Quy tắc bất biến:** Chỉ tăng `machine_counts[m]` khi dòng có `tiktok_id` hợp lệ:
  ```python
  if tiktok_id and stt_idx is not None and stt_idx < len(row):
      raw_stt = row[stt_idx]
      if raw_stt is not None and str(raw_stt).strip():
          machine_counts[m] = machine_counts.get(m, 0) + 1
  ```

## 3. Tự động mua Mail Hotmail nạp vào Kibe (`buy_hotmail.py`)
- Hỗ trợ CLI:
  ```bash
  python D:/Taadaa/tools/buy_hotmail.py --append-kibe <N> --target-machines <M1,M2,...>
  ```
- Nạp thẳng vào `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` cho đúng các máy `1..80` theo chuẩn 11 cột.

## 4. Lọc Target Reg theo danh sách máy cụ thể (`_detect_clean.py`)
- Truyền danh sách qua tham số `target_stts` hoặc biến môi trường `TIKTOK_REG_TARGET_STTS="1,2,5"`.
- `select_pending_targets` sẽ bỏ qua các máy không nằm trong danh sách này.
