# Single-Machine Takeover & Minimal Reporting Protocol (2026-08-31)

## 1. Minimal Reporting Style
- Batch/Cron/Reg báo cáo theo format:
```
Success:
- Machine <STT>: <kết_quả>

Fail:
- Machine <STT>: <MÃ_LỖI>
```
- Không giải thích kỹ thuật dài dòng, không in log chi tiết trừ khi user yêu cầu.

## 2. Safe Single-Machine Takeover during Multi-Machine Runs
- Khi user chỉ định takeover 1 máy trong lúc phiên nuôi acc multi-machine đang chạy toàn dàn:
  * **CẤM kill PID parent của feed runner** (không dùng taskkill làm dừng toàn bộ các máy khác).
  * Chờ máy mục tiêu hoàn thành hoặc kiểm tra lock của máy đó (nếu đã xong hoặc ở trạng thái giữ hiện trường `blocked`/`handoff` với `owner_active: false`), nhả lock qua script chính thức:
    `python python_runner/scripts/release-device-lock.py --machine <STT> --serial <SERIAL>`
  * Sau khi nhả lock an toàn của đúng máy đó, chạy tác vụ riêng cho máy đó với device lock độc lập.

## 3. OneDrive Excel Conflict Handling
- Khi mở workbook trong `D:\OneDrive\...` bị báo "UPLOAD BLOCKED / Discard Changes":
  * Do Office Document Cache xung đột khi Python ghi đè file trên đĩa.
  * Bấm **`Discard Changes` -> `Yes`** để Excel xóa cache và đọc lại bản mới nhất từ ổ đĩa an toàn.
