# OmniRoute Build Incomplete & Next.js Watchdog Crash Flapping Incident (2026-11-02)

## 1. Bản Chất Sự Cố
- **Hiện tượng:** Cổng `20129` (OmniRoute) sập liên tục, trả về `HTTP Connection Refused` hoặc crash lặp lại mỗi ~65 giây. Watchdog PowerShell (`omniroute_watchdog.ps1`) kích hoạt restart liên tục và nhanh chóng chạm trần restart limit (`MaxRestartsInWindow`), làm hệ thống rơi vào trạng thái tê liệt.
- **Nguyên nhân gốc rễ (Root Cause):**
  1. **Lệnh build bị timeout ngắt ngang:** Khi chạy `npm run build` hoặc `npm run build:backend` với timeout quá ngắn (ví dụ 60s), trình biên dịch Next.js 16 đã kịp dọn dẹp/xóa thư mục build cũ nhưng chưa kịp hoàn tất việc sinh file `BUILD_ID` trong thư mục `.build/next/`.
  2. **Vội vàng kill tiến trình khi build chưa verify:** Sau khi lệnh build bị ngắt (Exit 124 timeout), Coordinator vội vàng gửi tín hiệu terminate tiến trình Node.js đang chạy trên cổng 20129.
  3. **Lỗ hổng logic trong Watchdog cũ:** Script watchdog khởi động `next start` mà không hề kiểm tra tính toàn vẹn của thư mục build. Khi thiếu `BUILD_ID`, lệnh `next start` lập tức văng exit code 1. Watchdog tiếp tục khởi động lại vô tội vạ, làm cạn kiệt hạn ngạch restart và gây crash loop.

---

## 2. Giải Pháp Khắc Phục Chuẩn Xác (Đã Kiểm Chứng Bởi Claude)

### A. Tái tạo Artifact Build Hoàn Chỉnh
Bắt buộc chạy build đầy đủ với timeout dài (hoặc background process) và kiểm tra sự tồn tại của `BUILD_ID`:
```bash
npm run build
# Kiểm tra sự tồn tại của file BUILD_ID
test -f C:/Users/Kibe/OmniRoute/.build/next/BUILD_ID && echo "Build OK"
```

### B. Chốt Chặn An Toàn Cho Watchdog (Guard Against Broken Build)
Bổ sung kiểm tra điều kiện tiên quyết trong hàm `Start-OmniRoute` ở cả file runtime (`AppData/Roaming/omniroute/omniroute_watchdog.ps1`) và repo (`scripts/ops/omniroute_watchdog.ps1`):
```powershell
$BuildIdPath = Join-Path $AppDir ".build\next\BUILD_ID"
if (-not (Test-Path $BuildIdPath)) {
    Write-Log "build_missing: Cannot start OmniRoute because BUILD_ID is missing at $BuildIdPath. Run npm run build first. Skipping restart."
    return
}
```
* **Tác dụng:** Nếu build bị lỗi hoặc dở dang, watchdog sẽ **từ chối restart** để không làm tốn quota restart và không gây crash flapping, giữ nguyên trạng thái để chờ khắc phục build.

---

## 3. Quy Tắc Vận Hành Bắt Buộc (Invariants)
1. **CẤM TUYỆT ĐỐI kill tiến trình runtime trước khi build xong:** Khi cập nhật code backend/frontend của gateway hoặc router, chỉ được phép reload/restart tiến trình SAU KHI lệnh build đã trả về exit code 0 và file `BUILD_ID` đã hiện diện trên đĩa.
2. **Timeout build phải đủ rộng:** Lệnh build Next.js trên Windows cần tối thiểu 180s - 300s, không bao giờ chạy build với timeout 60s ở foreground.
