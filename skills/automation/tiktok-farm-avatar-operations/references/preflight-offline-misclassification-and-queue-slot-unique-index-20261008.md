# Preflight Offline Misclassification & Queue Slot Unique Index Hardening (2026-10-08)

## 1. Hiện tượng & Phản ánh của Operator
- **Phản ánh 1:** Báo cáo watchdog liệt kê hàng loạt máy `[PREFLIGHT_VPN_BLOCKED]`, trong khi tất cả các máy đều cắm proxy đầy đủ trong `PROXYgandienthoai.xlsx` (*"Máy không có vpn là sao làm gì có chuyện đó"*).
- **Phản ánh 2:** Báo cáo đối soát hiện trường phát hiện 1 máy chứa tới 13 accounts trong hàng đợi avatar (*"Map 13 acc 1 máy là sao cái đéo gì thế"*).
- **Phản ánh 3:** Thắc mắc vì sao up avatar không đọc từ `taikhoan_run_safe.xlsx` mà đọc từ `Tik1..Tik8.xlsx` (*"Mà sao up avatar k dùng taikhoanrunsafe up mà cứ tự chế file v"*).

---

## 2. Nguyên nhân cốt lõi & Cơ chế lỗi

### A. Bẫy gán nhầm lỗi mất kết nối ADB thành lỗi VPN (`PREFLIGHT_VPN_BLOCKED`)
- Trong `run_post.py` (khối preflight), toàn bộ các exception kế thừa `ConsumerPreflightError` bị gom chung vào:
  ```python
  except ConsumerPreflightError as cpe:
      logger.error(f"[PREFLIGHT_VPN_BLOCKED] device={device_id} error={cpe}")
  ```
- Tuy nhiên, trong `automation_core/preflight.py`, hàm `require_android_vpn` khi không gửi được lệnh qua ADB do thiết bị tuột cáp / offline cũng ném ra:
  ```python
  raise ConsumerPreflightError(f"device is offline or ADB/USB disconnected for {serial_str}: {status.error}")
  ```
- **Hậu quả:** Máy bị tuột cáp USB hoặc rớt socket ADB nhưng telemetry lại báo `PREFLIGHT_VPN_BLOCKED`, khiến Operator và Coordinator chẩn đoán sai bản chất lỗi (nghĩ rằng proxy hỏng thay vì kiểm tra cáp/USB).

### B. Thiếu ràng buộc Unique Slot trên `avatar_replace_queue` dẫn đến dồn 13 nick / máy
- Schema cũ của `avatar_replace_queue`:
  ```sql
  PRIMARY KEY (username, tik, host_id)
  ```
- Khóa chính **không chứa cột `may`**.
- Khi một máy đổi nick (do migrate niche, thay acc die), lệnh `INSERT ... ON CONFLICT(username, tik, host_id)` thấy username mới nên chèn thêm dòng mới mà không xóa dòng cũ của máy đó.
- Dẫn đến máy 213 (và hơn 250 slot trên Admin) lưu song song cả nick cũ ngày 02/10 lẫn nick mới ngày 07/10 $\to$ đẩy số lượng lên 13 nick / máy, khiến runner cố switch sang nick cũ đã bị đá văng và báo `ACCOUNT_SWITCHER_FAILED`.

### C. Ranh giới sử dụng Workbook giữa các luồng
- **`taikhoan_run_safe.xlsx` (Dành riêng cho Nuôi & Follow):**
  - Chỉ gồm 4-5 cột: `['May', 'Device ID', 'ID', 'Video Đã Đăng', 'Ngày Tạo']`.
  - Hoàn toàn **KHÔNG có cột `Folder Video`** và **không chia slot `Tik 1..8`**. Không thể dùng cho runner avatar vì runner không biết nick thuộc slot Tik mấy và bốc ảnh từ folder render nào trên đĩa.
- **`Tik1.xlsx` đến `Tik8.xlsx` (Sổ cái chuẩn cho Upload & Avatar):**
  - Chứa đầy đủ: `Máy`, `device ID`, `ID`, `Folder Video`, `video gốc`, `Avatar Đã Up`.
  - Là nguồn dữ liệu chuẩn mực để đồng bộ media và gán slot chạy.

---

## 3. Quy trình khắc phục chuẩn hóa

### 1. Phân loại lỗi chính xác trong Preflight (`run_post.py`)
```python
except ConsumerPreflightError as cpe:
    cpe_str = str(cpe)
    if "device is offline" in cpe_str or "disconnected" in cpe_str:
        err_type = "DEVICE_OFFLINE"
    else:
        err_type = "PREFLIGHT_VPN_BLOCKED"
    logger.error(f"[{err_type}] device={device_id} vpn_required={vpn_required} error={cpe}")
    reporter.save_report({
        "status": "FAILED",
        "device_id": device_id,
        "reason": f"[{err_type}] {cpe}",
        "error_type": err_type,
        "vpn_required": bool(vpn_required),
    })
    return 2
```
- Đi kèm unit test kiểm chứng: `test_vpn_preflight_device_offline_saves_device_offline_report`.

### 2. Dọn sạch rác và khóa cứng Unique Index trên Database
1. Xóa các dòng rác lệch với `farm_account_info`:
   ```sql
   DELETE FROM avatar_replace_queue 
   WHERE rowid IN (
       SELECT q.rowid 
       FROM avatar_replace_queue q
       LEFT JOIN farm_account_info f ON q.may = f.may AND q.tik = f.tik AND q.username = f.username
       WHERE f.username IS NULL
   );
   ```
2. Tạo Unique Index ngăn ngừa vĩnh viễn việc trùng lặp slot:
   ```sql
   CREATE UNIQUE INDEX IF NOT EXISTS uq_avatar_queue_slot ON avatar_replace_queue(may, tik, host_id);
   ```
3. Đồng bộ database sạch sang máy trạm Admin:
   ```bash
   scp D:/Taadaa/data/tiktok_tracker.db admin-farm:D:/Taadaa/data/tiktok_tracker.db
   ```
