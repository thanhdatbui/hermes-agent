# GemPhoneFarm Follow Cadence & Dwell Time Analysis (2026-09-14)

Đối chiếu trực tiếp từ 3 file workflow GemPhoneFarm gốc của đối tác (cùng setup hạ tầng 8 nick/máy, 2 máy/1 proxy, Samsung S7):
1. `TIKTOK-Nuoi-Tai-Khoan-Goc_decrypted.json` (205 nodes)
2. `TIKTOK-FLOW-TÌM-KIẾM-Thành-đạt_decrypted.json` (389 nodes)
3. `TIKTIK-ĐĂNG-VIDEO-Đạt_Decrypted.gemphonefarm` (64 nodes)

## 1. Dữ liệu thực tế: Đăng video đều vẫn bị nhả follow nếu nhịp thao tác sai
- Đối soát 176 tài khoản dính án phạt nhả follow (`fail_streak >= 1`) với `taikhoan_run_safe.xlsx`:
  - 170 / 176 tài khoản (96.6%) **đã đăng trên 5 video**.
  - 44 tài khoản đã đăng **trên 20 video** (ví dụ Máy 11 Row 1: 23 video vẫn dính `fail_streak = 3`).
- **Kết luận:** Nhận định "chỉ cần đăng video đều là tự hết nhả follow" là không đầy đủ. Yếu tố quyết định là **nhịp độ tương tác (Cadence) và thời gian ngâm (Dwell Time)** khi đi follow.

## 2. Thông số nhịp độ GemPhoneFarm thực tế
- **Dwell Time ngâm Profile mục tiêu trước khi tap Follow:**
  - GemPhone delay từ **5.8s đến 12.5s** (`5812, 12549 ms`) sau khi mở Profile rồi mới chạm vào nút Follow.
  - Tuyệt đối cấm vừa mở Profile xong tap Follow ngay trong 1-2s (bị Risk Engine tính là bot cơ học).
- **Phản hồi sau khi tap Follow:**
  - Delay chờ server nhận: **1.8s đến 5.6s** (`1814, 5654 ms`).
- **Khoảng cách nghỉ giữa 2 lần Follow (Inter-follow delay):**
  - Node `rf10473`: nghỉ ngẫu nhiên từ **5.1s đến 29.5s** (`5142, 29521 ms`) trước khi chuyển sang tìm kiếm/follow người tiếp theo.
- **Cơ chế kiểm chứng (Verification):**
  - Tại Profile Anchor/Target đơn lẻ: Vuốt kéo reload (Pull-to-refresh từ y=115 xuống y=1650) để kiểm tra server state thật.
  - Trong danh sách list: Sử dụng Path B Verify (bấm vào username mở Profile con) để kiểm tra trạng thái nút từ server, không đứng kéo màn hình list.
