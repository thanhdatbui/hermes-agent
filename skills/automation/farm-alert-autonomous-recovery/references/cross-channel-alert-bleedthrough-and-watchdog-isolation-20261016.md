# Cross-Channel Alert Bleed-Through & Watchdog Isolation Protocol (2026-10-16)

## 1. Bản chất sự cố (Root Cause & Anti-Regression)
Khi hệ thống có nhiều luồng nghiệp vụ chạy song song trên cùng một batch (Feed, Follow, Upload):
- Người dùng đã quy định rõ phân tách độc lập 3 kênh báo cáo:
  1. `tiktok luot nuoi acc` (`-5377611430`): Chỉ nhận báo cáo Lướt Feed.
  2. `tiktok follow` (`-5127276494`): Chỉ nhận báo cáo và Farm Alert của Follow chéo.
  3. `tiktok video` (`-5435853713`): Chỉ nhận báo cáo và Farm Alert của Đăng Video.

- **Điểm mù tai hại**: Trong script điều phối chung (`feed_session_watchdog.py`), nhánh chạy của Feed (`mode == "feed"`) lại tính gộp lỗi Follow (`tot_fl_err`) và Upload (`tot_up_err`). Khi Follow chéo lỗi hàng loạt ($\ge 8$ máy), script Feed tự động đổi header thành:
  `🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT HÀNG LOẠT (X máy lỗi script Follow) - {win['name']} (Row {active_row})`
  và bắn thẳng vào nhóm nuôi acc (`tiktok luot nuoi acc`), phá vỡ hoàn toàn nguyên tắc phân luồng kênh đã cam kết.

## 2. Invariants bắt buộc tuân thủ
1. **Zero Cross-Channel Alert Bleed-Through**:
   - Header `🚨 [FARM ALERT]` của một kênh CHỈ ĐƯỢC PHÉP phản ánh lỗi thuộc phạm vi quản lý của kênh đó.
   - Tuyệt đối cấm dùng biến đếm lỗi của Follow (`tot_fl_err`) hoặc Upload (`tot_up_err`) để gán alert cho tin nhắn Lướt Feed.
2. **Kênh chuyên trách (Dedicated Cronjobs)**:
   - Nghiệp vụ Follow chéo có script riêng `follow_session_watchdog.py` chạy độc lập, gửi trực tiếp về `-5127276494`. Không để script Feed "gánh hộ" việc bắn Farm Alert của Follow.
3. **Fail-Safe Modularization**:
   - Khi bóc tách monolith script thành package module, bắt buộc thêm `sys.path.insert(0, scripts_dir)` động để tránh lỗi `ModuleNotFoundError` khi cronjob kích hoạt từ thư mục ngoài.
