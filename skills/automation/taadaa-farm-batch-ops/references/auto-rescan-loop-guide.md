# Hướng Dẫn Vận Hành Auto Rescan Loop Cho Downloader (Tiktok-Video Farm)

## Mục Đích
Tự động quét lặp các folder chưa đạt chuẩn trong toàn bộ farm (video_count < 30 hoặc `insufficient_pool`) cho đến khi đạt 100% farm mà không cần người vận hành phải chạy thủ công từng đợt.

## Vị Trí File
- Script điều phối: `D:\Taadaa\Tiktok-video\scripts\auto_rescan_loop.py`
- Script downloader lõi: `D:\Taadaa\Tiktok-video\scripts\download_by_niche.py`
- Python runtime: `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe`
- Database theo dõi: `C:\CodexRuntime\tiktok-video\state.db` (hoặc `D:\CodexRuntime\tiktok-video\state.db`)
- File log: `D:\CodexRuntime\tiktok-video\download_run.log`

## Cơ Chế Hoạt Động
1. **Truy vấn DB định kỳ**:
   ```sql
   SELECT folder_num, niche, video_count, status FROM folders 
   WHERE video_count < 30 OR status = 'insufficient_pool' 
   ORDER BY folder_num
   ```
2. **Kiểm tra hoàn thành**:
   - Nếu kết quả truy vấn rỗng: In `ALL_FOLDERS_COMPLETE: All folders have >= 30 videos.` và thoát loop với exit code `0`.
3. **Rescan vòng lặp**:
   - Nếu còn folder thiếu: Gom danh sách `folder_nums` thành chuỗi CSV (ví dụ: `1,2,5`).
   - Khởi chạy subprocess gọi `download_by_niche.py` với tham số chuẩn:
     ```bash
     D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe -u D:\Taadaa\Tiktok-video\scripts\download_by_niche.py \
       --total-folders 640 \
       --folders <folders_csv> \
       --sources D:\OneDrive\SharedData\tiktok-video\sources.qualified30.json \
       --niche-pool D:\Taadaa\Tiktok-video\data\niches_pool.txt \
       --exclusion-list D:\Taadaa\Tiktok-video\data\exclusion_list.txt \
       --verified-channels D:\Taadaa\Tiktok-video\data\verified_vn_channels.jsonl \
       --state-db <state_db_path> \
       --runtime C:\CodexRuntime\tiktok-video \
       --output-root "D:\video goc" \
       --niche-mode strict \
       --min-videos 30 \
       --target-videos 45 \
       --max-videos 65 \
       --max-folders-per-channel 2 \
       --parallel 10 \
       --continue-on-insufficient \
       --all-languages \
       --proxy-pool D:\Taadaa\Tiktok-video\proxy_pool_67_direct.txt \
       --cookies-dir D:\CodexRuntime\tiktok-video \
       --global-ledger-dir D:\OneDrive\SharedData\tiktok-video\global-ledger \
       --ledger-machine-id Kibe
     ```
   - Stream log trực tiếp vào `download_run.log`.
   - Chờ process kết thúc, sleep theo `--interval` (mặc định 15 giây), sau đó lặp lại vòng quét tiếp theo.

## Tham Số CLI
- `--max-rounds`: Giới hạn số vòng quét tối đa (mặc định: `0` là chạy lặp vô tận cho đến khi đạt chuẩn 100%).
- `--interval`: Thời gian nghỉ giữa các vòng quét (giây, mặc định: `15`).
- `--parallel`: Số luồng tải song song (mặc định: `10`).
- `--state-db`: Đường dẫn custom tới `state.db`.
- `--python-exe`: Đường dẫn custom tới Python binary.
- `--log-path`: File lưu log runtime (mặc định: `D:\CodexRuntime\tiktok-video\download_run.log`).

## Lệnh Khởi Chạy Chuẩn
```bash
D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe D:/Taadaa/Tiktok-video/scripts/auto_rescan_loop.py
```
