---
name: farm-reverse-api-vs-real-device-discipline
description: Kỷ luật phân định ranh giới giữa Reverse Internal API vs Vận hành Thiết bị Thật trên Phone Farm, chống over-engineering vô ích.
---
# Farm Reverse API vs Real Device Discipline

## Core Invariants

### 1. Ranh giới Giữa Cào Dữ Liệu HTML 0.3s vs Internal API Chữ Ký
- **Thực tế Farm**: Script canonical `D:/Taadaa/tools/tiktok_account_tracker.py` bóc thẻ JSON `__UNIVERSAL_DATA_FOR_REHYDRATION__` từ HTML public profile đạt tốc độ thực tế **~0.29s / nick** (0.297s trên nick `huy010822`).
- **Cấm Over-Engineering**: Tuyệt đối không thay thế cơ chế cào HTML 0.3s bằng các Internal API (`/api/post/item_list`, `/api/user/list`) đòi hỏi chữ ký động (`a_bogus`, `X-Bogus`, `X-Gorgon`). Request không có chữ ký sẽ bị trả về `len == 0` (Silent Drop); việc duy trì môi trường JS VM để sinh chữ ký sẽ kéo tụt tốc độ xuống 2-3s/nick (chậm gấp 10 lần) và gãy code mỗi 2-4 tuần khi TikTok cập nhật Wasm.

### 2. Sự Thật về Kiểm Tra Nick Bị Chặn Thao Tác (Action Block / Shadow Follow Ban)
- **Không tồn tại API kiểm tra từ xa**: TikTok không bao giờ phơi cờ `is_follow_blocked` ra ngoài public API. Mọi API từ bên ngoài soi vào nick bị cấm follow đều thấy profile bình thường (`status: LIVE`).
- **Ground Truth Duy Nhất trên Máy Thật**: Cơ chế kiểm tra duy nhất đúng là thao tác thật trên thiết bị Android: Bấm nút Follow $\rightarrow$ Reload lại profile $\rightarrow$ Soi xem nút có bị nhả về `NOT_FOLLOWED` (theo logic chuẩn của `verify_follow.py`) hay không. Cấm Coordinator hứa hẹn hoặc vẽ vời "API check trước nick bị cấm follow".

### 3. Khung Định Hướng Sử Dụng Reverse Engineering Hợp Lý
- **VÙNG NÊN DÙNG**:
  1. Giải mã file workflow tĩnh bị đóng gói/mã hóa từ bên ngoài (e.g. `.gemphonefarm` AES-256 sang Python ADB).
  2. Tải direct link CDN video không watermark từ Douyin/Kuaishou (e.g. `douyin-auto-dub`).
- **VÙNG TUYỆT ĐỐI CẤM**:
  1. Cố đấm ăn xôi thay thế runner máy thật bằng API giả lập để đi follow, thả tim hay tương tác.
  2. Đập bỏ các script monolith đang chạy ổn định của farm để viết lại từ đầu bằng AI.
