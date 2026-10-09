# Sự Cố SQLite WAL Bloat Gây Lỗi "Session Storage Could Not Be Written" (06/10/2026)

## 1. Hiện tượng & Triệu chứng
Người dùng thấy bot dừng lượt và văng thông báo hệ thống:
```text
⚠️ No reply: the turn was stopped because session storage could not be written 
(the transcript would have been lost on restart). This is often a full disk — 
free some space (or fix state.db permissions), then send your message again.
```

## 2. Bản chất kỹ thuật & Nguyên nhân gốc
1. **Dung lượng Database:** File `C:\Users\Kibe\AppData\Local\hermes\state.db` đã tích tụ phình to lên tới **14 GB**.
2. **Kẹt WAL Lock:** File Write-Ahead Log `state.db-wal` bị kẹt lock trong các lượt ghi dồn dập (multi-session concurrency), SQLite không tự động hoàn thành passive checkpoint.
3. **Ảo giác Full Disk:** Mặc dù ổ C: vẫn còn dư ~22 GB, nhưng khi SQLite cố gắng mở transaction ghi mới trên file 14GB mà bị kẹt lock / timeout I/O, hệ thống runtime của Hermes bắt exception không ghi được transcript và đánh dấu nhầm thành lỗi "full disk / permission error".

## 3. Quy trình khắc phục tức thì O(1)
Chạy lệnh Python SQLite mở kết nối timeout cao và ép thu nhỏ WAL:
```python
import sqlite3
conn = sqlite3.connect(r'C:\Users\Kibe\AppData\Local\hermes\state.db', timeout=30.0)
res = conn.execute('PRAGMA wal_checkpoint(TRUNCATE);').fetchall()
print('WAL truncate result:', res)  # Kết quả mong đợi: [(0, 0, 0)]
conn.close()
```
Lệnh `TRUNCATE` sẽ ép ghi toàn bộ frame từ WAL vào database chính và thu nhỏ kích thước file WAL về 0 byte ngay lập tức, giải phóng hoàn toàn khóa I/O cho Hermes Gateway.
