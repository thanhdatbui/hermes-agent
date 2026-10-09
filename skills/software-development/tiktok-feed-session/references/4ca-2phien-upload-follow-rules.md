# Kiến Trúc 4 Ca x 2 Phiên & Quy Tắc Ràng Buộc Upload / Follow

## 1. Lịch Phân Bổ 4 Ca x 2 Phiên / Ngày (HCMC - Asia/Ho_Chi_Minh)
- Toàn bộ farm chạy theo chu kỳ 4 Ca, mỗi Ca gồm đúng 2 Phiên:
  - **Ca 4 (Đêm):** Phiên 1 lúc `00:00` | Phiên 2 lúc `01:30` (Ngày chẵn: Row 8 | Ngày lẻ: Row 7).
  - **Ca 1 (Sáng):** Phiên 1 lúc `06:00` | Phiên 2 lúc `08:00` (Ngày chẵn: Row 2 | Ngày lẻ: Row 1).
  - **Ca 2 (Trưa):** Phiên 1 lúc `12:00` | Phiên 2 lúc `14:00` (Ngày chẵn: Row 4 | Ngày lẻ: Row 3).
  - **Ca 3 (Tối):**  Phiên 1 lúc `18:00` | Phiên 2 lúc `20:00` (Ngày chẵn: Row 6 | Ngày lẻ: Row 5).
  - **Dead Zone:** `02:30 -> 05:59` (tuyệt đối không dispatch).

## 2. Quy Tắc Phân Quyền Giữa Phiên 1 & Phiên 2
- **Phiên 1 (Session Index = 1):**
  - Mục tiêu: Chỉ lướt Feed + Follow chéo (với nick đủ điều kiện).
  - **CẤM TUYỆT ĐỐI đăng video ở Phiên 1.** `run-feed-session.ps1` chỉ truyền `--session-index 1`, không truyền cờ upload.
- **Phiên 2 (Session Index = 2):**
  - Mục tiêu: Lướt Feed + Follow chéo + **Tự động đăng video** (Upload hook).
  - `run-feed-session.ps1` truyền `-SessionIndex 2` -> tự động kích hoạt `--allow-upload-hook` xuống `run_tiktok.py`.
  - Nếu máy có file video tương ứng với Row trong ca nuôi acc thì thực hiện đăng; nếu không có video hoặc đã đăng trong ngày thì safe-skip an toàn.

## 3. Quy Tắc Gate An Toàn Cho Follow Hook (User Chốt 11/09/2026)
- **Ngưỡng tối thiểu:** Nick bắt buộc phải có **tối thiểu 5 video (`video_count >= 5`)** mới được kích hoạt follow hook.
- **Lý do an toàn:** Nick < 5 video (0..4 video hoặc chưa có số liệu) chưa đủ trust, follow sẽ bị TikTok nhả nút (unfollow ảo) hoặc dính action block ngay lập tức.
- **CẤM CHẶN CỨNG THEO ROW:** Tuyệt đối không dùng các logic cứng như `if row in (3, 4, 5, 6): return skipped`. Mọi Row (từ Row 1 đến Row 8), bất kỳ nick nào đã có $\ge 5$ video đều được phép đi follow.

## 4. Ngân Sách Thời Gian Thiết Bị & Chu Kỳ Nghỉ Của Nick (User Chốt 10/2026)
- **Chạy song song 160 máy**: 160 máy vật lý chạy hoàn toàn độc lập, song song. CẤM TUYỆT ĐỐI tính toán thời gian chạy theo kiểu dồn tuần tự cả farm.
- **Tải thực tế trên 1 máy S7**:
  - 1 ngày chỉ chạy đúng **4 nick** (ngày lẻ: Row 1, 3, 5, 7; ngày chẵn: Row 2, 4, 6, 8).
  - 4 nick x 2 phiên = **8 phiên / máy / 24h**.
  - Mỗi phiên lướt ~7-8 phút -> Tổng screen-on time chỉ **~60-64 phút / ngày**. Máy idle (ngủ sâu) > 22 tiếng/ngày, cực kỳ mát và an toàn cho pin S7.
  - CẤM TUYỆT ĐỐI tăng lên 3 phiên/ca: 2 phiên/ca (cách nhau 1.5 - 2h) đã là trần hoàn hảo mô phỏng người thật. Tăng lên 3 phiên/ca sẽ tạo chuỗi lặp máy móc và tăng nguy cơ dính bot detection.
- **Phân định Cố Định Vĩ Mô vs Random Vi Mô**:
  - **CỐ ĐỊNH VĨ MÔ (Macro Persona Schedule):** BẮT BUỘC CỐ ĐỊNH 100%. Row 1 luôn chạy Ca 1 ngày lẻ, Row 3 luôn chạy Ca 2... để tạo nhịp sinh học nhất quán cho nick trong mắt thuật toán TikTok. CẤM xáo trộn đổi giờ/đổi ca lung tung giữa các ngày.
  - **RANDOM VI MÔ (Micro Jitter):** Áp dụng bên trong khung giờ cố định. Jitter khởi động ca rải nhẹ ±3 đến ±7 phút (RandomizeMachineOrder + Stagger 2s-8s giữa các máy), kết hợp random dwell time (Fast Swipe 3-5s xen kẽ Deep Inspect 8-12s) để chống cờ bot cluster.
- **Chu kỳ nghỉ an toàn**:
  - Việc chạy luân phiên ngày Chẵn / Lẻ bản chất đã cho mỗi nick nghỉ liên tục **~32 – 36 tiếng** giữa 2 ngày hoạt động.
  - KHÔNG giãn thêm thành 1 ngày chạy 2 ngày nghỉ (nghỉ 48h) vì sẽ làm "nguội" Recency Signal, làm chậm quá trình tích lũy trust của tài khoản.

## 5. Quy Chuẩn Báo Cáo Chốt Phiên / Tổng Kết Farm Nuôi Acc
Mọi báo cáo chốt phiên hoặc điều phối farm BẮT BUỘC phải đề cập đủ **3 trụ cột**:
1. **Lướt Feed:** Số máy thành công, số máy fail, tổng số swipes.
2. **Đăng Video (Upload Hook):** Trạng thái theo Phiên 1 (không đăng) vs Phiên 2 (đã đăng / skip / thiếu video).
3. **Follow Chéo (Follow Hook):** Trạng thái follow, số lượt follow hoàn tất, số máy đủ điều kiện $\ge 5$ video.
CẤM TUYỆT ĐỐI bỏ sót báo cáo Follow hook trong tổng kết.
