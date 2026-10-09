# Recovery Scope Lock & Test Lock Rules

## 1. SCOPE LOCK (Chống Sửa Lan Man)
- **Lỗi ở đâu sửa đúng ở đó:**
  - Nếu nguyên nhân gốc nằm ở tầng detector, XML parsing, device lock $\rightarrow$ Sửa tại `automation-core`.
  - Nếu nguyên nhân ở logic runner, retry, navigation $\rightarrow$ Sửa tại file flow của consumer repo (`tiktok-luot nuoi acc`).
- **CẤM TUYỆT ĐỐI sửa lan man / tiện tay refactor dạo:** Đang fix lỗi của máy thì không được tiện tay sửa sang `watchdog`, `cron`, `classifier` hay các tính năng không liên quan làm phình diff và gây Plan-Review REJECT.

## 2. TEST LOCK (Chống Timeout Test Toàn Repo)
- **CẤM TUYỆT ĐỐI:** Không chạy lệnh bare `pytest` quét toàn bộ monorepo (2000+ tests dính timeout 900s / 15 phút).
- **BẮT BUỘC:** CHỈ chạy focused tests (`pytest <test_file> -k <test_name>`) cho đúng file vừa sửa.
- **Thời gian chạy test:** Đảm bảo test hoàn tất dưới 2 phút.
