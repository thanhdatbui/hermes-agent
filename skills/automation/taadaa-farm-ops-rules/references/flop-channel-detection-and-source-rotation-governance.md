# Quy Chuẩn Quét Kênh Flop, Xoay Nguồn Cào & Cấm Bỏ Acc (Farm Taadaa)

## 1. Nguyên Tắc Cốt Lõi: CẤM BỎ ACC KHI FLOP (Keep-Alive Invariant)
- **TUYỆT ĐỐI KHÔNG BỎ ACC / KHÔNG DỪNG ĐĂNG VIDEO:**
  * Khi kênh TikTok bị flop (view lẹt đẹt < 200, tim kẹt đáy < 20 sau $\ge 5$ clip):
  * CẤM hạ cấp acc thành `SEEDING_ONLY`, cấm xóa nick khỏi danh sách upload, cấm dừng lịch đăng.
  * *Triết lý vận hành:* Nick nuôi trên farm vẫn giữ nhịp đăng video đều đặn theo chu kỳ máy; thuật toán TikTok có độ trễ phân phối và có thể cắn đề xuất ở các clip tiếp theo.
- **GIẢI PHÁP DUY NHẤT KHI FLOP: XOAY NGUỒN CÀO (SOURCE ROTATION):**
  * Không đổi niche loạn xạ trên nick cũ (lệch Audience Vector).
  * Giữ đúng hoặc tinh chỉnh ngách cùng họ, hoán đổi creator nguồn cào sang creator mới sạch, chưa bị nát nội dung.
  * **Bảo toàn mốc đã đăng:** Bắt buộc truyền cờ `--start-seq <video_da_dang + 1>` khi render kho mới (`swap_single_folder_pipeline.py`). Tuyệt đối không reset số thứ tự video đã đăng trong Excel.

## 2. Tiêu Chí Phân Loại Kênh Deterministic (Flop Detection Criteria)
Hệ thống đối soát dựa trên `tiktok_tracker.db` (`snapshots`, `farm_account_info`) và Excel `Tik1..Tik8.xlsx`:
1. **`NEW_WARMUP`:** Số video đã đăng $< 5$ clip. Chưa đủ mẫu số liệu để kết luận, tiếp tục ca đăng bình thường.
2. **`HEALTHY`:** Số video $\ge 5$, tổng tim $\ge 20$ và tỷ lệ $\text{heart\_per\_video} \ge 3.0$. Kênh đang tăng trưởng tốt, giữ nguyên nguồn cào.
3. **`STAGNANT_WATCH`:** Đã đăng $\ge 5$ clip nhưng tăng trưởng tim chậm ($< 3.0$ tim/clip). Đưa vào danh sách theo dõi thêm 3 ca quét.
4. **`FLOP_NEED_SOURCE_SWAP`:** Đã đăng $\ge 5$ clip nhưng tổng tim $< 20$ HOẶC $\ge 3$ snapshot ngày liên tiếp delta tim và delta follower đều bằng 0.

## 3. Ranh Giới Báo Cáo vs Tự Động Cào Nguồn (Throttle & Safety Gate)
- **NGUY CƠ TRÀN ĐĨA & NGHẼN BĂNG THÔNG:**
  * Mỗi kênh cào 40–45 clip + render FFmpeg tiêu tốn 15–30 phút CPU 100% và 2–3 GB dung lượng đĩa.
  * Nếu phát hiện 30 kênh flop mà để bot tự động bùng phát cào đồng loạt $\rightarrow$ Ngay lập tức tràn đĩa `0 MB Free` làm sập cụm render farm và nghẽn proxy MikroTik.
- **QUY CHUẨN ĐIỀU PHỐI (SEMI-AUTO 1 CHẠM QUA CRON 07:15):**
  * Cronjob `daily-stale-upload-accounts-watchdog` (07:15 sáng) tích hợp module `flop_channel_scanner.py`:
  * Tách biệt 2 nhóm rõ ràng:
    - *Nhóm Kẹt Kỹ Thuật (Stale Upload):* Máy rớt cáp ADB, runner crash, mất ID Excel $\rightarrow$ Sửa kết nối máy.
    - *Nhóm Đang Đăng Đều Nhưng Flop:* Máy chạy mượt nhưng view/tim kẹt đáy $\rightarrow$ Liệt kê Top kênh thảm nhất kèm ngách đề xuất và câu lệnh swap O(1) đã tính sẵn `start_seq`.
  * Sếp duyệt và gõ lệnh swap 1 chạm khi cần.
- **ĐIỀU KIỆN TIÊN QUYẾT NẾU TỰ ĐỘNG HÓA 100% (AUTO-QUEUE):**
  * Bắt buộc có Throttle: Tối đa $\le 1-2$ kênh/ngày, chỉ chạy vào ban đêm khi máy rảnh.
  * Bắt buộc lấy nguồn từ **Curated Hot Pool** đã kiểm định (không tiếng nói nước ngoài, không watermark KOL triệu follow), cấm AI tự ý tìm kiếm cào bừa ngoài web.

## 4. Công Cụ & Lệnh Vận Hành O(1)
- **Script lõi:** `D:/Taadaa/tools/flop_channel_scanner.py`
- **Quét toàn farm Kibe:** `python D:/Taadaa/tools/flop_channel_scanner.py --cluster kibe`
- **Quét riêng máy & sinh lệnh swap:** `python D:/Taadaa/tools/flop_channel_scanner.py --machine <N> --generate-swap-commands`
- **Xuất JSON cho cron/dashboard:** `python D:/Taadaa/tools/flop_channel_scanner.py --cluster kibe --json-output`
- **Suite kiểm thử:** `tests/test_flop_channel_scanner.py` (100% mocked offline).
