# Triage Lịch Đăng Video Phiên 1 & Phiên 2 và Đối Soát Ground Truth Đăng Video (2026-09-12)

## 1. Cơ Chế Đăng Video Mới (Case 152 — 4 Ca × 2 Phiên)
Từ 10/09/2026, hệ thống chuyển sang mô hình:
- **Phiên 1 (P1):** Sau khi lướt feed, máy tự động kiểm tra và đăng video ngay.
- **Phiên 2 (P2):**
  - Nếu P1 **đã đăng thành công** -> Kiểm tra `_ShiftUploadLedger` / `upload_result.json` và **Safe-Skip** ngay lập tức (`reason: already_uploaded_in_shift`). Tuyệt đối không đăng lặp lần 2.
  - Nếu P1 **chưa đăng hoặc đăng lỗi** -> P2 tự động **đăng bù**.
- **Cam kết an toàn tuyệt đối:** Tối đa đúng 1 video / account / ca.

## 2. Chu Kỳ Phân Bổ Ca & Row (Ngày Chẵn vs Ngày Lẻ)
- **Ngày Lẻ:**
  - Ca 1 (06:00): Row 1 (`Tik1.xlsx`)
  - Ca 2 (12:00): Row 3 (`Tik3.xlsx`)
  - Ca 3 (18:00): Row 5 (`Tik5.xlsx` — hiện chưa mở đăng video)
  - Ca 4 (00:00): Row 7 (`Tik7.xlsx`)
- **Ngày Chẵn:**
  - Ca 1 (06:00): Row 2 (`Tik2.xlsx`)
  - Ca 2 (12:00): Row 4 (`Tik4.xlsx`)
  - Ca 3 (18:00): Row 6 (`Tik6.xlsx` — hiện chưa mở đăng video)
  - Ca 4 (00:00): Row 8 (`Tik8.xlsx`)

## 3. Quy Trình Điều Tra O(1) Khi User Hỏi: "Phiên trước có đăng video chưa? Hay mới đăng đúng phiên này?"
Tránh quét đĩa diện rộng (`os.walk`, `glob` hàng chục nghìn file trong `D:/CodexRuntime` hay `.ai-runs` gây timeout >180s). Tra cứu theo 3 nguồn O(1):

1. **Báo cáo Feed Session Watchdog:**
   - Đọc trực tiếp các file summary trong `C:\Users\Kibe\AppData\Local\hermes\cron\output\1d62cb3562e0\`.
   - Tìm 2 file tổng kết của P1 và P2 trong ca hôm nay (file kích thước >500 bytes).
   - Đọc mục `Đăng Video (1/2)` và `Đăng Video (2/2)` để xem số lượng máy đăng thành công ở P1 và số máy bù ở P2.

2. **Kiểm tra `upload_result.json` của phiên vừa xong:**
   - Đường dẫn: `D:\Taadaa\runtime\kibe\live\<YYYY-MM-DD>\<run-folder>\machines\machine_<N>\<run-id>\upload_result.json`.
   - Các máy P1 đã đăng thành công sẽ có:
     `"status": "skipped", "reason": "already_uploaded_in_shift"`
   - Các máy đăng bù thành công ở P2 sẽ có:
     `"status": "success"`

3. **Đối soát Lũy kế Video qua Snapshot Bundles:**
   - So sánh `target_count` giữa snapshot đầu ngày (`D:\Taadaa\runtime\kibe\cron-state\snapshot_bundles\<YYYY-MM-DD>\gen_*\post-state.json`) và file hiện tại (`D:\Taadaa\runtime\kibe\cron-state\post_state.json`).
   - Hoặc tra cứu nhanh các backup snapshot giữa các ngày để chứng minh số video tăng đều đặn theo từng ngày chẵn/lẻ.
