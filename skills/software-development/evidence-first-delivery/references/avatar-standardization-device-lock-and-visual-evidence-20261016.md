# Bằng Chứng Thị Giác Khi Chuẩn Hóa Profile & Xử Lý An Toàn Tranh Chấp Device Lock (2026-10-16)

## 1. Bối Cảnh Thực Tế
Khi User gửi ảnh chụp Profile TikTok (ví dụ: kênh Yoga `@yobi1965` trên Máy 34) với yêu cầu *"Chuẩn hoá acc này"*, Coordinator thực hiện quy trình chuẩn hóa 3 món (Ava - Hashtag - Pin). Trong quá trình thực hiện, thao tác nạp avatar lên thiết bị có thể bị chặn bởi hàng rào bảo vệ Device Lock (`SKIPPED_LOCKED` do batch 2FA ban đêm đang giữ máy).

## 2. Kỷ Luật Bằng Chứng Thị Giác (Evidence-First Invariant)
1. **Soi Mắt Trực Tiếp Profile Ban Đầu**:
   - Xác định rõ máy ($M = 34$), Slot ($Slot = 6$, `Tik6.xlsx`), Folder nguồn ($F_{src} = 434$), Folder render ($F_{out} = 270$).
   - Soi mắt avatar hiện tại: Nhận diện avatar phong cảnh rừng cây lệch chủ đề Yoga của kênh.
2. **Kiểm Thử Mẫu Bằng Chứng Khung Tròn**:
   - Trích xuất frame mặt từ video gốc, crop chuẩn vuông $512\times 512$, headroom trần đầu $\ge 30\text{px}$.
   - Dựng ảnh preview khung tròn TikTok `tmp_avatar_circle_preview.jpg` (vẽ đường viền tròn, làm tối $70\%$ viền ngoài).
   - **Soi mắt bắt buộc trước khi gửi**: Mở file qua `browser_navigate` và gọi `browser_vision` kiểm chứng nhân vật nằm chính giữa, không lẹm chữ/cụt đầu.
   - Gửi thẻ `MEDIA:<path_posix>` trên dòng độc lập, kèm xác nhận ngắn gọn nội dung nhìn thấy qua vision.

## 3. Xử Lý An Toàn Khi Gặp Xung Đột Device Lock (`SKIPPED_LOCKED`)
1. **Nguyên nhân**:
   - Runner `run_avatar_batch_3accs.py` kết thúc với `ExitCode: 0` nhưng `summary.csv` báo:
     `"34","0","3","SKIPPED_LOCKED","False","device lock active"`
   - File lock `~/.codex/device-locks/machine_34.lock.json` đang được giữ bởi tiến trình batch bảo mật ban đêm (ví dụ: `run_batch_live_2fa.py` PID `6332` chạy `status: queued_v2`).
2. **Kỷ luật bất biến**:
   - **CẤM cướp lock hoặc xóa file lock** khi PID chủ sở hữu vẫn đang sống (`psutil.pid_exists(pid) == True`).
   - **Không báo hoàn thành giả tạo**: Không khẳng định avatar trên app đã đổi khi runner bị `SKIPPED_LOCKED`.
   - **Safe Handoff**:
     * Đã chuẩn bị sẵn file avatar tại cả 2 đầu $F_{src}$ và $F_{out}$.
     * Đã tạo marker `.manual_avatar_locked` chống quét đè.
     * Đã cập nhật cột `Avatar = 'PENDING'` trong file Excel `Tik<Slot>.xlsx`.
     * Đã nạp bản ghi `PENDING` vào hàng đợi SQLite `avatar_replace_queue`.
     * Bàn giao cho cronjob `post-evening-avatar-watchdog` tự động nạp lên app ngay khi batch 2FA hoàn tất và nhả device lock.
