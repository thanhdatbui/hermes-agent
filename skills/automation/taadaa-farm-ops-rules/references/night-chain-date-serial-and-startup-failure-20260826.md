# Night Chained Pipeline Failure Analysis: Date Serial & Gmail Preflight Startup (2026-08-26)

## 1. Cơ chế lỗi Device ID bị ghi đè bằng ngày tháng
- File nguồn `taikhoan_run_safe.xlsx` có nhiều dòng trên 1 máy. Khi một dòng có giá trị `23/08/2026` hoặc `2026-08-24` ở cột Device ID:
- Hàm loader đọc từ trên xuống dưới $\rightarrow$ dòng lỗi ở dưới cùng sẽ ghi đè serial thật $\rightarrow$ ADB command fail `device not found`.
- **Khắc phục:** Filter bỏ định dạng ngày tháng khi đọc cột `Device ID` và dùng `set` để gom serial duy nhất cho từng máy.

## 2. Cơ chế lỗi `[BLOCKED][PRE_GMAIL][APP_STARTUP]` hàng loạt
- Hàm `prepare_app_for_automation` kiểm tra foreground strict bằng `mCurrentFocus`.
- Trên Samsung S7/Android 7, mở app Gmail bị lag/delay vượt quá 10 lần retry (15s) $\rightarrow$ core báo startup failed $\rightarrow$ batch Gmail bị stop 10/15 máy.
