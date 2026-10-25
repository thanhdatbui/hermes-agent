# Cross-Cluster Alert Timeline Audit & Transient Socket Triage

## 1. False Diagnosis Trap (Bẫy Quy Kết Vội Hạ Tầng)
Khi nhận báo cáo từ cronjob liên cụm (như `cron_clear_tiktok_cache.py` chạy từ Kibe sang Admin qua `192.168.110.119:5037`):
```text
🏢 【FARM ADMIN - MÁY 201-280】
• Đã hoàn tất: 0 máy (None)
• Lỗi (0)
```
- **BẪY KẾT LUẬN VỘI:** Khẳng định "ADB Admin bị bind loopback 127.0.0.1", "Admin bị mất mạng LAN", hoặc "Admin PC bị tắt".
- **HẬU QUẢ NGHIÊM TRỌNG:** Bị User phản bác và quở trách ("Xàm lồn sao mấy ca trước chạy được?"), vì thực tế các ca nuôi feed trước đó trong cùng ngày (08:00, 12:00, 14:00) vẫn do Kibe điều phối qua `tcp:192.168.110.119:5037` và 74+ máy Admin chạy thành công 100%!

---

## 2. Timeline Sanity Check (Quy Trình Đối Soát Lịch Sử Bắt Buộc)
Trước khi kết luận hạ tầng mạng hỏng hoặc ADB binding sai:
1. **Kiểm tra các phiên chạy gần nhất trong ngày của cụm từ xa:**
   - Soi thư mục `D:/Taadaa/runtime/admin/live/<YYYY-MM-DD>/`.
   - Đọc `summary.txt` ca gần nhất: nếu `event_counts.success >= 50`, khẳng định **kết nối LAN và ADB remote giữa Kibe và Admin hoàn toàn thông suốt**.
2. **Kiểm tra log can thiệp dịch vụ Admin (`D:/Taadaa/logs/admin_ssh.jsonl`):**
   - Rà soát các lệnh thực thi trên Admin quanh khung giờ cronjob dọn cache (03:00 - 05:00 sáng).
   - Tìm kiếm sự kiện: `taskkill /F /IM adb.exe`, `restart_adb.py`, reboot host, hoặc kẹt socket.
   - Nếu phát hiện thời điểm `netstat -ano | findstr :5037` trả về exit code 1 (không có tiến trình lắng nghe), đây là **lỗi TRANSIENT do đụng cửa sổ bảo trì/restart ADB ngầm**, không phải lỗi cấu hình vĩnh viễn.

---

## 3. Lỗ Hổng Hiển Thị Báo Cáo Gây Hiểu Lầm
- Khi `get_connected_devices()` gặp timeout (do ADB server đang trong nhịp restart), hàm trả về dictionary rỗng `{}` $\rightarrow$ `online_fleet = []` (0 máy).
- Khi tính toán báo cáo:
  * `Đã hoàn tất = len(c_succ) = 0` $\rightarrow$ In `0 máy (None)`
  * `Lỗi = len(online_fleet) - len(c_succ) = 0 - 0 = 0` $\rightarrow$ In `Lỗi (0)`
- **Quy chuẩn sửa đổi:** Nếu `online_fleet == 0` trong khi `fleet_total > 0` (file workbook vẫn đọc được 80 máy), bắt buộc báo cáo phải hiển thị:
  `🚨 Cảnh báo: Không kết nối được ADB Host Admin (192.168.110.119:5037) - Bỏ qua cụm` thay vì in `Đã hoàn tất: 0, Lỗi (0)` gây hiểu lầm farm bị phá hoặc sập.

---

## 4. Triage Checklist Nhanh O(1)
- [ ] Ping / SSH kiểm tra sống còn: `python D:/Taadaa/tools/admin_ssh.py "hostname"` (< 1s).
- [ ] Kiểm tra tiến trình ADB trên Admin: `python D:/Taadaa/tools/admin_ssh.py "tasklist /FI \"IMAGENAME eq adb.exe\""`.
- [ ] Kiểm tra thiết bị thực tế qua SSH nội bộ: `python D:/Taadaa/tools/admin_ssh.py "python D:/Taadaa/tools/inspect_machine.py"`.
- [ ] Tuyệt đối cấm kết luận đứt cáp / loopback nếu chưa đối chiếu log chạy của các ca liền kề trong cùng ngày.
