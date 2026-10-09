# Kỷ Luật Điều Phối Dual-Cluster & An Toàn Cron Task Farm (Kibe Local & Admin Remote)

## 1. Kiến Trúc Dual-Cluster (2 Cụm Máy)
- **Cụm 1 - Kibe (Local)**:
  * Quản lý dàn máy M01 – M80 (`range(1, 81)`).
  * Kết nối USB trực tiếp vào PC Kibe.
  * Socket ADB: Cục bộ (`adb_socket: None`), gọi lệnh trực tiếp qua `adb.exe`.
  * Sổ cái cấu hình: `D:\OneDrive\TaadaaData\kibe\Tik1.xlsx`.
- **Cụm 2 - Admin (Remote)**:
  * Quản lý dàn máy M201 – M280 (`range(201, 281)`).
  * Cắm USB vào PC Admin, kết nối qua LAN sang Kibe.
  * Socket ADB: `tcp:192.168.110.119:5037` (tham số CLI: `-H 192.168.110.119 -P 5037`, env: `ADB_SERVER_SOCKET`).
  * Sổ cái cấu hình: `D:\OneDrive\TaadaaData\admin\Tik1.xlsx`.

---

## 2. Quy Trình Chẩn Đoán Khi Nhận Cảnh Báo "Sao Không Chạy Bên Admin?"
Khi user hỏi "Ủa sao không chạy bên Admin?" hoặc khi báo cáo cron chỉ hiển thị dàn máy Kibe (M01-M80):
1. **CẤM SA ĐÀ VÀO DEBUG MÁY LẺ**: Không nhảy vào soi chi tiết các máy fail trên Kibe (như M33, M73...) làm loãng ngữ cảnh.
2. **KIỂM TRA KIẾN TRÚC SCRIPT NGAY**: Xác định xem script đang là **Single-Cluster** hay **Dual-Cluster**:
   - Biến workbook: Có bị hardcode cứng về `kibe\Tik1.xlsx` không?
   - Cấu trúc CLUSTERS: Đã khai báo danh sách cấu hình cho cả `kibe` và `admin` chưa?
   - Điều kiện trigger / Checkpoint ca nuôi: Script trên Admin có kiểm tra nhầm file state ở thư mục `runtime\kibe` dẫn tới tự hủy (`silent exit`) không?
   - Kết nối phần cứng Admin: Kiểm tra Remote ADB `192.168.110.119:5037` xem có bị sập cả Hub USB 20 cổng (như cụm M261-M280) không.

---

## 3. Các Bẫy Thiết Kế (Pitfalls) & Chuẩn Nâng Cấp Dual-Cluster (Sol Reviewer Gate >= 85)

### Bẫy 1: Rò rỉ biến môi trường Socket ADB (ADB Socket Leakage)
- **Hiện tượng**: Khi gọi batch cho Kibe sau hoặc song song với Admin, nếu `os.environ` đã có `ADB_SERVER_SOCKET`, lệnh ADB của Kibe sẽ bị định tuyến nhầm sang Remote Socket của Admin, gây timeout hoặc xung đột máy.
- **Quy tắc bắt buộc**:
  ```python
  env = os.environ.copy()
  if cluster.get("adb_socket"):
      env["ADB_SERVER_SOCKET"] = cluster["adb_socket"]
  else:
      env.pop("ADB_SERVER_SOCKET", None)  # Bắt buộc xóa để không rò rỉ socket remote vào local Kibe
  ```

### Bẫy 2: Lọc thiết bị kết nối theo danh sách Fleet (`total_connected`)
- **Hiện tượng**: Gọi `adb devices` đếm toàn bộ thiết bị trả về trong output (bao gồm máy test ngoài, giả lập, emulator), khiến tỷ lệ hoàn thành "Toàn farm hoàn tất X/Y máy" bị sai lệch.
- **Quy tắc bắt buộc**:
  ```python
  fleet_serials = {s for _, s in machines}
  cluster_connected_fleet = [s for s in connected if s in fleet_serials]
  total_connected += len(cluster_connected_fleet)
  ```

### Bẫy 3: Phá vỡ tính bất biến của chế độ Dry-Run (`--dry-run`)
- **Hiện tượng**: Tăng bộ đếm retry (`machine_retries`) hoặc ghi file state trước khi kiểm tra `args.dry_run`, làm thay đổi dữ liệu khi người dùng chỉ muốn chạy thử.
- **Quy tắc bắt buộc**: Kiểm tra `if args.dry_run:` và thoát sớm ngay sau khi in kế hoạch máy cần xử lý, tuyệt đối không gọi `save_state()`.

### Bẫy 4: Thời điểm tăng bộ đếm Retry (`machine_retries`)
- **Hiện tượng**: Tăng retry counter trước khi tiến trình chạy. Nếu máy gặp sự cố crash hoặc timeout hệ thống, máy sẽ bị mất lượt retry oan.
- **Quy tắc bắt buộc**: Chỉ tăng `machine_retries[str(m)] += 1` bên trong nhánh `else:` khi tác vụ thực thi trên thiết bị trả về thất bại thực tế (và bỏ qua các máy chỉ bị tạm khóa `[LOCKED]`).

### Bẫy 5: Tính Hermetic của Unit Test (Chống Phụ Thuộc Ổ Đĩa Thật)
- **Hiện tượng**: Unit test kiểm tra `Path("D:/OneDrive/.../Tik1.xlsx").exists()` hoặc đọc trực tiếp file excel production. Khi chạy trong môi trường CI/sandbox/khác máy, test sẽ fail ngay lập tức.
- **Quy tắc bắt buộc**:
  - Mock `openpyxl.load_workbook` và dữ liệu sheet trong unit test.
  - Viết test chứng minh toán học: `set(kibe_fleet) & set(admin_fleet) == set()` (Disjoint fleet ranges) để chứng minh an toàn tuyệt đối, không bao giờ xung đột ID khi dùng chung state file.

### Bẫy 6: Đồng bộ Type Signature & Return Tuples
- Khi bổ sung `cluster_name` vào kết quả trả về của worker function (`clear_device_cache`):
  - Phải cập nhật `-> tuple[int, str, bool, str, str]` ở khai báo.
  - Phải đảm bảo MỌI nhánh return (kể cả exception fallback, lock unavailable) đều trả về đủ 5 phần tử, tránh lỗi unpacking ở thread executor.
