# Hermes Runtime Script Path Resilience & GPMClient Import Fallback

## Bối cảnh & Vấn đề
Khi các script tự động hóa trong `D:\Taadaa\GPM auto\scripts\` (ví dụ `sync_gpm_lifecycle.py`) được triển khai hoặc sao chép sang thư mục scripts của Hermes runtime:
`C:\Users\Kibe\AppData\Local\hermes\scripts\`

Các lệnh import đường dẫn tương đối dạng:
```python
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
```
sẽ giải quyết đường dẫn thành `C:\Users\Kibe\AppData\Local\hermes\src` (không tồn tại).
Hậu quả:
- Khối `try ... except ImportError:` bắt lỗi và gán `GPMClient = None`.
- Khi script thực thi hàm nghiệp vụ (ví dụ `client = GPMClient(base_url=...)`), Python ném lỗi:
  `TypeError: 'NoneType' object is not callable`
  khiến tiến trình crash hoặc dừng đồng bộ.

## Quy tắc giải quyết chuẩn

### 1. Luôn khai báo đường dẫn tuyệt đối fallback
Khi định nghĩa `sys.path`, kết hợp cả đường dẫn tương đối theo repo và đường dẫn tuyệt đối cố định đến source repo:
```python
# Tương đối (khi chạy trực tiếp trong D:\Taadaa\GPM auto\scripts)
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Tuyệt đối (khi chạy từ %LOCALAPPDATA%\hermes\scripts hoặc workspace khác)
GPM_AUTO_SRC = Path(r"D:\Taadaa\GPM auto\src")
if GPM_AUTO_SRC.exists() and str(GPM_AUTO_SRC) not in sys.path:
    sys.path.insert(0, str(GPM_AUTO_SRC))
```

### 2. Guard kiểm tra None trước khi gọi constructor
Không để exception `TypeError` nổ không kiểm soát:
```python
def sync_lifecycle_gpm():
    logger.info("Bắt đầu đồng bộ lifecycle GPM...")
    if GPMClient is None:
        logger.error("GPMClient is None, cannot proceed")
        return
    ...
```

### 3. Quy trình deploy và verify
1. Sửa trên repo gốc: `D:\Taadaa\GPM auto\scripts\<script>.py`.
2. Đồng bộ sang runtime: `C:\Users\Kibe\AppData\Local\hermes\scripts\<script>.py`.
3. Chạy kiểm thử từ chính thư mục runtime:
   `python "C:\Users\Kibe\AppData\Local\hermes\scripts\<script>.py" --dry-run`
4. Commit và push git trên repo gốc `D:\Taadaa\GPM auto`.
