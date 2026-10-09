# Admin Cluster Expansion & Decoupled 2FA Chain Watchdogs (06/10/2026)

## 1. Bối cảnh & Chỉ đạo dứt khoát từ Operator
- Operator phản hồi gay gắt khi thấy chuỗi 2FA bị gián đoạn:
  + *"kẹt phase reg gmail thì kệ con mẹ nó chứ mắc gì k chạy phase add 2fa đéo hiểu"*
  + *"tao cần thiết kế phase add 2fa nhiều hơn để phủ all nick kiểm tra lại các cron hiện tại r thiết kế cho tao"*
  + *"làm đi, mà add 2fa cả fam admin chứ"*
- Tình trạng thực tế lúc audit:
  + Farm Kibe: 639 nick active, 454 đã có 2FA, **185 nick còn thiếu 2FA** (22 nick thiếu pass).
  + Farm Admin: 614 nick active (Máy 201–280), **614/614 nick chưa từng có 2FA TOTP (100% thiếu)**.

---

## 2. Root Cause Bug Hạn Chế Máy Admin (NO_ELIGIBLE_TARGETS)
- Trong `python_runner/run_batch_live_2fa.py`:
  ```python
  def _machine(value: object) -> str:
      text = _clean(value)
      try:
          number = int(float(text))
      except (TypeError, ValueError):
          return ""
      return str(number) if 1 <= number <= 80 else ""  # BUG: Cứng trần 80
  ```
- **Hậu quả:** Khi runner chạy trên workbook Admin (`D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx`), toàn bộ máy 201–280 bị trả về chuỗi rỗng `""`. Hàm `freeze_targets()` lọc bỏ toàn bộ danh sách và ném lỗi `{"status": "validated", "reason": "NO_ELIGIBLE_TARGETS"}` mà không hề báo rõ nguyên nhân.
- **Bản vá chuẩn:** Mở rộng trần máy `1 <= number <= 999` để hỗ trợ toàn diện multi-cluster (Kibe 1–80, Admin 201–280, các dải máy tương lai).

---

## 3. Kiến Trúc Decoupled 2FA & Multi-Cluster Dispatch

### Nguyên tắc Decoupled (Chống nghẽn liên hoàn):
- Trong `post_noon_chain_watchdog.py`:
  + Đổi default `--lane all` (chạy cả Gmail và TikTok 2FA).
  + Tách biệt độc lập: Phase 1 (Reg Gmail) dù kết thúc với mã lỗi `FAILED` hay `SUCCESS`, hệ thống **BẮT BUỘC tiếp tục thực thi Phase 2 (TikTok 2FA)**.
  + Không bao giờ để lỗi của phase trước làm tê liệt phase bảo mật downstream.

### Dispatch đồng thời 2 Cụm Kibe + Admin:
- **Cụm Kibe (Máy 1–80):** Thực thi trực tiếp qua local runner với workbook `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`.
- **Cụm Admin (Máy 201–280):** Dispatch sang host `admin-farm` qua SSH:
  ```bash
  ssh -o ConnectTimeout=10 admin-farm \
    "powershell -NoProfile -Command \"Set-Location 'D:/Taadaa/tiktok-add-bao-mat-f2a'; & 'D:/Taadaa/python-envs/automation/Scripts/python.exe' python_runner/run_batch_live_2fa.py --workbook-path 'D:/OneDrive/TaadaaData/admin/taikhoan_dat_v2_updated .xlsx' --workbook-sheet 'Tài Khoản' --max-workers 40 --live\""
  ```
- Tự động skip các máy đang bận chạy ca nuôi feed theo cơ chế per-device lock (ví dụ PID 47872 đang chạy feed Row 4 trên Admin).

---

## 4. Ma Trận Khung Giờ Phủ 2FA Toàn Farm (Dual-Window Schedule)

| Khung Giờ (HCM) | Cronjob Name | Tần Suất | Đối Tượng & Hành Vi |
| :--- | :--- | :--- | :--- |
| **14:30 - 18:30** *(Sau Ca Trưa)* | `post-noon-chain-watchdog` | `*/5 14,15,16,17,18 * * *` | Cuốn chiếu Reg Gmail -> Add 2FA TikTok (40 workers Kibe + 40 workers Admin) trong khoảng nghỉ trước Ca 3. |
| **01:00 - 02:50** *(Đêm muộn)* | `night-tiktok-2fa-watchdog` | `*/10 1,2 * * *` | Quét càn toàn bộ nick thiếu 2FA / mật khẩu yếu của cả 2 cụm Kibe và Admin trước ca dọn cache 03:00 sáng. |
