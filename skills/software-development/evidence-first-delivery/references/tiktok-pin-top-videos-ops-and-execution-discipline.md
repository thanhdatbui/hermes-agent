# TikTok Pin Top Videos Operations & Execution Discipline

## 1. User Steering & Anti-Stall Invariant
- **Thực thi ngay, cấm lảm nhảm / đối phó:** Khi User đã chỉ định rõ đối tượng hoặc lệnh thực thi (ví dụ: *"Làm đi Có video 8853 view kìa"*), CẤM TUYỆT ĐỐI đứng im giải thích cơ chế code, báo cáo `--dry-run`, hoặc ném ảnh preview rác (crop avatar) để câu giờ.
- Bắt buộc kích hoạt ngay lệnh chạy thật trên thiết bị, lấy kết quả thực tế, chụp ảnh màn hình điện thoại thật xác minh và gửi bằng chứng cho User.

## 2. Kỷ Luật Vận Hành Script `pin_top_videos.py`
- **Thời lượng và Timeout Guard:**
  + Flow ghim video đầy đủ gồm: Wakeup -> Mở Profile -> ATX dump UI -> Parse view các video tile -> Mở video -> Mở action sheet (Share/3 chấm) -> Bấm nút Ghim -> Chờ reload -> ATX dump verify lại.
  + Toàn bộ chuỗi thao tác trên máy thật thường kéo dài từ 35s - 50s.
  + **Bẫy Timeout 60s:** Terminal foreground bị chặn timeout > 60s (`[GUARD_FOREGROUND_TIMEOUT_EXCEEDED]`). Nếu chạy foreground với timeout 60s sẽ rất dễ văng `Exit 124` khi mạng hoặc máy bị trễ vài giây.
  + **Quy chuẩn chạy chuẩn:** BẮT BUỘC chạy qua tiến trình nền:
    ```bash
    terminal(background=True, notify_on_complete=True, timeout=180, command="python D:/Taadaa/tools/pin_top_videos.py --machine <N> --min-views 1000")
    ```
    Sau đó đợi bằng `process(action='wait', session_id=..., timeout=60)`.

- **Cứu hộ ATX-Agent Daemon khi Dump Rỗng (Empty UI):**
  + Nếu log xuất hiện `atx_dump_fallback` hoặc latency dump UI kéo dài > 7s rồi báo `status: empty`:
  + Kiểm tra và khởi động lại daemon atx-agent ngay qua lock an toàn:
    ```bash
    python D:/Taadaa/tools/with_device_lock.py --machine <N> --force-preempt -- adb -s <serial> shell /data/local/tmp/atx-agent server -d
    python D:/Taadaa/tools/with_device_lock.py --machine <N> --force-preempt -- adb -s <serial> forward tcp:7912 tcp:7912
    ```

## 3. Nghiệm Thu & Soi Mắt Màn Hình Thật (Gate 6)
- **Chụp ảnh màn hình thật sau khi ghim:**
  ```bash
  python D:/Taadaa/tools/with_device_lock.py --machine <N> --force-preempt -- adb -s <serial> exec-out screencap -p > D:/Taadaa/reports/standardization_previews/machine_<N>_pinned_evidence.png
  ```
- **Soi mắt trước khi gửi:**
  + BẮT BUỘC gọi `browser_vision` (hoặc OCR) mở ảnh ra soi trực tiếp.
  + Xác nhận:
    1. Đúng màn hình hồ sơ của tài khoản đích (`@username`).
    2. Ô video đầu tiên bên trái hàng trên cùng (top-left) phải hiển thị icon ghim / cờ "Đã ghim".
    3. Số view của ô đầu tiên khớp với video view cao nhất vừa chọn ghim.
  + Báo cáo rõ chi tiết đã nhìn thấy tận mắt kèm `MEDIA:<path>` trong cùng phản hồi.
