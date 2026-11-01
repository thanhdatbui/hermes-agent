# Flop Channel Detection, Source Rotation, and Hot Niche Ground Truth

## 1. Bản Chất Vấn Đề (Flop 0 View & Cơ Chế Phát Hiện)
- Khi tài khoản farm đăng liên tục nhiều video nhưng dính `0 view` (hoặc tim < 20 sau >= 5 clip, hoặc 3 snapshot liên tiếp không tăng tim/follower), kênh đã bị thuật toán TikTok đánh giá là **FLOP / Shadowbanned**.
- Nguyên nhân phổ biến: Nguồn video cào (raw) thuộc dạng ẩm thực/nấu ăn cào tràn lan không mặt người, không voice, dễ bị quét trùng lặp (*Unoriginal / Duplicate Content*).
- **Quy tắc bất biến (User Constraint):**
  - **KHÔNG BỎ ACC**, không hạ cấp acc, không dừng đăng video.
  - Nick flop vẫn tiếp tục chu kỳ nuôi và đăng video bình thường theo nhịp độ farm.
  - Biện pháp duy nhất: **ĐỔI NGUỒN CÀO (Source Rotation)** và render nối tiếp từ `start_seq = (video_da_dang + 1)` để không làm gián đoạn lịch đăng và không xóa các clip cũ đã đăng trên TikTok.
  - **Trình tự dọn dẹp bắt buộc:** BẮT BUỘC dọn sạch video đã render cũ trước (`D:/TIKTOK-videonuoinick/<rend>`) rồi mới dọn video gốc (`D:/video goc/<raw>`), sau đó mới tải nguồn cào mới để tránh tình trạng bot nuôi lấy nhầm file render cũ đang dở dang.

## 2. Công Cụ, Watchdog & Cơ Chế Cảnh Báo Định Kỳ
1. **Watchdog giám sát định kỳ (Đã tích hợp):**
   - Tên Cronjob: **`daily-stale-upload-accounts-watchdog`** (ID: `5ad19a65f7ef`).
   - Lịch chạy: **07:15 sáng hàng ngày** (`15 7 * * *`).
   - Nơi nhận báo cáo: Group Telegram Farm Alert (`telegram:-5435853713`).
   - Script thực thi: `cron_stale_upload_watchdog.py`.
   - Cơ chế: Gọi `_get_flop_section(cluster="kibe", limit=8)` qua engine `flop_channel_scanner.py`. Khi phát hiện kênh flop ($f\_cnt > 0$), watchdog tự động gắn cờ `run.check("flop_accounts", f_cnt)` kích hoạt trạng thái `ANOMALY` để phát hành tin nhắn chi tiết kèm lệnh O(1) swap mẫu về Telegram.

2. **Quét thủ công hoặc theo máy cụ thể:**
   ```bash
   python D:/Taadaa/tools/flop_channel_scanner.py --cluster kibe [--machine <N>] --generate-swap-commands
   ```
   - Đọc kết hợp `tiktok_tracker.db` (bảng `snapshots`, `farm_account_info`) và các file `Tik1..Tik8.xlsx`.
   - Phân loại: `HEALTHY`, `STAGNANT_WATCH`, `FLOP_NEED_SOURCE_SWAP`, `NEW_WARMUP`.
   - Sinh sẵn câu lệnh swap O(1) với `start_seq = video_da_dang + 1`.

2. **Thi công xoay nguồn (Source Swap Pipeline):**
   ```bash
   python D:/Taadaa/Tiktok-video/scripts/swap_single_folder_pipeline.py \
     --machine <M> --tik <T> \
     --folder-raw <RAW> --folder-render <REND> \
     --start-seq <NEXT_SEQ> --min-videos 40 --clean-old \
     --channel "<URL_KENH_MOI>" \
     --uploader "<TEN_KENH>" --niche-slug "<SLUG>" --niche-label "<LABEL>"
   ```
   - Pipeline tự động: Dọn file thừa, cào tối thiểu 40 clip mới từ kênh nguồn vào staging, backup an toàn, hoán đổi thư mục raw, tạo `avatar.jpg`, render video bắt đầu từ `start_seq.mp4`, cập nhật Excel và ledger.

## 3. Ground Truth Đánh Giá Niche Toàn Farm (Thống Kê 1.272 Acc)
*CẢNH BÁO KỶ LUẬT:* TUYỆT ĐỐI CẤM lấy mẫu nhỏ lẻ 3-5 nick cá biệt để kết luận Niche hot. BẮT BUỘC tổng hợp trên toàn bộ dữ liệu farm (`tiktok_tracker.db` + toàn bộ `Tik1..Tik8.xlsx`).

- **Niche #1 - Câu chuyện cuộc sống (Storytelling / Triết lý / Cảm động):**
  - **Vua tương tác toàn farm:** 40 nick quản lý kéo tới gần 30.000 tim (trung bình 748 tim/nick, 45.7 tim/clip), tỷ lệ flop chỉ 5.0%.
  - Kênh tiêu biểu: Thông Thái (`@ThongThai`), `@huynhim41` (6 clip đạt 1.8k tim).
- **Niche #2 - Giao thông / Camera hành trình:**
  - **Hiệu suất / clip cao nhất farm:** 56.3 tim/clip, 1.365 tim/nick, 0% flop.
  - Kênh tiêu biểu: `@VuiGiaoThôngVN` (`@tuantuannguyen56` kéo gần 5.000 tim với 34 clip).
- **Niche #3 - Gym / Gái tập Gym / Fitness:**
  - **Tăng trưởng bền nhất farm:** 39 nick kéo hơn 8.000 tim, hơn 1.250 followers, chỉ 7.7% flop.
  - Cụm top đầu: `@thanh.huyn4934` (4.2k tim), `@th.thy081` (1k tim), `@lu.huyn926` (1k tim).
- **Niche #4 - Hài giả gái / Học sinh:**
  - Kéo follow nhanh (`@huy010822` >1.000 FL), nhưng độ phân hóa cao (tỷ lệ flop ~22%).
- **CÁC NICHE BẪY FLOP CẦN TRÁNH HOẶC THAY THẾ:**
  - **Ẩm thực quay cận cảnh không người:** 77 nick mà chỉ số lẹt đẹt (4.6 tim/clip), 13% flop. Rất dễ bị TikTok quét lỗi trùng lặp/unoriginal content bóp về 0 view.
  - **Yoga / Mỹ phẩm / Skincare / Cười cắt ghép:** Tỷ lệ flop từ 18% - 33%.

## 4. Cạm Bẫy Kỹ Thuật (Pitfalls)
1. **CronRun Context Premature Exit:** Trong script watchdog báo cáo (`cron_stale_upload_watchdog.py`), nếu `with run_ctx as run:` bị đóng sớm ở đầu script thì context manager sẽ exit trước khi khối audit chạy. `run.set_report(msg)` ở cuối script trở nên vô tác dụng, dẫn đến script kết thúc với stdout rỗng (silent) và không đẩy tin về Telegram. Bắt buộc bọc toàn bộ luồng trong `run.__enter__()` và `run.__exit__()`.
2. **Nguồn cào YouTube Shorts vs TikTok Web:** Cào YouTube Shorts qua yt-dlp + MikroTik proxy (`192.168.110.2:10001-10035`) có độ tin cậy và tốc độ cao nhất (không bị lỗi secondary user ID / block session như TikTok profile web).
3. **Thứ tự dọn thư mục khi swap nguồn:** BẮT BUỘC xóa dọn kho render (`D:/TIKTOK-videonuoinick/<rend>`) trước khi dọn kho raw (`D:/video goc/<raw>`), đảm bảo không còn clip tồn dư của nguồn cũ bị bot upload nhầm.
4. **Fallback INSERT Database:** Hàm update database trong swap pipeline cần cấp đủ trường ordinal để thỏa mãn ràng buộc NOT NULL của bảng folders.
4. **Kỷ Luật Thi Công Đồng Loạt (Batch Parallel Concurrency):** Khi User yêu cầu thay nguồn hàng loạt cho các kênh flop, CẤM TUYỆT ĐỐI tự ý thi công cuốn chiếu từng con một rồi chat dông dài (vừa mất thời gian vừa gây bực mình cho User). BẮT BUỘC khởi chạy song song nhiều tiến trình nền (`background=true, notify_on_complete=true`) cho từng cặp máy/folder mục tiêu. Dải proxy MikroTik (`10001 - 10035`) tự động phân bổ ngẫu nhiên theo cổng để chống thắt cổ chai mạng khi tải đồng thời nhiều luồng yt-dlp.
