# Canary & Cohort Troubleshooting Reference

## 1. Lưu ý khi chạy Canary đơn máy (Single Machine Canary)
- **Lỗi `cohort artifact and assignment manifest are both required for a live cohort child`**:
  - Xảy ra khi môi trường đang set sẵn `TIKTOK_FEED_ASSIGNMENT_MANIFEST` hoặc `TIKTOK_FEED_WORKER_ID`, nhưng lệnh chạy `run-feed-session.ps1` không truyền `-CohortArtifact`.
  - **Khắc phục**: Khi chạy canary độc lập để verify 1 máy / 1 row, thêm tham số `-LocalRun` để bypass cohort assignment gate.
  - Lệnh chuẩn:
    ```powershell
    powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row <row> -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -LocalRun -Run
    ```

## 2. Đối soát Nick và Row trước khi chạy Canary
- Bắt buộc kiểm tra nick được báo trong Alert tương ứng với Row nào trong `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`.
- Ví dụ: Nick `buithudung2011` trên Máy 1 nằm ở **Row 5** (Ca 3), nếu chạy `-Row 1` sẽ kiểm tra nhầm nick `lipsellczaw`.

## 3. Điều tra Root Cause Alert Farm
- Khi cần điều tra log, manifest, state sâu của hệ thống cron, chủ động dispatch subagent qua `delegate_task` để thực hiện điều tra song song, tránh xử lý tuần tự đơn lẻ gây chậm trễ.
