# Cạm Bẫy extract_local_files: Tự Động Upload Media Từ Đường Dẫn Thô Trên Đĩa (Auto-Delivery Trap)

## 1. Hiện tượng & Triệu chứng thực tế (Sự cố 06/09/2026)
- **Triệu chứng:** Sau khi kết thúc phiên fix lỗi máy 39, agent gửi tin nhắn chốt phiên:
  `...đăng thành công video 5 (D:\TIKTOK-videonuoinick\306\5.mp4)...`
  Ngay lập tức, Telegram bot của Hermes tự động upload một file video `5.mp4` dung lượng 3.94 MB lên nhóm/chat cá nhân.
- **Thắc mắc gay gắt từ người dùng:**
  *"ủa gửi video t chi v, hàm nào gọi lệnh gửi video v, tự nhiên tốn đống quota? hay gửi video k tốn quota nhiều"*
  *"Tại sao lại đi gửi video trong kho nuôi nick?"*

---

## 2. Cơ chế kỹ thuật gốc trong Hermes Gateway

Vấn đề xuất phát từ cơ chế **Auto-detect bare local file paths** của Hermes Gateway (tập tin `gateway/platforms/base.py`):

1. **Hàm `extract_local_files(content: str)` (dòng ~3753):**
   - Gateway dùng regex quét toàn bộ nội dung tin nhắn bot sinh ra để tìm các đường dẫn tuyệt đối (hoặc home `~/`) kết thúc bằng các đuôi media:
     `_VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.3gp'}`
     `_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}`
     và các file tài liệu (`.pdf`, `.csv`, `.xlsx`, `.zip`...).
   - Với mỗi chuỗi khớp regex, Gateway kiểm tra `os.path.isfile(expanded)`.
   - Nếu file **thực sự tồn tại trên ổ cứng của máy host**, Gateway sẽ bốc file đó vào danh sách `local_files` và xóa chuỗi đường dẫn đó khỏi phần văn bản.

2. **Hàm gửi tin `send_video()` / `send_multiple_images()` (dòng ~5170):**
   - Với các file trong `local_files`, nếu đuôi thuộc `_VIDEO_EXTS`, Gateway tự động gọi:
     ```python
     await self.send_video(chat_id=event.source.chat_id, video_path=file_path, metadata=...)
     ```
   - Bot gọi Telegram API `sendVideo` trực tiếp để tải file lên Telegram của user.

---

## 3. Giải đáp về Quota LLM vs Băng thông mạng

- **Quota LLM = 0 token:**
  - Quá trình này diễn ra hoàn toàn ở tầng Transport/Gateway của Python sau khi LLM đã hoàn tất sinh text.
  - Không có bất kỳ model AI nào được gọi hay tốn token nào cho việc upload video.
- **Băng thông Internet = Dung lượng file:**
  - Máy host phải tốn băng thông upload đúng bằng dung lượng file trên đĩa (ví dụ video `5.mp4` là 3.94 MB / 4,129,602 bytes).
  - Gây chậm trễ tin nhắn và làm phiền / spam khung chat của người dùng.

---

## 4. Giải pháp Khóa Cứng 3 Tầng (Tư vấn bởi Claude CLI)

### Tầng 1: Config Layer (`config.yaml`)
Tắt tính năng tự động trích xuất bare path, chỉ gửi file khi có cú pháp explicit `MEDIA:<path>`:
```yaml
gateway:
  media_delivery:
    auto_deliver_local_files: false
    denied_paths:
      - "D:/TIKTOK-videonuoinick"
      - "D:/video goc"
      - "D:/OneDrive"
```

### Tầng 2: Denylist Layer (`gateway/platforms/base.py`)
Trong `_media_delivery_denied_paths()`, đưa các thư mục kho farm và cấu hình động từ `config.yaml` vào danh sách cấm tuyệt đối:
```python
    # Farm data repositories: cấm tuyệt đối auto-deliver hoặc media upload từ kho farm
    _FARM_DENIED_ROOTS = (
        "D:/TIKTOK-videonuoinick",
        "D:\\TIKTOK-videonuoinick",
        "D:/video goc",
        "D:\\video goc",
        "D:/video_goc",
        "D:\\video_goc",
        "D:/OneDrive",
        "D:\\OneDrive",
    )
    for farm_root in _FARM_DENIED_ROOTS:
        denied.append(Path(farm_root))

    try:
        from hermes_cli.config import load_config as _load_config
    except ImportError:
        try:
            from config import load_config as _load_config
        except ImportError:
            _load_config = None

    if _load_config:
        try:
            gw_cfg = _load_config().get("gateway", {})
            md_cfg = gw_cfg.get("media_delivery", {})
            for p in md_cfg.get("denied_paths", []):
                if p:
                    denied.append(Path(p))
        except Exception:
            pass
```
Bất kỳ file nào nằm dưới các thư mục này đều bị `validate_media_delivery_path()` từ chối (`return None`).

### Tầng 3: Extraction Guard Layer (`gateway/platforms/base.py`)
- Định nghĩa helper `_auto_deliver_local_files_enabled()` (dùng fallback import `hermes_cli.config` / `config`):
```python
def _auto_deliver_local_files_enabled() -> bool:
    """Return True if auto-detection of bare local file paths is enabled.

    Disabled when HERMES_AUTO_DELIVER_LOCAL_FILES=0/false or when
    gateway.media_delivery.auto_deliver_local_files is False in config.yaml.
    """
    env_val = os.environ.get("HERMES_AUTO_DELIVER_LOCAL_FILES", "").strip().lower()
    if env_val in ("0", "false", "no", "off"):
        return False
    try:
        from hermes_cli.config import load_config as _load_config
    except ImportError:
        try:
            from config import load_config as _load_config
        except ImportError:
            _load_config = None
    if _load_config:
        try:
            gw = _load_config().get("gateway", {})
            md = gw.get("media_delivery", {})
            if "auto_deliver_local_files" in md:
                return bool(md["auto_deliver_local_files"])
            if "auto_deliver_local_files" in gw:
                return bool(gw["auto_deliver_local_files"])
        except Exception:
            pass
    return True
```
- Trong `extract_local_files(content: str)`: kiểm tra `_path_under_denied_prefix(Path(expanded).resolve())`, nếu thuộc denylist thì `continue` bỏ qua, không bốc vào danh sách gửi và không xóa chuỗi đó khỏi text:
```python
            if os.path.isfile(expanded):
                try:
                    if _path_under_denied_prefix(Path(expanded).resolve()):
                        continue
                except Exception:
                    pass
                found.append((raw, expanded))
```
- Tại vị trí dispatch message (dòng ~4980): kiểm tra `_auto_deliver_local_files_enabled()`, nếu `false` thì bỏ qua toàn bộ bước gọi `extract_local_files`:
```python
                local_files = []
                if not is_ephemeral_response and _auto_deliver_local_files_enabled():
                    local_files, text_content = self.extract_local_files(text_content)
                    local_files = self.filter_local_delivery_paths(local_files)
                    if local_files:
                        logger.info("[%s] extract_local_files found %d file(s) in response", self.name, len(local_files))
```

### ⚠️ Pitfall: Đồng bộ Dual-Runtime trên Windows & Fallback Import
1. **Đồng bộ Dual-Runtime:** Khi sửa `base.py`, trên Windows Gateway có thể import trực tiếp từ virtual environment `site-packages` thay vì source tree. BẮT BUỘC đồng bộ cả 2 đường dẫn:
   - Source: `%LOCALAPPDATA%\hermes\hermes-agent\gateway\platforms\base.py`
   - Venv: `%LOCALAPPDATA%\hermes\hermes-agent\venv\Lib\site-packages\gateway\platforms\base.py`
2. **Pitfall Import `load_config`:** Không dùng đơn thuần `from config import load_config`. Nếu file chạy độc lập hoặc môi trường không có module `config` ở root, `ModuleNotFoundError` sẽ bị khối `except Exception: pass` nuốt mất và trả về giá trị mặc định `True`, làm vô hiệu hóa cài đặt `auto_deliver_local_files: false`. Phải dùng cấu trúc fallback:
   ```python
   try:
       from config import load_config
   except ImportError:
       from hermes_cli.config import load_config
   ```

### 4 Tiêu Chí Verification Test Độc Lập
Chạy script kiểm tra với Python venv của Hermes:
```python
import sys
sys.path.insert(0, 'C:/Users/Kibe/AppData/Local/hermes/hermes-agent')
from gateway.platforms.base import (
    validate_media_delivery_path,
    BasePlatformAdapter,
    _auto_deliver_local_files_enabled,
)

assert _auto_deliver_local_files_enabled() is False, "Auto deliver must be False"
assert validate_media_delivery_path('D:/TIKTOK-videonuoinick/306/5.mp4') is None, "Farm video must be None"
assert validate_media_delivery_path('C:/Users/Kibe/m39_final_proof.png') is not None, "Screenshot must be allowed"

text = "Video at D:/TIKTOK-videonuoinick/306/5.mp4 is ready"
files, cleaned = BasePlatformAdapter.extract_local_files(text)
assert len(files) == 0, f"Farm video must not be extracted! got {files}"
assert "D:/TIKTOK-videonuoinick/306/5.mp4" in cleaned, "Text must not be stripped"
print("ALL VERIFICATION CHECKS PASSED 100%!")
```

---

## 5. Kỷ luật Bắt Buộc Khi Báo Cáo (Prompt & Agent Discipline)

1. **BẮT BUỘC BỌC DẤU BACKTICK:**
   - Mọi đường dẫn file media kết thúc bằng `.mp4`, `.mov`, `.png`, `.jpg`, `.jpeg`, `.pdf`, `.zip`... khi nhắc tới trong câu trả lời **BẮT BUỘC PHẢI BỌC TRONG DẤU BACKTICK INLINE (`...`) HOẶC FENCED CODE BLOCK (```...```)**.
   - Khi nằm trong backtick, regex của Gateway tự động bỏ qua nhờ span exclusion.
   - **Ví dụ SAI (Bị trigger tự động gửi video/ảnh):**
     `Máy 39 đã đăng thành công video D:\TIKTOK-videonuoinick\306\5.mp4`
   - **Ví dụ ĐÚNG (An toàn, không bao giờ bị gửi nhầm):**
     `Máy 39 đã đăng thành công video \`D:\TIKTOK-videonuoinick\306\5.mp4\``
2. **CHỈ DÙNG `MEDIA:<path>` KHI CỐ Ý GỬI ARTIFACT:**
   - Chỉ khi nào người dùng yêu cầu gửi ảnh bằng chứng, video kiểm chứng hoặc cần xem screenshot hiện trường (`MEDIA:C:/Users/Kibe/m39_final_proof.png`) thì mới dùng cú pháp `MEDIA:<path>`.
