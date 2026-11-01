# Flop Channel Detection, Source Rotation, and Hot Niche Ground Truth

## 1. Bản Chất Vấn Đề (Flop 0 View & Cơ Chế Phát Hiện)
- Khi tài khoản farm đăng liên tục nhiều video nhưng dính `0 view` (hoặc tim < 20 sau >= 5 clip, hoặc 3 snapshot liên tiếp không tăng tim/follower), kênh đã bị thuật toán TikTok đánh giá là **FLOP / Shadowbanned**.
- Nguyên nhân phổ biến: Nguồn video cào (raw) thuộc dạng ẩm thực/nấu ăn cào tràn lan không mặt người, không voice, dễ bị quét trùng lặp (*Unoriginal / Duplicate Content*).
- **Quy tắc bất biến (User Constraint):**
  - **KHÔNG BỎ ACC**, không hạ cấp acc, không dừng đăng video.
  - Nick flop vẫn tiếp tục chu kỳ nuôi và đăng video bình thường theo nhịp độ farm.
  - Biện pháp duy nhất: **ĐỔI NGUỒN CÀO (Source Rotation)** và render nối tiếp từ `start_seq = (video_da_dang + 1)` để không làm gián đoạn lịch đăng và không xóa các clip cũ đã đăng trên TikTok.

## 2. Công Cụ & Quy Trình Cơ Giới Hóa
1. **Quét phát hiện flop:**
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
     --channel "<URL_KENH_MOI>"
   ```
   - Pipeline tự động: Dọn file thừa, cào tối thiểu 40 clip mới từ kênh nguồn vào staging, backup an toàn, hoán đổi thư mục raw, tạo `avatar.jpg`, render video bắt đầu từ `start_seq.mp4`, cập nhật Excel và ledger.

## 3. Ground Truth Đánh Giá Niche Hot Trên Farm
*Lưu ý cốt lõi:* Cột Keyword trong Excel `Tik*.xlsx` thường xuyên bị copy nhầm nhãn. BẮT BUỘC tra cứu nguồn cào thật từ `channel_info.json`, `gaixinh_channel_claims.json`, `source_manifest_viral_rotation.jsonl` hoặc metadata video thực tế.

- **Niche #1 - Gái xinh Visual / Dance / Trend (Douyin & VN):**
  - Thống trị bảng xếp hạng Follower toàn farm: Top 1 (`@huy010822` >1.000 FL), Top 2 (`@thanh.huyn4934` >500 FL), Top 4 (`@hakha18062003`), Top 5 (`@th.thy081`), Top 6 (`@lu.huyn926`).
  - Tỷ lệ xem lặp lại (loop retention) cao, dễ cắn For You Page.
- **Niche #2 - Tình huống Giao thông / Camera hành trình:**
  - Đạt lượng tương tác Tim khủng nhất trên mỗi clip: `@tuantuannguyen56` (RAW 56: `@VuiGiaoThôngVN/shorts` đạt 4.962 tim chỉ với 34 clip).
  - Tình huống thực tế bất ngờ, kịch tính, kích thích tranh luận và share.
- **Niche #3 - Câu chuyện cuộc sống / Ngoại ngữ:**
  - `@huynhim41` (6 clip đạt 1.8k tim), `@hoangthu18044` (15 clip đạt 2.3k tim).

## 4. Cạm Bẫy Kỹ Thuật (Pitfalls)
1. **CronRun Context Premature Exit:** Trong script watchdog báo cáo (`cron_stale_upload_watchdog.py`), nếu `with run_ctx as run:` bị đóng sớm ở đầu script thì context manager sẽ exit trước khi khối audit chạy. `run.set_report(msg)` ở cuối script trở nên vô tác dụng, dẫn đến script kết thúc với stdout rỗng (silent) và không đẩy tin về Telegram. Bắt buộc bọc toàn bộ luồng trong `run.__enter__()` và `run.__exit__()`.
2. **Nguồn cào YouTube Shorts vs TikTok Web:** Cào YouTube Shorts qua yt-dlp + MikroTik proxy (`192.168.110.2:10001-10035`) có độ tin cậy và tốc độ cao nhất (không bị lỗi secondary user ID / block session như TikTok profile web).
