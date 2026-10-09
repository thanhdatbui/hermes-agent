# Feed Session & Watchdog Preflight Pitfalls (Đối soát & Vận hành Farm)

## 1. Nhầm lẫn nhãn lỗi `blocked-vichanger-vpn` với việc cài ViChanger
- **Hiện tượng:** Log máy hoặc báo cáo watchdog hiển thị:
  + `final_status: blocked-vichanger-vpn`
  + `reason: [device-lock] machine N blocked by ViChanger/VPN preflight`
- **Bản chất kỹ thuật:**
  + Toàn farm cấm tuyệt đối ViChanger.
  + Nhãn `blocked-vichanger-vpn` là chuỗi legacy cũ trong `python_runner/flows/multi_machine_feed_session.py` (dòng 4240-4243) bọc exception khi gọi `require_vichanger_connected` (thực chất là alias của `require_proxy_connected` trong `core/vpn_preflight.py`).
  + Khi kiểm tra nguyên nhân thật, luôn đọc `stop_reason`. 99% trường hợp là máy bị ngắt kết nối Wi-Fi:
    `required router proxy is unreachable for <serial> (kill switch active or no connection): dumpsys connectivity: Wi-Fi not connected`
  + Preflight kiểm tra thấy không có Wi-Fi/proxy nên kích hoạt kill-switch chặn chạy để chống leak IP thật của máy.

## 2. Gating Follow sau Lướt Feed
- **Điều kiện thứ tự:** Flow follow chéo trong `run_all.py` / `batch_runner` được thiết kế chạy nối tiếp sau feed. Chỉ những máy hoàn thành lướt feed thành công trong phiên mới được chuyển sang bước kiểm tra follow.
- **Điều kiện tài khoản:** Ngay cả khi vào bước follow, hệ thống kiểm tra số lượng video trên profile:
  + Nếu tài khoản chưa đủ 5 video (`< 5 videos`), script lập tức skip với lý do: `under-5-videos-follow-disabled` (tuân thủ rule farm: nick mới chưa đủ 5 video cấm follow chéo để tránh checkpoint).
  + Máy bị `skipped-device-locked` hoặc preflight fail ở bước feed sẽ không được đẩy vào follow.

## 3. Phân biệt Preflight Safety Skip vs. Farm Alert [MÁY N]
- Khi máy bị lock (`skipped-device-locked` do process trước chưa release lock) hoặc bị chặn mạng an toàn (`blocked-vichanger-vpn` / Wi-Fi disconnected), runner chủ động đánh dấu skip và ghi log bảo vệ máy.
- Hệ thống KHÔNG gửi Farm Alert `[MÁY N]` cho các trường hợp preflight skip này vì đây không phải là lỗi app kẹt UI hay lỗi treo uiautomator trong phiên cần can thiệp.
- Farm Alert chỉ bắn khi máy đang trong phiên lướt feed thật và gặp sự cố dừng phiên (`manual-needed`, checkpoint, captcha, focus loss không tự phục hồi).

## 4. Tốc độ điều tra đối soát ca chạy (Tránh Delegation Treo)
- Khi user hỏi tình trạng máy fail hoặc số liệu ca chạy, KHÔNG delegate subagent chạy ngầm nếu chỉ cần đọc log đối soát (dễ gây timeout hoặc quét ổ đĩa).
- Trích xuất trực tiếp bằng đường dẫn cụ thể:
  `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/<row-session>/<run-id>/summary.txt`
  Kiểm tra `event_counts` và kết quả từng máy trong thư mục `machines/machine_<N>/.../summary.txt` để trả lời ngay lập tức.
