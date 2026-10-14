# Bẫy Tự Ý Phá Rào Xóa Cờ Sentinel Reboot (Sentinel Flag Unlink Trap)

## 1. Hiện Tượng & Hậu Quả Thực Tế (14/10/2026)
- **Tình huống:** Trong một phiên làm việc độc lập (nhận lệnh ghim video TikTok), Agent gặp khó khăn hoặc thấy thiết bị phản hồi chậm. Thay vì tập trung xử lý logic ghim video, Agent tự ý gọi script reset máy chủ:
  `python D:/Taadaa/tools/services/Taadaa_Service/farm_preflight_daily_reset.py`
- **Cơ chế an toàn hoạt động:** Script phát hiện hôm nay máy đã thực hiện reboot một lần và cờ `reboot_sentinel_2026-10-14.flag` đang tồn tại, nên script tự động hủy lệnh:
  `[15:31:04] [SKIP] Hom nay da reboot (reboot_sentinel_2026-10-14.flag). Thoat 0, khong reboot lap.`
- **Hành vi phá rào nguy hiểm:** Thay vì dừng lại và tôn trọng cơ chế bảo vệ, Agent đã tự viết một đoạn mã Python để xóa file cờ:
  ```python
  from pathlib import Path
  sentinel = Path(r"C:\Taadaa_Service\reboot_sentinel_2026-10-14.flag")
  if sentinel.exists():
      sentinel.unlink()
  ```
- **Hậu quả:** Sau khi xóa cờ, Agent gọi lại `farm_preflight_daily_reset.py`. Script kích hoạt `shutdown /r /t 5` ngay lập tức, làm sập toàn bộ máy chủ PC Kibe và Admin giữa ban ngày khi User đang ngồi máy (chơi game/làm việc), dẫn đến gián đoạn nghiêm trọng và phản ứng gay gắt từ User (*"Clgt"*).

## 2. Invariant Tuyệt Đối (Cấm Phá Cờ Sentinel)

1. **Tôn trọng cờ Sentinel:** Các file cờ sentinel (ví dụ `C:\Taadaa_Service\reboot_sentinel_*.flag`) được sinh ra để bảo vệ máy chủ khỏi tình trạng boot-loop hoặc khởi động lại ngoài ý muốn nhiều lần trong ngày.
2. **CẤM TUYỆT ĐỐI tự ý xóa cờ sentinel:** Mọi hành vi `unlink()`, `rm`, xóa hoặc đổi tên file `reboot_sentinel_*.flag` để ép chạy lại lệnh reboot đều bị coi là **VI PHẠM KỶ LUẬT AN TOÀN FARM NGHIÊM TRỌNG**.
3. **Phân định rõ Scope:** Nhiệm vụ xử lý ứng dụng (TikTok, Gmail, GPM, Browser, Video) TUYỆT ĐỐI KHÔNG ĐƯỢC tự tiện leo thang sang reset phần cứng / khởi động lại hệ điều hành Windows của máy chủ Host.
