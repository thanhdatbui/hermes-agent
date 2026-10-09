# Cross-Farm Multi-Cluster Topology & Anchor Precedence Strategy

## Bối cảnh phân tầng Farm (Kibe vs Admin)
- Khi farm mở rộng sang nhiều cụm (ví dụ Cụm Kibe 80 máy vs Cụm Admin 80 máy), các cụm thường có vòng đời tài khoản lệch nhau:
  - **Cụm trưởng thành (Authority / Anchor Pool)**: Dàn nick Tik1, Tik2 đã đăng $\ge 10$ video, đủ điều kiện làm Anchor Mode 2.
  - **Cụm mới vận hành (Growth / Seed Pool)**: Dàn nick mới tinh hoặc chỉ mới đăng 1–2 video.
  - Dàn Tik3–Tik8 của cụm trưởng thành về bản chất nội dung cũng non trẻ tương tự cụm mới.

## Nguyên lý điều phối Follow đa cụm
1. **Bảo toàn Anchor Precedence**:
   - Thuật toán Mode 2 luôn có Hard Gate: Nick làm Anchor bắt buộc phải là Row $\le 2$ (Tik1/Tik2) VÀ có `video_count >= 10`.
   - Do đó, dù gộp chung danh sách UID của cả 2 farm thành một Combined Pool, 100% Anchor của Mode 2 vẫn thuộc về dàn Tik1/Tik2 của cụm trưởng thành (Kibe).
   - Mọi máy chạy Mode 2 (kể cả máy của cụm mới) đều search và vào trang cá nhân của Anchor cụm trưởng thành $\rightarrow$ xem video, bấm Like và follow chính Anchor đó (`_ensure_anchor_followed`) trước khi mở tab Following.
   - Kết quả: Dàn Tik1/Tik2 của cụm trưởng thành **luôn được hứng follow trước tiên**, không hề bị chậm tiến độ về đích.

2. **Phá vỡ đồ thị mạng khép kín (Anti Closed-loop Detection)**:
   - Nếu chạy cô lập từng farm, các máy trong cụm chỉ follow qua lại lẫn nhau trên cùng dải IP/thiết bị $\rightarrow$ tạo thành cụm mạng đóng (Closed-loop Clique / High Clustering Coefficient), thuật toán Anti-Spam dễ detect và mass-release.
   - Khi gộp Combined Pool:
     - Các máy cụm mới (Admin) sẽ dùng dải IP/proxy độc lập bên ngoài để follow về Anchor của cụm Kibe $\rightarrow$ tạo luồng follower ngoại vi cực kỳ tự nhiên và uy tín (High Trust Bridge).
     - Các máy cụm cũ khi quét danh sách hoặc bù budget Mode 1 sẽ follow xen kẽ cả nick của cụm mới $\rightarrow$ pha loãng đồ thị tương tác.

3. **Quy tắc thiết kế Data-layer**:
   - Ưu tiên gộp ở tầng dữ liệu thông qua script sync định kỳ xuất ra `taikhoan_run_safe_combined.xlsx` gộp toàn bộ row hợp lệ của các farm.
   - Runner không cần can thiệp logic nhạy cảm, vẫn giữ nguyên cơ chế lọc Anchor $\ge 10$ video và phân bổ budget tự nhiên.
