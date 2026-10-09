# Kiến trúc Dữ liệu Farm & Quy tắc Phân tách Sổ cái (Cross-Farm Data Architecture)

## 1. Phán quyết Kiến trúc từ Sol (Lead AI Architect)
> **"Gộp logic để đọc — tuyệt đối KHÔNG gộp vật lý để vận hành."**

Khi mở rộng farm từ 1 cụm (80 máy) sang nhiều cụm (160 máy: Kibe máy 1-80, Admin máy 201-280):
- **Tuyệt đối KHÔNG gộp các file Excel vận hành (Operational Workbooks):**
  - Sổ cái credentials: `taikhoan_dat_v2_updated .xlsx`
  - Các ca/slot chạy: `Tik1.xlsx` -> `Tik8.xlsx`
  - File an toàn cục bộ: `kibe/taikhoan_run_safe.xlsx` và `admin/taikhoan_run_safe.xlsx`
  - *Lý do:* Thảm họa file lock (race condition), OneDrive sync conflict tạo file rác, single point of failure (1 file lỗi là sập cả 160 máy), mở rộng blast radius lộ credential.
- **Tạo View gộp Read-Only phục vụ tương tác chéo (Cross-Farm Target Pool):**
  - File: `D:/OneDrive/TaadaaData/taikhoan_run_safe_combined.xlsx`
  - Được sinh tự động bởi script `D:/Taadaa/tools/sync_combined_safe_workbook.py` (hook tự động sau khi sync tài khoản).
  - Chỉ chứa cột an toàn (`May`, `Device ID`, `ID`, `Video Đã Đăng`), loại trừ trùng lặp, chỉ đọc.

## 2. Hard Gate Anchor Mode 2 (Kibe-Only Anchor)
Trong module Follow chéo (`follow_engine.py`):
- **Anchor Mode 2 (Nick mồi để đi follow follower):** BẮT BUỘC chỉ được lấy nick của dàn Kibe:
  `1 <= machine <= 80` và `video_count >= 10` (Row 1 hoặc Row 2).
- **Loại trừ tuyệt đối nick cụm Admin (`machine >= 201`) làm Anchor:** Dàn Admin mới, graph chưa đủ dày; nick Admin chỉ đóng vai trò là target được follow trong pool 930 UIDs.
- **Fail-closed:** Nếu `machine` là None hoặc không parse được `int`, gán sentinel 999 (loại khỏi anchor).

## 3. Quy tắc Creator Lifecycle & Ngày Dưỡng Sinh (Organic Rest)
- **Định nghĩa chuẩn Dưỡng Sinh:**
  - **Dưỡng sinh = 0 Follow (nghỉ tương tác ngoại vi, cào kết bạn)**.
  - **VẪN CHO ĐĂNG VIDEO BÌNH THƯỜNG:** Người dùng thật mở app post video rồi lướt feed là hành vi Creator lành mạnh được TikTok khuyến khích.
- **Tối ưu tốc độ tích lũy 10 video:**
  - Nếu cấm upload ở ngày dưỡng sinh: Nick chạy so-le chẵn/lẻ chỉ tích lũy được ~2.3 video/tuần -> mất **~30 ngày** mới đủ 10 video để tốt nghiệp đi follow.
  - Khi cho phép upload trong ngày dưỡng sinh: Nick đăng đều 3.5 video/tuần -> chỉ mất đúng **20 ngày** là tích đủ 10 video.
- **Telemetry Event:** Khi upload trong ngày dưỡng sinh, ghi log có cấu trúc:
  `child_ctx.logger.log(step="upload-hook", action="organic_rest_upload_permitted", result="permitted", machine=M, row=R)`
  và cắm cờ `child_ctx.config["_upload_in_organic_rest"] = True`.
