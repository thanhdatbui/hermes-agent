# Kỷ luật Chống Đụng Hàng Liên Máy (Admin vs Kibe) & Nguồn Thú Cưng / Viral Niches

## 1. Cơ Chế Chống Đụng Hàng Tuyệt Đối (Farm Admin vs Farm Kibe)

Khi cả 2 máy Kibe và Admin cùng cào video, tuyệt đối **CẤM ĐỤNG HÀNG** (tải trùng video ID hoặc dùng chung kênh độc quyền giữa 2 máy).

### A. Đồng bộ Blacklist Video IDs qua OneDrive Shared
- Kibe quét toàn bộ kho video gốc (`state.db` + đĩa `D:\video goc`) và xuất danh sách video IDs ra:
  `D:\OneDrive\SharedData\tiktok-video\kibe_downloaded_ids.json`
- Admin quét kho `D:\video goc may 2` và xuất ra:
  `D:\OneDrive\SharedData\tiktok-video\admin_downloaded_ids.json`
- Cả hai file nằm trong thư mục OneDrive đồng bộ thời gian thực giữa 2 máy.

### B. Bộ Lọc Loại Trừ Tự Động (Cross-Machine Exclusion Filter)
Trong mọi pipeline cào video (`download_gaixinh_pipeline.py`, `run_admin_gaixinh_downloader.py`, `smart_gaixinh_distributor.py`):
```python
def load_cross_machine_exclusions() -> set:
    shared_dir = Path(r"D:/OneDrive/SharedData/tiktok-video")
    exclusions = set()
    # Nhận diện máy qua hostname hoặc đối số dòng lệnh
    is_admin = "admin" in os.environ.get("COMPUTERNAME", "").lower() or "may 2" in str(sys.argv).lower()
    target_file = shared_dir / ("kibe_downloaded_ids.json" if is_admin else "admin_downloaded_ids.json")
    if target_file.exists():
        with open(target_file, "r", encoding="utf-8") as f:
            exclusions.update(json.load(f))
    return exclusions
```
- Khi phát hiện candidate `vid_id in exclusions` -> log `[CROSS-MACHINE SKIP]` và bỏ qua ngay, không tải về đĩa.

### C. Bẫy Fallback Dồn Cục Kênh (Fallback Duplication Trap) & Sự Cố Admin Farm 56 Folder
- **Sự cố thực tế**: Khi `run_admin_gaixinh_downloader.py` trên Admin gặp lỗi timeout (600s) hoặc kênh lỗi, script fallback dồn cục về kênh đầu danh sách, dẫn đến:
  - Kênh `@YeuLu` bị tải trùng vào **56 folder khác nhau** trên Admin!
  - `@vinhxo69` bị dồn vào **19 folder**!
  - `@meohera103` bị dồn vào **8 folder**!
  - Đặc biệt, `@YeuLu` vốn đã được cấp cho **Folder 199 bên Kibe**, gây vi phạm nghiêm trọng quy tắc cấm Admin đụng hàng Kibe.
- **Quy tắc ngăn chặn bắt buộc (1:1 Strict Channel Locking)**:
  1. **Khóa 1:1 tuyệt đối**: Mỗi folder BẮT BUỘC map với 1 kênh creator riêng biệt. CẤM TUYỆT ĐỐI cơ chế fallback tự động bốc lại kênh đầu danh sách khi gặp lỗi.
  2. **Fail-fast khi hết kênh**: Nếu kênh lỗi hoặc đã bị claim, script phải ghi nhận lỗi và `SKIP` sang kênh tiếp theo trong danh sách, tuyệt đối không tải lặp lại kênh đã gán cho folder khác.
  3. **Kiểm tra chéo claims hai chiều**: Trước khi tải cho bất kỳ folder nào, bắt buộc kiểm tra cả `gaixinh_channel_claims.json` trên Kibe và metadata `channel_info.json` trên Admin.

---

## 2. Kỷ Luật Báo Cáo Watchdog & Lịch Farm Alert 6H

- **Ẩn Mục Download Khi Đạt 100%**:
  Khi kho video gốc đã hoàn thành 100% (đủ 640/640 folder $\ge 30$ video) và tiến trình download không chạy, script watchdog (`farm_render_download_watchdog.py`) tự động ẩn phần `Video gốc`, chỉ báo cáo tập trung `Tiến độ Render Tik1..Tik8`.
- **Lịch Gửi Định Kỳ 6H**:
  Cronjob watchdog `farm-render-download-watchdog` được cấu hình lịch `0 */6 * * *` (00:00, 06:00, 12:00, 18:00) và đích gửi trực tiếp về Telegram nhóm Farm Alert (`telegram:-5373649734`).

---

## 3. Nguồn Thú Cưng (Cute Pets / Funny Animals)

Thú cưng là một trong những niche có tỷ lệ xem lặp (loop rate) và chia sẻ cao nhất trên TikTok / Shorts do tính visual toàn cầu, không rào cản ngôn ngữ.

### A. Manifest Nguồn Tuyển Chọn
Được lưu tại `D:\Taadaa\Tiktok-video\data\source_manifest_thucung.jsonl` (đồng bộ tại `D:\OneDrive\SharedData\tiktok-video\source_manifest_thucung.jsonl`):
- **YouTube Shorts VN**:
  - `@YeuLu`: Kênh Yêu Lu (chó mèo hài hước, 65+ clip)
  - `@OVVanThe`: Kênh chó cảnh, huấn luyện chó
  - `@SuperMeoo68`: Kênh mèo cute, đời sống mèo
  - `@vinhxo69`: Vinh Xô Pet
  - `@meohera103`: Mèo Hera
  - `@bossdogvietnam`: Boss Dog Vietnam
  - `@poodleTran`: Poodle Trần
  - `@kenhcuabu-kcbweb1502`: Kênh Của Bụ
  - `@TuiTiếnPet`: Tui Tiến Pet
  - `@meouo.channel`: Mèo Ú Channel
- **TikTok Thú Cưng VN**:
  - `@hoatangchomeo`, `@mino.hoho`, `@laputa_farm`, `@petmartvietnam`, `@nongtraidaudau`
- **Douyin Cute Pets & Fallback Keywords**:
  - `chó mèo hài hước shorts`, `thú cưng dễ thương shorts`, `mèo cute tiktok shorts`, `douyin cute pets shorts`, `funny animal moments shorts`.

---

## 4. Phân Tích Các Niche Triệu View Tự Nhiên Cao Nhất Trên TikTok & Kỷ Luật Chọn Kênh

### ⚠️ BẤT BIẾN TỐI CAO TỪ USER (HARD CONSTRAINTS):
1. **BẮT BUỘC 100% KÊNH VIỆT NAM (Tuyệt đối cấm kênh ngoại quốc)**:
   - Toàn bộ nguồn video nạp vào farm BẮT BUỘC phải là **kênh của creator Việt Nam**.
   - **TIÊU CHUẨN "K ĐƯỢC CÓ TIẾNG NƯỚC NGOÀI" (BẤT BIẾN TỪ USER)**:
     - CẤM TUYỆT ĐỐI lọt bất kỳ tiếng nói ngoại quốc nào (tiếng Anh, Tàu, Pháp...) vào video farm. Video có tiếng nước ngoài sẽ phá vỡ thuật toán phân phối tệp người xem Việt Nam, khiến kênh bị kẹt mốc 200 view limbo hoặc bị đánh giá là nick spam/clone quốc tế.
     - Kể cả ngách hình ảnh thư giãn (ASMR, Oddly Satisfying): Bắt buộc kiểm tra kỹ audio stream qua `ffprobe` và mẫu âm thanh, đảm bảo 100% thuần âm thanh vật lý (tiếng cắt xà phòng, cát động lực, không lời), **TUYỆT ĐỐI KHÔNG CÓ VOICE-OVER TIẾNG ANH LINH TINH**.
     - Thẩm định thị giác (OCR): Chạy OCR trên các frame đại diện để đảm bảo không dính phụ đề/chữ tiếng nước ngoài trên khung hình.
   - CẤM TUYỆT ĐỐI nhặt kênh quốc tế/nước ngoài (kể cả ngách không lời) khi chưa có chỉ đạo riêng. Nguồn nước ngoài sẽ lệch bối cảnh, chữ trên video tiếng Anh/Tàu, âm thanh ngoại lai khiến thuật toán TikTok phân phối sai tệp khán giả Việt Nam.
2. **"NICHE NHIỀU VIEW" $\ne$ "KÊNH IDOL VIRAL TRIỆU FOLLOW"**:
   - **Sai lầm tai hại (Bị User chửi)**: Tìm ngách nhiều view lại đi tải video của các Idol/Hot girl triệu follow (Ngọc Kem, Lê Bống, Đào Lê Phương Hoa...). Mặt họ đã quá quen mặt trên TikTok VN, người xem nhìn vào biết ngay nick clone/reup giả mạo, dễ dính gậy bản quyền và bị thuật toán đánh spam/bóp reach nặng.
   - **Định nghĩa chuẩn của User**:
     - **Đúng Niche nhiều view**: Chọn các ngách có thuật toán ưu tiên giữ chân người xem (Retention & Loop rate cao) như: Gái xinh nhảy trend TikTok / đời thường VN, Thú cưng cute (chó mèo), Mẹo vặt, Ẩm thực đường phố VN.
     - **Kênh ÍT VIRAL HƠN**: Bắt buộc chọn các **kênh cá nhân, creator nhỏ hoặc vừa của Việt Nam** (ví dụ `@lelephomaiquee`, `@gi.xinh.y46`, `@hnh999995`...): clip quay tự nhiên, nhạc trend TikTok Việt Nam, mặt mộc mạc đời thường, chưa bị nhận diện rộng rãi. Khi reup và render lách thuật toán, nick trông y hệt một người dùng thật đang chia sẻ cuộc sống cá nhân, cắn đề xuất tự nhiên rất bền và an toàn.

### 5 Niche Triệu View Tự Nhiên & Giữ Chân Cao Nhất:
Ngoài **Gái Xinh** (Visual/Dance) và **Thú Cưng** (Cute/Funny), 5 niche giữ chân người xem và kích thích thuật toán tốt nhất gồm:

1. **Oddly Satisfying & Phục chế đồ cũ (Restoration / Craft ASMR)**:
   - Ép thủy lực, gọt xà phòng, phục chế giày dép/đồng hồ cũ gỉ sét, làm tiểu cảnh mini.
   - *Lợi thế thuật toán*: **Tỷ lệ giữ chân người xem (Retention) cực cao**, người xem tò mò nán lại đến giây cuối cùng để xem thành phẩm biến đổi.
2. **Ẩm thực đường phố & Cận cảnh nấu ăn (Street Food / Visual Food ASMR)**:
   - Visual xèo xèo chiên nướng, sốt bốc khói, cắt gọt hoa quả tốc độ cao.
   - *Lợi thế thuật toán*: Kích thích trực giác thị giác (Food Porn) mạnh mẽ, người xem dừng lướt ngay lập tức dù không hiểu tiếng.
3. **Mẹo đời sống kỳ lạ & Ảo thuật ngắn (Life Hacks & Optical Illusions)**:
   - Mẹo vặt gia đình độc lạ, ảo thuật 5–10 giây.
   - *Lợi thế thuật toán*: **Kích thích tranh luận trong comment** ("ảo ma", "lừa đảo", "thử rồi không được"), đẩy số lượng bình luận bùng nổ giúp video viral.
4. **Em bé & Hài hước gia đình đời thường (Cute Babies & Relatable Comedy)**:
   - Phản ứng ngộ nghĩnh của trẻ nhỏ, trò đùa vô hại.
   - *Lợi thế thuật toán*: **Tỷ lệ chia sẻ (Share) cao nhất**, người xem thường share cho người thân, bạn bè.
5. Thiên nhiên kỳ thú & Cận cảnh sinh tồn (Nature Wonders / Primitive Survival)**:
   - Bắt cá suối độc lạ, đào hang bắt cua, xây nhà đất sinh tồn, timelapse nảy mầm/nở hoa.
   - *Lợi thế thuật toán*: Cảm giác thư thái, thời gian xem trung bình (watch time) gấp 1.5 - 2 lần video thông thường.

---

## 5. Manifest Xoay Tua Đa Ngách Triệu View (`source_manifest_viral_rotation.jsonl`)

Nhằm tối ưu thuật toán đa dạng nội dung cho dàn nick farm, hệ thống tổng hợp manifest xoay tua đa ngách:
- **Đường dẫn**: `D:\Taadaa\Tiktok-video\data\source_manifest_viral_rotation.jsonl` (đồng bộ tại `D:\OneDrive\SharedData\tiktok-video\source_manifest_viral_rotation.jsonl`).
- **Quy mô**: 84 kênh lớn đã được thẩm định ($\ge 30$ video ngắn/kênh):
  - 🐶 **Thú cưng**: 25 kênh (Yêu Lu, OV Văn Thế, Super Mèo 68, Vinh Xô Pet...)
  - 💃 **Gái xinh / Douyin Dance**: 19 kênh + 43 Creator Douyin Visual
  - 🍜 **Ẩm thực đường phố**: 10 kênh (Vua Đầu Bếp, Trần Bình, Học viện Bò & Gấu...)
  - 🔨 **Oddly Satisfying & Craft ASMR**: 10 kênh (Sáng Tạo VN, Xuân Phán TV, Thiên Phạm...)
  - 💡 **Mẹo vặt & Khám phá**: 10 kênh (Kiến Thức Thú Vị, Ghiền Địa Lý, Ezsu...)
  - 👶 **Hài hước & Baby / Gia đình**: 10 kênh (POPS Music Kids, VTV7 Kids, Hài Tín Việt...)

---

## 6. Kỹ Thuật Bypass YouTube Rate-Limit & Bot-Check Siêu Tốc (2026 SABR Engine)

Khi cào hàng trăm video YouTube Shorts, YouTube thường kích hoạt cơ chế chặn:
1. `ERROR: [youtube] ...: Video unavailable` (do thiếu JS engine hoặc player client web bị hạn chế stream SABR).
2. `This content isn't available, try again later. The current session has been rate-limited by YouTube for up to an hour`.

### Bộ 3 Giải Pháp Đã Kiểm Chứng Thực Tế:
1. **Deno JS Runtime**: Cài đặt `pip install deno` để yt-dlp tự động nhận diện `deno.exe`, thực thi giải mã JavaScript challenge nội bộ.
2. **Player Client Android**: Thêm cấu hình `"extractor_args": {"youtube": {"player_client": ["android"]}}`. Client Android trả về stream MP4 trực tiếp ổn định hơn web client.
3. **Tự Động Xoay Proxy MikroTik LAN (192.168.110.2:10001..10035)**:
   ```python
   def get_mikrotik_proxy() -> Optional[str]:
       import socket, random
       s = socket.socket()
       s.settimeout(0.5)
       try:
           if s.connect_ex(("192.168.110.2", 10001)) == 0:
               port = random.randint(10001, 10035)
               return f"http://admin%401:admin%401@192.168.110.2:{port}"
       except Exception:
           pass
       finally:
           s.close()
       return None
   ```
   - Xoay ngẫu nhiên qua 35 cổng PPPoE MikroTik LAN giúp triệt tiêu hoàn toàn IP rate limit, đạt tốc độ tải 2 – 6 MB/s mỗi clip.

---

## 7. Hợp Nhất Master 69 Proxy Pool Chuẩn Toàn Farm (User Invariant)

- **Tổng cộng chính xác**: **69 PROXIES** (thay vì 67 như các script cũ):
  - **35 cổng MikroTik PPPoE**: `mirotik1.taadaa.click:10001..10035` (auth `admin@1:admin@1`, truy cập LAN qua `192.168.110.2` siêu tốc 0.01 - 0.4s).
  - **32 cổng MobiProxy**: 4 block x 8 cổng (`5101..5108`, `5111..5118`, `5121..5128`, `5131..5138` trên `test.taadaa.click`).
  - **2 cổng Dedicated WAN / KhoaLee**:
    - `khoalee.duckdns.org:16002:5ns08q:AmLmaMJ0` (Cổng KhoaLee Port 2 - Sống 100%, phản hồi 0.48s, IP: `116.111.194.124`).
    - `171.241.230.152:18009:khoaleewan2:propass` (Cổng WAN2).
- **Chi tiết 2 Cổng KhoaLee**:
  - **Port 16001**: `http://Gyx4k1:RzI0fc3o@khoalee.duckdns.org:16001` (Trích xuất từ 9router DB `data.sqlite`, từng gán Máy 37 & 75; TCP port OPEN, upstream dongle có thể tạm ngắt mạng).
  - **Port 16002**: `http://5ns08q:AmLmaMJ0@khoalee.duckdns.org:16002` (Từng gán Máy 38 & 76 và `master_gmail_manager.xlsx`; Sống 100%).
  - Các port `16003..16019`: Port TCP mở nhưng yêu cầu xác thực riêng (HTTP 407).
- **Tập tin phân phối**:
  - `D:/Taadaa/Tiktok-video/proxy_pool_69.txt` (danh sách master 69 proxy)
  - `D:/Taadaa/Tiktok-video/proxy_pool_67.txt` (backward-compat cho script cũ)
  - `D:/OneDrive/TaadaaData/proxy_combined_pool.txt` (đồng bộ cả cụm farm)
- Script sinh tự động: `python D:/Taadaa/Tiktok-video/scripts/generate_67_proxy_pool.py`.
