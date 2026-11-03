# Kỷ Luật Thống Kê Niche (Chống Bẫy Outlier Skew) & Đồng Bộ SQLite SSOT (2026-11-04)

## 1. Bẫy Thống Kê "Tổng Tim / Tổng Clip" (Nick Hoa Hậu Gánh Cả Ngách)
- **Hiện tượng thực tế:** Khi chạy kiểm toán 1.272 nick farm (`audit_niches_farm.py`), nếu chỉ lấy `Tổng Tim / Tổng Clip` (Average gộp) để đánh giá:
  - Ngách `Câu chuyện` có vẻ vượt trội với 39.0 tim/clip và hơn 31.000 tim.
  - Nhưng khi phân tích sâu: **Top 1 nick hoa hậu (@huynhim41) gánh tới 63.8% tổng tim** của cả ngách. Đa số các nick bình thường khác chỉ đạt median 5.7 tim/clip và 19.6% nick vẫn kẹt dưới sàn 3 tim/clip.
- **Kỷ luật bắt buộc:**
  1. **CẤM TUYỆT ĐỐI** dựa vào Average gộp để tư vấn chọn ngách cho nick đang flop.
  2. BẮT BUỘC phân tích theo:
     - **Median Tim/Clip (Trung vị):** Đo lường điểm sàn thực tế mà một nick trung bình nhận được.
     - **Median Follower:** Tỷ lệ chuyển đổi người theo dõi thực tế.
     - **Tỷ lệ Flop (< 3 tim/clip):** Xác suất nick bị chôn chân ở hố view sàn.
     - **Độ phụ thuộc Top 1 (% Tim từ nick cao nhất):** Kiểm tra xem ngách phát triển đồng đều hay bị méo mó do cá biệt 1 nick viral.
  3. **Kết luận xếp hạng sàn ổn định:**
     - 👑 **Gái xinh / Creator:** Điểm sàn an toàn nhất farm (Median 7.7 tim/clip, Median 43 follower, Flop chỉ 8.7%, độ phụ thuộc Top 1 chỉ 26.3%).
     - 🎵 **Âm nhạc:** Median 7.5 tim/clip, Flop 11.1%, độ phụ thuộc Top 1 chỉ 15.1% (phân bổ cực kỳ tự nhiên).
     - ❌ **Ẩm thực & Làm đẹp:** Đáy hiệu suất toàn farm (Median 2.6 - 3.3 tim/clip, Flop 38.5% - 55.6%).

---

## 2. Invariant SQLite SSOT Toàn Farm (`farm_master.db`) vs Excel Mirror
- **Bản chất kiến trúc:**
  - `D:/Taadaa/data/farm_master.db` là **MỎ NEO CHÂN LÝ DUY NHẤT (SSOT)**.
  - Các file `Tik<N>.xlsx` chỉ là mirror một chiều dùng để quan sát qua Office, **tuyệt đối không được dùng làm runtime dependency**.
- **Quy mô 1.280 slot tài khoản (160 máy):**
  - Cụm Kibe (Máy 1 - 80): 640 slot (Slot 1 - 8).
  - Cụm Admin (Máy 201 - 280): 640 slot (Slot 1 - 8).
  - Toàn bộ 1.280 slot được lưu trữ tập trung tại bảng `tiktok_workflow_state` trong `farm_master.db`.
- **Thao tác dữ liệu qua Data Access Layer (DAL):**
  - Mọi tác vụ tra cứu, cập nhật cursor (`posted_count`), cập nhật avatar (`avatar_status`), hoặc hoán đổi ngách (`update_niche_and_render`) **BẮT BUỘC** gọi qua module `D:/Taadaa/tools/farm_sqlite_dal.py`.
  - Kết nối sử dụng `WAL mode` + `busy_timeout = 15000ms` chống deadlock và triệt tiêu lỗi file lock OneDrive.

---

## 3. Hoán Đổi Nguồn Cho Cụm Máy Admin ($M \ge 200$)
- Khi chạy `swap_single_folder_pipeline.py` cho máy cụm Admin:
  1. `machine_0` của renderer bắt buộc map về dải `0..79`: `machine_0 = (args.machine - 201) if args.machine >= 200 else (args.machine - 1)`.
  2. `workbook_path`: Trỏ đúng thư mục `D:/OneDrive/TaadaaData/admin/Tik<Slot>.xlsx`.
  3. Preflight Proxy: Thiết bị Admin cần có `global http_proxy` (`192.168.110.2:1000N`) trước khi chạy upload avatar, nếu thiếu sẽ bị chặn bởi `[PREFLIGHT_VPN_BLOCKED]`.
