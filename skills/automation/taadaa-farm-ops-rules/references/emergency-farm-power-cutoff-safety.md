# Quy trình Tắt Khẩn Cấp Farm Khi Mất Điện (Emergency Farm Shutdown)

## 1. Bản chất phần cứng Box Phone
- Công tắc cơ của box phone (hoặc rút phích cắm) **không khác gì cúp điện đột ngột**. Box phone không có bo mạch kích hoạt ACPI shutdown cho điện thoại bên trong.
- Nếu gạt công tắc / rút nguồn ngay khi Android đang ghi cache, SQLite DB (TikTok, Google Play) -> Dễ dính:
  + Bootloop / treo logo phân vùng `/data`.
  + Hỏng chip nhớ flash (eMMC/UFS) do sốc áp hoặc mất nguồn giữa chu kỳ write.
  + Corrupt session login / cookies tài khoản.

## 2. Kỷ luật vận hành khi có sự cố mất điện (UPS đang gánh)
1. **Không bắt người dùng nhớ lệnh ADB dài dòng**: Lúc cúp điện UPS kêu dồn dập, người dùng không thể nhớ hay gõ các lệnh phức tạp.
2. **Cơ chế 1-Click tiện dụng & đồng bộ**:
   - File thực thi đặt tại: `D:\OneDrive\TAT_FARM_KHAN_CAP.bat` và shortcut tại Desktop các máy điều khiển (`C:\Users\Kibe\Desktop\TAT_FARM_KHAN_CAP.bat`).
   - Cả máy Kibe và máy Admin đều truy cập được qua thư mục OneDrive chung.
3. **Quy trình 3 bước chuẩn**:
   - **Bước 1**: Chạy `TAT_FARM_KHAN_CAP.bat` (hoặc báo Hermes qua Telegram nếu Router mạng có cắm UPS). Script sẽ bắn song song `adb -s <serial> shell reboot -p` cho toàn bộ máy qua ThreadPool trong ~1-2s.
   - **Bước 2**: Chờ 3-5 giây để Android flush cache xuống bộ nhớ flash và ngắt nguồn an toàn.
   - **Bước 3**: Gạt công tắc Box Phone -> Tắt PC -> Tắt UPS.
