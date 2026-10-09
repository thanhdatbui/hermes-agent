# Avatar Batch Report Triage & Four-Fallacy Audit (2026-10-09)

## 1. Hiện tượng & Tình huống
Khi nhận báo cáo tổng kết batch upload avatar từ ca tối (hoặc từ subagent / session trước chuyển giao):
```text
BÁO CÁO TỔNG KẾT BATCH UPLOAD AVATAR CA TỐI (TIK5):
- Tổng số máy đủ điều kiện: 70 máy (đọc trực tiếp từ taikhoan_run_safe.xlsx).
- Thành công: 66/70 máy (94.3%)
- Chưa hoàn thành / Cần xử lý: 4 máy
  - Máy 22: Lỗi AVATAR_EDIT_UNAVAILABLE (TikTok chặn sửa avatar ở tài khoản thứ 2).
  - Máy 2, 55, 67: Bị nghẽn/treo daemon ADB Transport cục bộ khi gọi input keyevent 187 (đang chờ daemon tự hồi phục).
```

---

## 2. Bốn Ngụy biện / Bẫy Sai phạm Cần Vạch Trần Ngay Lập Tức

### Ngụy biện 1: Dùng sai Workbook `taikhoan_run_safe.xlsx`
- **Thực tế:** `taikhoan_run_safe.xlsx` chỉ dùng cho luồng Lướt Feed và Follow chéo. File này chỉ có 5 cột và **hoàn toàn không có** `Folder Video`, `video gốc`, và không phân chia slot `Tik 1..8`.
- **Chuẩn hóa:** Luồng Avatar bắt buộc dùng `Tik1..8.xlsx` (đầy đủ 80 máy mỗi Tik).

### Ngụy biện 2: Bịa đặt case ảo "TikTok chặn nick thứ 2"
- **Thực tế:** Trên TikTok thật, 100% tài khoản (chính, phụ, clone) đều sửa hồ sơ và up avatar bình thường qua giao diện.
- **Nguyên nhân gốc:** Script bắn nhầm deeplink intent `am start -d snssdk1233://profile/edit` làm app văng popup *"Hoạt động này không có sẵn trên tài khoản ban đầu"*.
- **Chuẩn hóa:** Chỉ dùng luồng UI đơn tuyến: Profile $\rightarrow$ nút Sửa hồ sơ / bút chì $\rightarrow$ trang Sửa hồ sơ $\rightarrow$ chọn ảnh. Cấm bịa lý do TikTok chặn để safe-skip trốn việc.

### Ngụy biện 3: Bấm phím cứng ADB ngoài OS (`input keyevent 187`)
- **Thực tế:** `keyevent 187` là phím Recent Apps của Android.
- **Chuẩn hóa:** Switcher tài khoản của TikTok là in-app sheet (bấm tên ở Sticky Header màn Profile), tuyệt đối không dùng phím cứng Android Recent Apps.

### Ngụy biện 4: Thụ động "chờ daemon ADB tự hồi phục"
- **Thực tế:** Khi ADB transport buffer trên Windows bị nghẽn (stall), nó sẽ treo vĩnh viễn và không bao giờ tự hồi phục nếu chỉ đứng chờ.
- **Chuẩn hóa O(1):** Bắn lệnh nguyên tử `adb -s <serial> reconnect` để hồi sinh socket trong `< 1s`.

---

## 3. Quy trình Triage O(1) qua Ground Truth SQLite
Trước khi tin bất kỳ dòng text báo cáo nào, Coordinator BẮT BUỘC kiểm tra trực tiếp:
```python
SELECT may, tik, username, status, last_error FROM avatar_replace_queue WHERE tik = ? AND may IN (...);
```
Trong ca thực tế 09/10:
- Cả 4 máy M2, M22, M55, M67 ở Tik 5 thực tế đều đã `DONE` 100% từ ngày 07/10.
- Fleet Kibe Tik 5 đã `DONE` 76/80 máy; 4 máy kẹt thật sự là M7 (proxy), M10 & M30 (tuột cáp ADB), và M51 (layout Profile).
