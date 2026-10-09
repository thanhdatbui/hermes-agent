# Quy Chuẩn Canary Test B4 (tiktok-luot nuoi acc) & Đọc Kết Quả Trực Tiếp (2026-09-06)

## 1. Mục Đích & Lệnh Chạy B4
Sau khi patch code xử lý lỗi kẹt trên farm nuôi acc (`tiktok-luot nuoi acc`), Coordinator hoặc Worker thực thi bước **B4 (Canary Test)** để kiểm chứng trực tiếp trên đúng thiết bị vừa gặp sự cố mà không can thiệp ADB tay:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```

### Các cờ bắt buộc:
- `-Machines <N>`: Giới hạn duy nhất máy cần test kiểm chứng.
- `-Row 1`: Chạy slot row chỉ định (mặc định Row 1 hoặc Row bị dừng).
- `-RecoveryTestSwipes 2`: Giới hạn 2 lượt vuốt kiểm tra (nhanh, nhẹ, an toàn).
- `-SkipAccountWorkbookSync`: Bỏ qua sync workbook để không làm lệch cursor hay chậm tiến trình.
- `-Run`: Thực thi thật (bỏ qua dry-run/preview).
- Cài đặt timeout terminal $\ge 600\text{s}$.

## 2. Quy Tắc Bóc Tách Kết Quả & Zero-Disk-Scan (BẮT BUỘC)
Khi lệnh hoàn thành, runner in ra đường dẫn artifact ở dòng cuối cùng:
```text
Status: success
Artifacts: D:\Taadaa\tiktok-luot nuoi acc\.ai-runs\<TIMESTAMP>
```

### 🛑 PITFALL CHẾT NGƯỜI: CẤM QUÉT ĐĨA RỘNG
- **Tuyệt đối CẤM** dùng `os.walk`, `glob(recursive=True)`, `search_files` đệ quy hoặc grep trên `D:\Taadaa\tiktok-luot nuoi acc\.ai-runs` hay codebase `automation-core`.
- Thư mục `.ai-runs` chứa hàng nghìn thư mục con, ảnh chụp screencap PNG và XML dung lượng lớn. Quét đệ quy sẽ gây **Command timed out (>900s)** làm hỏng phiên và treo coordinator.

### ✅ Cách Đọc Trúng Đích Tức Thì (O(1)):
Trích xuất đường dẫn timestamp từ stdout và đọc trực tiếp 2 file summary:

1. **Tổng hợp đa máy:**
   `D:\Taadaa\tiktok-luot nuoi acc\.ai-runs\<TIMESTAMP>\summary.txt`
   - Đọc bảng `multi_machine_summary`: Xác nhận `final_status == "success"`, `swipes_completed == 2`.
   - Đọc `blocker_taxonomy_summary`: Xác nhận category là `pass/degraded acceptable` (`count: 1`).

2. **Chi tiết từng bước trên máy `<N>`:**
   `D:\Taadaa\tiktok-luot nuoi acc\.ai-runs\<TIMESTAMP>\machines\machine_<N>\<TIMESTAMP>\summary.txt`
   - `safety_summary`: Kiểm tra các step `baseline`, `profile_preflight`, `before_swipe`, `swipe_1_after`, `swipe_2_after`, `verify_profile` đều có `safety_status: ok`.
   - `popup_summary`: Kiểm tra xem popup mục tiêu (ví dụ "Thông tin về AI", "shop cta", "voucher"...) có xuất hiện và được dismiss đúng quy chuẩn hay không.
   - `watch_delay_summary`: Kiểm tra thời gian xem trước khi vuốt (3–10s), thời lượng vuốt (300–450ms) và jitter (30px).
   - `cleanup_close_all`: Xác nhận app được dọn dẹp đóng an toàn sau phiên (`cleanup_close_all_result: success`).
