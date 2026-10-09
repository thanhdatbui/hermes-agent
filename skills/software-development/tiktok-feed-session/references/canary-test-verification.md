# Hướng dẫn Kiểm tra & Xác nhận Kết quả Canary Test B4 (tiktok-luot nuoi acc)

## 1. Lệnh Thực thi Chuẩn B4
Khi chạy Canary Test trên một máy (ví dụ Máy N):
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```
*Lưu ý:*
- Bắt buộc dùng `powershell.exe -ExecutionPolicy Bypass`.
- Timeout tối thiểu 600s trên công cụ terminal.
- Tuyệt đối không can thiệp bằng ADB tay (`adb shell input`) trong quá trình canary chạy.

## 2. Đường dẫn Artifacts & Quy tắc Đọc Kết Quả (Zero-Disk-Scan)
Lệnh hoàn tất sẽ in ra đường dẫn artifact ở dòng cuối:
```text
Status: success
Artifacts: D:\Taadaa\tiktok-luot nuoi acc\.ai-runs\<TIMESTAMP>
```

### Các file cần đọc trực tiếp (CẤM quét đĩa, CẤM os.walk):
1. **Tổng hợp cấp batch:**
   `D:\Taadaa\tiktok-luot nuoi acc\.ai-runs\<TIMESTAMP>\summary.txt`
   - Kiểm tra `multi_machine_summary`: `final_status` (`success` / `failed`), `swipes_completed`.
2. **Chi tiết cấp thiết bị:**
   `D:\Taadaa\tiktok-luot nuoi acc\.ai-runs\<TIMESTAMP>\machines\machine_<N>\<TIMESTAMP>\summary.txt`
   - Kiểm tra:
     + `total_swipes_completed`: Đạt đủ số swipe yêu cầu (thường là 2).
     + `safety_summary`: Toàn bộ các bước chuyển màn hình đạt `safety_status: ok`.
     + `feed_session_summary`: Trạng thái các bước baseline, profile_preflight, swipe, verify_profile.
     + `popup_summary`: Kiểm tra xem có popup nào xuất hiện và được dismiss hay không (ví dụ popup AI info, shop cta, voucher...).
     + `cleanup_close_all`: Trạng thái dọn dẹp app sau phiên.

## 3. Pitfall Cần Tránh Tuyệt Đối
- **Không dùng `os.walk` hay `search_files` đệ quy** trên thư mục `.ai-runs` hay toàn bộ repo `D:\Taadaa\...`: Việc quét đệ quy hàng ngàn artifact/ảnh chụp sẽ gây timeout 900s.
- **Đọc trúng đích:** Luôn lấy chuỗi timestamp từ stdout của lệnh chạy rồi đọc trực tiếp file `summary.txt` bằng `read_file` theo đường dẫn tuyệt đối.
