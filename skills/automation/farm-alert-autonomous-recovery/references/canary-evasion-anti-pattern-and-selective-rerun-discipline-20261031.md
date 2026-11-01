# Invariant Không Né Tránh Canary & Chạy Lại Máy Lỗi Sau Farm Alert

## 1. Tránh Bẫy "Bỏ Qua Canary Giả Hiệu (--no-canary)"
- **Cấm Tuyệt Đối Viện Cớ Ca Nuôi Đang Chạy Để Né Canary / Trốn Việc:**
  - Không tự ý dùng `--no-canary` với lý do "bảo vệ ca nuôi farm chiều" rồi báo xong để né tránh kiểm tra máy thật.
  - Khi máy đang dính device-lock do ca nuôi chính thức (`project=tiktok-luot nuoi acc` / `queued_v2`), đây là xung đột tiến trình hợp lệ nhưng **không được coi là lý do để trốn chạy lại các máy lỗi**.
  - **Hành vi bắt buộc:** Phải đồng bộ code vá sang toàn bộ cụm (Kibe & Admin), sau đó theo dõi phiên hoặc kích hoạt watchdog/selective re-run chính xác trên các máy bị lỗi ngay khi điều kiện cho phép.

## 2. Quy Trình Rerun Đúng Máy Lỗi (Selective Re-run)
- Khi Farm Alert báo danh sách máy lỗi (ví dụ M44, M221, M245, M271):
  1. **Vá Code & Kiểm Thử Offline:** Vá logic trong `state_machine.py` hoặc `multi_machine_feed_session.py`, biên dịch `py_compile` pass.
  2. **Đồng Bộ Lập Tức Sang Admin Remote:** Kiểm tra SHA256 khớp tuyệt đối trên cả 2 cụm (`admin_ssh.py`).
  3. **Khắc Phục Lỗi Gap Numbering Ở Thư Mục Video:** Nếu lỗi `video_not_rendered` do khuyết số (ví dụ có 1..11 rồi nhảy sang 27..61), kiểm tra thư mục video gốc `D:\video goc` và thư mục render `D:\TIKTOK-videonuoinick`. Gate 5 bắt buộc dùng cơ chế auto-fallback `min(rem >= next_video)` để bốc video tiếp theo có sẵn, không được skip mù quáng làm tồn đọng acc.
  4. **Theo Dõi Bằng Chứng Máy Thật:** Quan sát tiến trình live của ca hoặc chạy re-run đúng danh sách máy failed, đối soát log `upload_result.json` và summary thực tế trước khi nghiệm thu.
