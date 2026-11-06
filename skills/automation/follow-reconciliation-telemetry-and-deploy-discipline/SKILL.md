---
name: follow-reconciliation-telemetry-and-deploy-discipline
description: Kỷ luật đối soát số liệu follow chéo, chống ảo giác tự suy diễn follow tự nhiên và fix lỗi Join-Path PowerShell 5.1.
---

# Follow Reconciliation Telemetry & Deploy Discipline

## 1. Ground Truth Invariant: Chống Bịa Đặt / Suy Diễn Lượt Follow Tự Nhiên
- **Cạm bẫy:** Khi đối soát TikTok Web thấy delta tăng nhiều hơn số lượt follow chéo script báo cáo (ví dụ: script báo 12 lượt, nhưng Web tăng 17 lượt so với baseline cũ):
  - **CẤM TUYỆT ĐỐI** Coordinator tự đoán mò hoặc bịa đặt lý do "acc có follow tự nhiên khi lướt feed" nếu không có bằng chứng rõ ràng trong `log.jsonl`.
  - Trên thực tế, cấu hình lướt feed thường kiểm tra xác suất và bỏ qua (`'action': 'follow_video', 'result': 'skipped', 'error': 'roll skipped by follow rate percent'`).
  - **Bản chất kỹ thuật:** TikTok CDN/Web áp dụng mô hình **Eventual Consistency**. Khi tài khoản thực hiện batch follow mới, máy chủ TikTok mới flush và đồng bộ hiển thị các action follow cũ hoặc pending follow bị delay từ các phiên trước lên Web profile.

## 2. Invariant Đối Soát Khi Baseline Cũ (`is_stale_baseline = True`)
- **Vấn đề cũ (Khóa cứng equality):** Watchdog kiểm tra `latest_fl - prev_fl == expected_delta`. Khi delta trên web lớn hơn số lượt script báo (do gom flush trễ), điều kiện bị `False` và nick bị dán nhãn `UNPROVEN` oan uổng.
- **Quy tắc chuẩn hóa (Tolerant Lower Bound):**
  ```python
  stale_matches_expected = (
      bool(baseline_row)
      and is_stale_baseline
      and expected_delta > 0
      and (int(latest_row[0] or 0) - int(baseline_row[0] or 0)) >= expected_delta
  ) if latest_row else False
  ```
  - Khi Web ghi nhận delta $\ge$ `expected_delta` > 0: Xác nhận thành quả thực tế trên Web đã chứng minh script đã follow thành công tối thiểu số lượng đã báo.
  - Ghi nhận `script X lượt - web Y lượt - lệch (+diff) [baseline cũ (...)]`, TUYỆT ĐỐI KHÔNG dán nhãn `UNPROVEN`.
  - Chỉ dán nhãn `UNPROVEN` khi `web_delta < expected_delta` hoặc hoàn toàn thiếu snapshot.

## 3. PowerShell 5.1 `Join-Path` Positional Parameter Bug
- Trên Windows PowerShell 5.1 mặc định, `Join-Path` chỉ nhận tối đa 2 tham số vị trí: `Path` và `ChildPath`.
- Lệnh 3 tham số: `Join-Path $RepoRoot 'scripts' 'hermes_cron'` sẽ văng:
  `ParameterBindingException: A positional parameter cannot be found that accepts argument 'hermes_cron'`
  khiến các script deploy wrapper bị gãy ngầm mà không báo lỗi ra ngoài.
- **Sửa chuẩn:**
  ```powershell
  # Cách 1: Lồng Join-Path
  $SourceDir = Join-Path (Join-Path $RepoRoot 'scripts') 'hermes_cron'
  
  # Cách 2: Sử dụng .NET System.IO.Path
  $SourceDir = [System.IO.Path]::Combine($RepoRoot, 'scripts', 'hermes_cron')
  ```

## 4. Kỷ Luật Đo Đạc DB Thực Tế vs Ngưỡng Dò Mã Nguồn & Bản Đồ Slot 1.268 Nick
- **Phân biệt "Ngưỡng Script Dò Mồi" vs "Ngưỡng Thực Tế Gánh Tải":**
  - Nhìn vào code `follow_state.py` thấy `account_age_days >= 30` hoặc `age >= 60` chỉ là **ngưỡng cửa sổ bắt đầu thả mồi thăm dò (probe)** với budget nhỏ (1–3 follow).
  - Khi User hỏi về năng lực thật của farm, **BẮT BUỘC query trực tiếp DB (`tiktok_tracker.db` / `farm_master.db`)**, trích xuất Snowflake timestamp từ UID (`uid >> 32`) để đo tỷ lệ `following > 0` và sản lượng thực tế:
    * **30 – 59 ngày:** 90% bị nhả (Following = 0).
    * **60 – 89 ngày:** 42% có follow, nhưng trung bình chỉ đạt 1.0 follow/nick.
    * **90 – 120 ngày:** 70% follow được, trung bình 5.4 follow/nick $\rightarrow$ Bắt đầu gánh tải thực sự.
    * **> 120 ngày (Cựu binh):** 92% giữ follow, trung bình 98+ follow/nick.
- **Bản Đồ Phân Bổ 1.268 Slot Farm (CẤM Nhầm Lẫn Là "Kho Chờ Chưa Gán"):**
  - Tuyệt đối không query join nhầm bảng cũ `account_mapping` (chỉ có 597 acc) hay `account_state` (rỗng) dẫn đến hallucinate ra "kho chờ ngoài máy".
  - Bảng SSOT cấu trúc slot chuẩn là **`farm_account_info`** (1.268 nick):
    * **Cụm Kibe (80 máy x 8 slot = 640 nick):** Tik 1 đến Tik 8, tuổi từ 56d đến 230d.
    * **Cụm Admin (80 máy x 8 slot = 628 nick):** Tik 1 đến Tik 8, tuổi từ 37d đến 60d.
    * Tất cả 1.268 slot đều đã nằm trên máy thật (S7) và phân đều từ Tik 1 đến Tik 8.
- **Cơ Chế Bơm 2 Chiều Của Cựu Binh (Bi-directional Pumping):**
  - Nick cựu binh (Row 1, 2) là đối tượng gom follow để xuất bán (target), nhưng **bản thân chúng vẫn là động cơ bơm follow khỏe nhất cho các acc khác**. Không coi nick nhận follow là nick "ngồi im hưởng thụ".
- **Công Thức Tính Tải Xuất Xưởng Vụ Tết (30 Nick x 1.000 FL):**
  - Cần bơm chéo ~26.500 FL/tháng (~880 FL/ngày) sau khi trừ nền tảng có sẵn và follower tự nhiên từ video.
  - Với ~950 nick khả dụng (trừ 25% hao hụt do cooldown luân phiên và bảo trì máy), tải thực tế chỉ là **~0.92 follow / nick / ngày** $\rightarrow$ Dư sức đạt chỉ tiêu mà không cần ép tải bất kỳ nick nào.

## 5. Bẫy Đồng Bộ Wrapper Templates (`tiktok_runner.py` & 4-Way Parity)
- **Triệu chứng lặp lại:** Sửa logic trong git repo (`scripts/hermes_cron/tiktok_runner.py` nâng `timeout=180`, `workers=25`) nhưng Scheduler vẫn tiếp tục chạy file cũ trong `%LOCALAPPDATA%\hermes\scripts` và `deploy/hermes-home/scripts` (`timeout=90`, `workers=15`).
- **Nguyên nhân gốc rễ (Upstream Authority Trap):** 
  - `cron_sync_watchdog.py` lấy `DEPLOY_SCRIPTS` (`D:\Taadaa\Hermes\deploy\hermes-home\scripts`) làm master upstream.
  - Nếu chỉ chạy deploy sang `%LOCALAPPDATA%` mà không copy sang `DEPLOY_SCRIPTS` và `ONEDRIVE_SCRIPTS`, ở nhịp chạy tiếp theo `cron_sync_watchdog.py` sẽ phát hiện bản ở deploy cũ hơn hoặc lệch nội dung và **ghi đè ngược file cũ vào `%LOCALAPPDATA%`**!
- **Hậu quả ngầm:** Với Dynamic Pool Row 0 (>80 accs), tiến trình cào T0 trước phiên bị timeout 90s kill ngang giữa chừng ➔ Mất trắng snapshot baseline T0 cho Farm Kibe ➔ Watchdog lùi về baseline hôm trước (>20h) và kích hoạt lỗi `UNPROVEN`.
- **Kỷ luật Deploy bắt buộc (4-Way SHA-256 Parity):** Mọi thay đổi trong `scripts/hermes_cron/` BẮT BUỘC phải deploy đồng bộ 4 tầng (Source Repo, Deploy SSOT, AppData Scheduler Runtime, OneDrive Sync Shared) để bảo đảm 4 file có cùng mã SHA-256 tuyệt đối:
  ```powershell
  $src = 'D:\Taadaa\tiktok-luot nuoi acc\scripts\hermes_cron\tiktok_runner.py'
  $dst1 = Join-Path $env:LOCALAPPDATA 'hermes\scripts\tiktok_runner.py'
  $dst2 = 'D:\Taadaa\Hermes\deploy\hermes-home\scripts\tiktok_runner.py'
  $dst3 = 'D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\tiktok_runner.py'
  Copy-Item -LiteralPath $src -Destination $dst1, $dst2, $dst3 -Force
  ```

## 6. Bẫy Eventual Consistency CDN vs Vội Vã Dán Nhãn `UNPROVEN`
- **Bản chất hạ tầng:** Khi một máy farm vừa follow xong (ví dụ M36 follow 18 accs), Web profile của TikTok trên CDN/Edge server chưa thể flush ngay tại thời điểm kết thúc phiên (sau 10–15 phút web delta vẫn bằng 0). Vài giờ sau (như kiểm chứng lúc 09:27), CDN flush và web profile tăng đủ +18 khớp 100%.
- **Quy tắc xử lý:**
  - Khi baseline cũ và `web_delta == 0` lúc vừa kết thúc ca: Không được coi là thất bại vĩnh viễn hay phán bừa tài khoản không follow. Phải kiểm tra log thiết bị thực tế trước (`log.jsonl` -> `run_follow ok {'status': 'OK', 'followed': N}`).
  - **Khắc phục bug header watchdog (`total_reported` accumulator):** Trong `reconcile_cluster_following`, `total_reported += expected_delta` BẮT BUỘC phải được cộng dồn cả ở nhánh `else:` (nhánh UNPROVEN), triệt tiêu hoàn toàn lỗi header vô lý `+ Đối soát TikTok Web (Script báo 0 lượt follow):` khi chi tiết bên dưới vẫn báo 18 lượt.
  - Phân tách rạch ròi giữa việc "đã commit vào Git" và "đã deploy vào runtime Scheduler": Không bao giờ được khẳng định "đã fix xong" khi chưa verify hash SHA-256 trên `%LOCALAPPDATA%\hermes\scripts` và file template thật của Cronjob.

## 7. Quy Chuẩn Tạm Dừng Toàn Bộ Cron Nuôi Acc / Thao Tác Thiết Bị S7 Farm
- **Bối cảnh:** Khi User yêu cầu "Dừng cronjob nuôi acc", "tạm thời không đụng S7" hoặc khi cần đóng băng farm để bảo trì/nghỉ ngơi:
- **Danh sách 12 Cronjob bắt buộc Pause (Không để sót job phụ chạm ADB/USB):**
  1. `phase9-runner-tiktok-feed` (`cdd43b124363`): Feed runner chính.
  2. `phase9-staging-picker` (`304211820b28`): Staging picker tạo hàng đợi nuôi.
  3. `tiktok-feed-session-watchdog` (`1d62cb3562e0`): Giám sát phiên feed.
  4. `tiktok-follow-session-watchdog` (`6991768931e1`): Giám sát follow chéo.
  5. `night-tiktok-2fa-watchdog` (`2029d4224662`): Bật 2FA ban đêm trên thiết bị.
  6. `post-morning-gmail-2fa-watchdog` (`693dcacb8999`): Bật 2FA Gmail sau ca sáng.
  7. `post-noon-chain-watchdog` (`7d32d8c1907e`): Chuỗi Reg Gmail -> 2FA TikTok sau ca trưa.
  8. `post-evening-avatar-watchdog` (`25d6f8ab0264`): Upload avatar sau ca tối.
  9. `tiktok-rolling-rename-watchdog` (`35e94bb43979`): Đổi biệt danh trên máy.
  10. `farm-idle-screen-and-app-healer` (`48ac6f7fce40`): Đóng app về Home & chỉnh timeout màn hình S7.
  11. `farm-app-provision-watchdog` (`a78be2b1f517`): Kiểm tra và cài đặt 4 app S7.
  12. `end-of-day-clear-tiktok-cache` (`79021fa79d8b`): Dọn cache TikTok cuối ngày qua ADB.
- **Kỷ luật đồng bộ sau khi Pause:** Ngay sau khi pause trên Hermes CLI, BẮT BUỘC kích hoạt chạy `cron_sync_watchdog.py` để đồng bộ trạng thái `paused: true` trong `jobs.json` sang `DEPLOY_JOBS` và `ONEDRIVE_JOBS`, ngăn chặn các tiến trình sync đè ngược trạng thái active cũ.


