# Vận hành tải bù video đúng niche và render song song Kibe - Admin

## 1. Nguyên tắc cốt lõi
- **Chuẩn video:** Tối thiểu 40, đích đến 45 clip (>=45) cho toàn bộ 1.280 folder (Kibe M1..M80 và Admin M201..M280).
- **Đúng niche tuyệt đối:** Tải bù theo `niche` trong `Tik1.xlsx..Tik8.xlsx` / `niches_pool.txt`. Không dùng gái xinh thay thế các ngách khác.
- **Chống trùng lặp tuyệt đối:**
  - Giữa 2 máy: bắt buộc dùng chung và ghi vào ledger `D:\OneDrive\SharedData\tiktok-video\global-ledger\` (`Admin.jsonl` và `Kibe.jsonl`). Hàm `claim_source()` kiểm tra chéo trước khi bắt đầu tải.
  - Nội bộ máy: bảng `folders` và `videos` trong `state.db` kiểm soát claim/source/video.
- **Tải bù song song:** Không chờ một bên xong mới kích hoạt bên kia. Hai downloader đúng niche phải chạy đồng thời, tách khỏi render supervisor.

## 2. Bẫy thực tế & Cách khắc phục
1. **`reserve_folder()` bỏ qua folder thiếu:** Nếu folder có status `complete`/`complete_partial` nhưng `video_count < target_videos`, logic cũ có thể skip sai. Chỉ skip khi `(row["video_count"] or 0) >= target_videos`.
2. **Proxy IP tĩnh chết:** Nếu pool còn IP cũ (`116.107.115.121:5102..5132`), downloader có thể timeout và lặp `folders_repaired=0`. Dùng pool DDNS `test.taadaa.click:5102..5132` cùng các endpoint MikroTik hợp lệ; sau khi đổi pool phải restart downloader để nạp cấu hình mới.
3. **Admin render tự thoát sớm:** `admin_render_chain.py`/`run_tik*.ps1` có thể chỉ ghi `SKIP` khi source <40 hoặc output đã đủ 45 rồi thoát nhanh, khiến Task Manager không thấy `ffmpeg.exe`. Khi cần render thật 1 worker, dùng launcher Python quét workbook (`Tik1.xlsx..Tik8.xlsx`), lọc `src >= 40` và `out < 45`, rồi gọi trực tiếp `random_batch_render.py` tuần tự qua batch nền (như `scripts/run_admin_render_1_worker.py`).
4. **`--parallel 20`:** Cấu hình 20 workers song song ở cả Kibe và Admin (`--parallel 20` trong `auto_rescan_loop.py` và `run_download_all_sources.py`). Chú ý: `run_download_kibe.py` là launcher script trả về ngay PID rồi exit 0 (không phải downloader dừng); tiến trình con thực sự (PID được in ra) mới là downloader đa luồng cần theo dõi qua `psutil`/`tasklist`.
5. **Chống trùng chéo (Global Ledger):** Cả hai máy đều ghi nhận claims vào `D:\OneDrive\SharedData\tiktok-video\global-ledger` (`Kibe.jsonl` và `Admin.jsonl`). `claim_source()` trong `scripts/global_ledger.py` bắt buộc từ chối nếu source đã bị máy kia claim. Tuyệt đối không được tắt hoặc bypass ledger này khi chạy song song.

## 3. Evidence gate bắt buộc
- `WMIC ReturnValue=0` chỉ chứng minh process creation được chấp nhận, không chứng minh job đang chạy.
- Trước khi báo RUNNING, phải có remote PID sống, log mới chứa `[DOWNLOAD-ALL]` cùng state/output path, và `SOURCE_CLAIMED`/download thành công hoặc MP4 count delta tại output.
- Trước khi báo render chạy, phải có `ffmpeg.exe` sống và log mới ghi folder đang render; log `DONE` cũ hoặc PID cũ không được dùng làm bằng chứng.

## 4. Tài liệu chi tiết
Xem `references/parallel-niche-supplementation-kibe-admin.md` cho canonical split, recovery và evidence gate.
