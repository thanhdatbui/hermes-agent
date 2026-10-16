# Xử Lý Xung Đột Device Lock Khi Nạp Avatar & Quy Chuẩn "Chuẩn Hoá 3 Món" (Ava - Hashtag - Pin)

## 1. Bản Chất Quy Chuẩn "Chuẩn Hoá 3 Món"
Khi nhận lệnh hoặc screenshot yêu cầu "Chuẩn hoá acc này" từ người dùng, Coordinator đối soát đồng thời 3 tiêu chí cốt lõi:

1. **Avatar (Ava)**:
   - **Soi mắt hiện trạng**: Đối chiếu avatar hiện tại trên app với nội dung video đang đăng trên kênh. Nếu kênh đăng bài tập Yoga / Giảm mỡ bụng nữ nhưng mang avatar phong cảnh, chó mèo, hay ảnh mặc định truyện tranh $\rightarrow$ **LỆCH NGÁCH, BẮT BUỘC ĐỔI**.
   - **Trích xuất & Crop**: Lấy frame đại diện từ $F_{src}$ (`D:/video goc/<F_src>/.avatar_work/representative_frames/`), crop vuông chuẩn `512x512`. Khuôn mặt nằm trục giữa, headroom đỉnh đầu vừa vặn 15–25% phía trên.
   - **Soi mắt trước khi gửi (Gate 6)**: Vẽ mask tròn mô phỏng avatar profile TikTok (bán kính $R = 256$, làm tối 70% vùng ngoài), mở qua `browser_navigate` + `browser_vision` kiểm chứng tận mắt trước khi phát thẻ `MEDIA:`.
   - **Đồng bộ & Khóa chống quét đè**:
     * Copy sang cả $F_{src}$ (`D:/video goc/<F_src>/avatar.jpg`) và $F_{out}$ (`D:/TIKTOK-videonuoinick/<F_out>/avatar.jpg`).
     * Tạo file `.manual_avatar_locked` tại cả 2 đầu thư mục.
     * Đăng ký vào cả 2 file `manual_avatar_protected_folders.json` (`D:/Taadaa/data/` và `D:/Taadaa/Tiktok-video/data/`).
     * Đặt cột `Avatar` trong `Tik<Slot>.xlsx` thành `PENDING`.
     * Chèn bản ghi vào SQLite `avatar_replace_queue` (`tiktok_tracker.db`).

2. **Hashtag Pool**:
   - Đối soát `Tik<Slot>.xlsx` cột `Keyword Video` và `Hashtag Pool`.
   - Đảm bảo Invariant 3 tầng của farm: 3–5 tags gồm các tag viral quốc dân (`#fyp #xuhuong #videohay...`) + **tối đa duy nhất 1 tag ngách** (ví dụ `#yoga`).

3. **Ghim Video (Pin Top)**:
   - **Ngưỡng cứng Farm Invariant**: **CHỈ GHIM VIDEO ĐẠT $\ge 1.000$ VIEWS** (tối đa 3 video).
   - **Quy tắc chống ghim flop**: Nếu tất cả video trên profile đều $< 1.000$ views (ví dụ 63, 176, 328 views), **BẮT BUỘC GIỮ NGUYÊN, KHÔNG ĐƯỢC GHIM ÉP**.
   - Watchdog nền sẽ tự động quét và ghim bổ sung khi có clip vượt ngưỡng 1.000 views.

---

## 2. Bẫy Xung Đột Device Lock Khi Kích Hoạt Nạp Avatar (`SKIPPED_LOCKED`)

### Hiện Tượng:
Khi chạy script nạp avatar thủ công hoặc batch launcher (`run_avatar_batch_3accs.py --tik <Slot> --machine <M>`), tiến trình kết thúc với exit code 0 nhưng xuất hiện log:
```text
Target bị bỏ qua trước/đầu launch: 1 (hoặc nhiều)
summary.csv: "34","0","3","SKIPPED_LOCKED","False","device lock active"
```

### Nguyên Nhân Gốc Rễ:
1. Máy farm $M$ đang bị giữ lock bởi một tiến trình hệ thống khác còn sống (PID liveness = True) — ví dụ batch 2FA ban đêm (`run_batch_live_2fa.py` PID `6332`), nuôi feed session (`tiktok_runner.py`), hoặc clear cache.
2. File lock tại `~/.codex/device-locks/machine_<M>.lock.json` mang trạng thái `status: queued_v2` hoặc `running`, kèm cờ `user_authorized: true` hoặc `pinned: true`.
3. Bộ lọc `machine_inventory._filter_locks` tự động phát hiện lock active và loại trừ máy $M$ khỏi danh sách launch để bảo vệ phiên tự động hóa đang chạy.

### Kỷ Luật Ứng Xử Invariant Farm Safety:
1. **CẤM TUYỆT ĐỐI**:
   - CẤM tự ý xóa file lock (`rm machine_<M>.lock.json`) khi tiến trình PID chủ sở hữu vẫn đang sống.
   - CẤM kill tiến trình batch của farm để giành giật máy.
2. **Quy Trình Xử Lý Chuẩn (Write-Through & Safe Handoff)**:
   - Bước 1: Hoàn tất 100% các bước chuẩn bị offline (ảnh crop chuẩn 512x512 tại 2 đầu, marker `.manual_avatar_locked`, registry JSON, Excel `PENDING`, SQLite `avatar_replace_queue`).
   - Bước 2: Báo cáo rõ ràng cho User: Ảnh avatar và dữ liệu đã sẵn sàng; hiện trường máy đang được tiến trình batch farm (kèm PID và tên script) sử dụng an toàn.
   - Bước 3: Cron watchdog `post-evening-avatar-watchdog` (chạy mỗi 5 phút) hoặc `avatar_replace_queue` watchdog sẽ tự động cuốn chiếu nạp avatar lên app ngay khi batch hiện tại hoàn tất và nhả device lock.
