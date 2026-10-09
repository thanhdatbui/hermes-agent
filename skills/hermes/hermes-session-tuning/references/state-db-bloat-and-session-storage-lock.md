# Hermes state.db 14GB Bloat, VACUUM Disk Exhaustion Trap & SQLite Busy Timeout Error ("session storage could not be written")

## Triệu chứng lỗi (Incident 07/10/2026)
Hermes ngắt turn với thông báo:
> ⚠️ No reply: the turn was stopped because session storage could not be written (the transcript would have been lost on restart). This is often a full disk — free some space (or fix state.db permissions), then send your message again.

## Cơ chế phát sinh lỗi thật
1. **Không phải do hết ổ cứng ban đầu (Full disk false alarm)**: Ổ C còn ~18.3 GB, ổ D còn >900 GB.
2. **Kích thước `state.db` vượt ngưỡng an toàn**:
   - `C:\Users\Kibe\AppData\Local\hermes\state.db` phình lên tới **14.2 GB** (hơn 3.46 triệu pages).
   - Tích tụ hơn **1.236.582 tin nhắn**, **6.000 sessions**, cùng các bảng FTS5 và trigram index khổng lồ (`messages_fts_trigram_data`).
3. **SQLite Write Lock Contention**:
   - SQLite có mặc định `busy_timeout = 5000ms` (5 giây).
   - Khi Coordinator hoặc Worker hoàn thành một turn dài, thao tác ghi transcript mới vào bảng `messages` kích hoạt cập nhật các bảng chỉ mục FTS/trigram trên file 14GB.
   - Thao tác I/O trên file 14GB vượt quá 5000ms dẫn đến lỗi `sqlite3.OperationalError: database is locked`.
   - Core Hermes dừng khẩn cấp để tránh mất transcript trên restart.

## 🚨 Bẫy VACUUM Ăn Tràn Ổ C (Full Disk Thật từ Full Disk Giả)
Khi chạy lệnh nén tiêu chuẩn của Hermes:
```bash
hermes sessions optimize
```
- Lệnh này chạy FTS merge và gọi lệnh SQLite `VACUUM`.
- `VACUUM` mặc định cần tạo một file database tạm thời có kích thước tương đương file gốc (14.2 GB) ngay trên ổ đĩa chứa DB hoặc trong thư mục `%TEMP%` (đều nằm trên ổ C).
- Do ổ C chỉ còn ~18 GB, quá trình tạo bản sao tạm thời đã **nuốt sạch dung lượng còn lại xuống 0 byte**, gây lỗi:
  ```
  Error: optimization failed: database or disk is full
  ```
- File tạm bị kẹt trong `%TEMP%` và Exclusive Lock của VACUUM làm cho mọi turn chat gửi đến lúc đó đều bị dội ngược ra ngoài.

## Quy trình chẩn đoán O(1)
```python
import sqlite3, os
p = r'file:C:/Users/Kibe/AppData/Local/hermes/state.db?mode=ro'
conn = sqlite3.connect(p, uri=True, timeout=5)
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM messages;')
print('Total messages:', c.fetchone()[0])
c.execute('PRAGMA page_count;')
pc = c.fetchone()[0]
c.execute('PRAGMA page_size;')
ps = c.fetchone()[0]
print('Total DB size GB:', round(ps * pc / (1024**3), 2))
```

## Phương án giải quyết & Tối ưu hóa chuẩn hóa 3 bước

### Bước 1: Prune session cũ qua CLI Hermes (Background)
Dùng lệnh built-in để xóa session cũ và tin nhắn cũ mà không cần viết script tự chế:
```bash
hermes sessions prune --older-than 21d --include-archived --yes
```
*Kết quả thực tế*: Xóa 2.256 sessions, dọn sạch 450.217 tin nhắn cũ trong < 30 giây.

### Bước 2: VACUUM chuyển hướng sang ổ có dung lượng lớn (VACUUM INTO)
Khi ổ C không đủ 2x dung lượng DB gốc, **CẤM** chạy VACUUM tại chỗ. Dùng cú pháp `VACUUM INTO` xuất thẳng sang ổ D (còn >800 GB trống):
```python
import sqlite3
src = r'C:\Users\Kibe\AppData\Local\hermes\state.db'
dst = r'D:\Taadaa\hermes_state_compact.db'
conn = sqlite3.connect(src, timeout=30)
conn.execute('PRAGMA busy_timeout = 30000;')
conn.execute(f"VACUUM INTO '{dst}';")
conn.close()
```
*Kết quả thực tế*: Nén từ 13.5 GB xuống 10.4 GB (giảm 3.04 GB) mà hoàn toàn không chạm vào dung lượng ổ C.

### Bước 3: Dọn dẹp Temp và giải phóng Lock
Xóa các file tạm SQLite còn sót trong `%TEMP%` và checkpoint WAL:
```powershell
Get-ChildItem -Path $env:TEMP -Filter '*sqlite*' | Remove-Item -Force
Get-ChildItem -Path $env:TEMP -Filter '*vacuum*' | Remove-Item -Force
```
```python
import sqlite3
conn = sqlite3.connect(r'C:\Users\Kibe\AppData\Local\hermes\state.db', timeout=30)
conn.execute('PRAGMA wal_checkpoint(PASSIVE);')
conn.close()
```
Đưa dung lượng trống ổ C lên >21 GB và latency truy vấn SQLite về **0.003s**.
