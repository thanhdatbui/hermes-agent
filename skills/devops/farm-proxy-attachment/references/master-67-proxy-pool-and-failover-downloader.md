# Master 67 Proxy Pool (MobiProxy + MikroTik PPPoE) & Fail-Over Rotation

## 1. Bản Chất Sự Cố & Bài Học Điều Phối (2026-09-12)
### Vấn Đề 1: Nhầm Lẫn Công Cụ & Tách Biệt Sai Giữa Phone Farm vs PC Tool
- **Quan niệm sai của Agent:** Cho rằng các cổng MikroTik PPPoE (`10001..10035`) hoặc MobiProxy (`5101..5132`) "chỉ dành riêng cho máy điện thoại, nếu script PC tải video nhảy vào sẽ chiếm dụng/đè IP".
- **Thực tế chuẩn của User:** Cả hai cụm proxy đều dùng chung hạ tầng cho toàn farm. Proxy sinh ra là để dùng xoay vòng; công việc nặng như batch download video nếu chỉ all-in vào 1 cụm hoặc vài cổng sẽ làm nghẽn cổ chai, lãng phí tài nguyên và dễ dính bot-check. Bắt buộc hợp nhất toàn bộ pool của cả 2 cụm (MobiProxy + MikroTik) để phân tán tải đều đặn.

### Vấn Đề 2: Lỗi DNS Hairpin & Giải Pháp Hosts Mapping
- **Hiện tượng:** Máy PC Kibe gọi vào domain `mirotik1.taadaa.click:1000X` bị `Connection timed out` 30s.
- **Root cause:** Domain `mirotik1.taadaa.click` phân giải ra IP WAN public (`171.231.181.33`). Router MikroTik đang chạy firewall DROP traffic từ WAN vào dải port quản trị/PPPoE và không cấu hình Hairpin NAT cho client nội bộ LAN đi vòng qua WAN.
- **Giải pháp O(1):** MikroTik RouterOS nằm tại IP LAN `192.168.110.2`. Thêm bản ghi DNS override vào `C:\Windows\System32\drivers\etc\hosts`:
  ```text
  192.168.110.2 mirotik1.taadaa.click
  ```
  Sau đó `ipconfig /flushdns`. Toàn bộ 35 cổng `10001..10035` lập tức phản hồi siêu tốc qua mạng nội bộ (~0.45s) mà không cần can thiệp firewall router.

### Vấn Đề 3: Nghẽn Cổ Chai I/O Database SQLite Trên Ổ Cơ HDD & Chuyển Dịch SSD
- **Hiện tượng:** Downloader 20 workers chạy một lúc thì bị đứng hình, treo ở 23/40 folders dù mạng vẫn thông.
- **Root cause:** File `state.db` (SQLite 46.444 dòng) nằm trên ổ cơ HDD `D:`. Dưới áp lực I/O nặng của tiến trình Render FFmpeg đọc ghi video liên tục, một câu query đơn giản bị block tới 156 giây (do bảng `videos` không có index).
- **Giải pháp chuẩn:** Di dời `state.db` (chỉ 18 MB) sang SSD NVMe `C:/CodexRuntime/tiktok-video/state.db` và đánh các index `(folder, status)`, `status`, `source_channel`. Tốc độ query giảm từ 156s xuống 0.0001s, giải phóng triệt để nghẽn cổ chai.

---

## 2. Kiến Trúc Master 67 Proxy Pool
Tổng số proxy: **67 ports live 100%**:
1. **32 ports MobiProxy:** `test.taadaa.click:5101` đến `5132` (Auth: `mobiN:TaadaaMobi#2026!`).
2. **35 ports MikroTik PPPoE:** `mirotik1.taadaa.click:10001` đến `10035` (Auth: `admin@1:admin@1`, route qua LAN `192.168.110.2`).

File master lưu cố định tại:
- `D:\Taadaa\Tiktok-video\proxy_pool_67.txt`
- `D:\Taadaa\Tiktok-video\combined_proxies_pool.txt`
- Generator script: `D:\Taadaa\Tiktok-video\scripts\generate_67_proxy_pool.py`

---

## 3. Quy Tắc Tải Video (Batch Downloader) Tối Ưu
- **Tách Biệt Worker Network I/O vs Render CPU (Chuẩn Gate 1):**
  - Worker Render (FFmpeg): Chạy ít (`--parallel 1` hoặc `2`) vì ngốn 100% CPU/GPU, gây lag máy host nếu mở nhiều.
  - Worker Download (yt-dlp): Chủ yếu là Network I/O, không tốn CPU/RAM $\rightarrow$ Bắt buộc mở lớn (`--parallel 20`) để kéo nhanh hàng loạt.
- **Cơ Chế Fail-Over Xoay Proxy Tức Thì Khi Gặp Lỗi:**
  - CẤM retry yt-dlp nhiều lần trên cùng một cổng proxy khi đã dính lỗi timeout/407/bot-check.
  - Bọc vòng lặp download với logic retry:
    ```python
    max_dl_attempts = 3
    for dl_attempt in range(max_dl_attempts):
        proxy = next_proxy(args)  # Luôn bốc proxy mới từ pool 67 cổng ở mỗi lần retry
        options["proxy"] = proxy
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([candidate.url])
            break  # Thành công thì thoát
        except Exception:
            if dl_attempt == max_dl_attempts - 1:
                raise
    ```
- **Nới Trần Ngách Hẹp Khi Thiếu Kênh Nguồn:** Khi gặp lỗi `insufficient_pool` do các ngách hẹp (nhạc, lập trình, vân tay...) chỉ có 4-8 kênh, thêm cờ `--max-folders-per-channel 2` để cho phép các kênh lớn san sẻ video sang các folder còn thiếu.
