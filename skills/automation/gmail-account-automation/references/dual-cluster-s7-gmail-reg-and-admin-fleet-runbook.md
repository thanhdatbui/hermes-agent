# Dual-Cluster Farm Architecture & Admin Fleet Reg/Sync Runbook

## 1. Kiến Trúc Dual-Cluster Toàn Farm (Kibe + Admin)
Toàn bộ Farm Taadaa vận hành trên 2 cụm máy vật lý độc lập được điều phối trung tâm từ máy chủ Kibe qua mạng nội bộ:

| Tham số | Cụm 1: Farm Kibe | Cụm 2: Farm Admin |
| :--- | :--- | :--- |
| **Dải máy (Fleet)** | Máy 01 – 80 (hoặc dải mở rộng 1–166) | Máy 201 – 280 (80 máy) |
| **Cơ chế ADB** | Local USB / Default daemon (`localhost:5037`) | Remote ADB Server: `tcp:192.168.110.119:5037` (`adb -H 192.168.110.119 -P 5037`) |
| **Config Host** | `D:\Taadaa\machine-config\kibe.yaml` | `D:\Taadaa\machine-config\admin.yaml` |
| **Data / Workbooks**| `D:\OneDrive\TaadaaData\kibe\` | `D:\OneDrive\TaadaaData\admin\` |
| **Runtime / Locks** | `D:\Taadaa\runtime\kibe\` | `D:\Taadaa\runtime\admin\` |
| **Excel Gmail** | `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` | `D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx` |
| **Proxy Mapping** | `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` | `D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx` |

---

## 2. Pitfall Điển Hình: Đơn Cụm Bỏ Quên Admin (Single-Cluster Blindness)
Các runner hoặc watchdog đời cũ thường mắc lỗi nghiêm trọng:
1. **Hardcode đường dẫn Kibe:** Trỏ chết vào `D:\OneDrive\TaadaaData\kibe\...` hoặc biến môi trường cục bộ, khiến Farm Admin không bao giờ được phục vụ.
2. **Gọi `adb devices` chay:** Chỉ quét các thiết bị cắm trực tiếp vào máy Kibe, bỏ qua 80 thiết bị của Farm Admin đang kết nối qua ADB server `192.168.110.119:5037`.
3. **Báo cáo phân mảnh:** Báo cáo Telegram chỉ hiển thị số liệu của Kibe, làm Coordinator và User ngộ nhận toàn farm đã hoàn tất.

Các script cần chuẩn hóa Dual-Cluster:
- `post_noon_chain_watchdog.py` (Reg Gmail + Add 2FA TikTok sau Ca 2).
- `cron_clear_tiktok_cache.py` (Dọn cache TikTok cuối ngày).
- `sync_gmail_clean_v2_to_tong.py` (Gom toàn bộ Gmail LIVE ra file tổng).
- `taikhoan_sync_cron_launcher.py` (Sync `taikhoan_run_safe.xlsx` khi có thay đổi).
- `sync_all_tik_keywords.py` (Sync keyword/niche cho các file Tik1..Tik8 cả 2 cụm).

---

## 3. Pattern Chuẩn Hóa Dual-Cluster Runner (Kế thừa từ tiktok_runner.py)
Khi viết hoặc sửa bất kỳ runner / watchdog nào quản lý thiết bị farm:

```python
CLUSTERS = [
    {
        "name": "kibe",
        "label": "FARM KIBE - MÁY 1-80",
        "workbook_root": Path("D:/OneDrive/TaadaaData/kibe"),
        "runtime_root": Path("D:/Taadaa/runtime/kibe"),
        "host_config": r"D:\Taadaa\machine-config\kibe.yaml",
        "adb_server_socket": None,
        "gmail_excel": Path(r"D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx"),
        "proxy_file": Path(r"D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx"),
    },
    {
        "name": "admin",
        "label": "FARM ADMIN - MÁY 201-280",
        "workbook_root": Path("D:/OneDrive/TaadaaData/admin"),
        "runtime_root": Path("D:/Taadaa/runtime/admin"),
        "host_config": r"D:\Taadaa\machine-config\admin.yaml",
        "adb_server_socket": "tcp:192.168.110.119:5037",
        "gmail_excel": Path(r"D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx"),
        "proxy_file": Path(r"D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx"),
    },
]
```

### Nguyên tắc thực thi:
1. **Thiết lập biến môi trường trước khi gọi tiến trình con:**
   - Cụm Kibe: Xóa hoặc bỏ qua `ADB_SERVER_SOCKET`, set `GMAIL_EXCEL_FILE` và `PROXY_DIENTHOAI_PATH` của Kibe.
   - Cụm Admin: Set `ADB_SERVER_SOCKET="tcp:192.168.110.119:5037"`, set `GMAIL_EXCEL_FILE` và `PROXY_DIENTHOAI_PATH` của Admin.
2. **Kỷ luật thứ tự chạy:** Chạy tuần tự từng cụm (hoặc stagger so le) để kiểm soát băng thông mạng và tải ADB.
3. **Template Báo Cáo Hợp Nhất (Telegram):**
   ```text
   [BÁO CÁO CHUỖI SAU CA TRƯA] [LANE GMAIL]
   • FARM KIBE (M01-M80):   ✓ 15 | ✗ 1 (Tổng 16 máy)
   • FARM ADMIN (M201-M280): ✓ 14 | ✗ 2 (Tổng 16 máy)
   => TỔNG CỘNG: ✓ 29 | ✗ 3 (Tỷ lệ đạt: 90.6%)
   ```
