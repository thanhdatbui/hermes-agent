# Consumer CLI Parser Contract & Isolation Pattern

## 1. Vấn Đề (Problem Statement)
Trong các consumer scripts (như `run_post.py` trong `Tiktok-video`, hoặc các runner trong `tiktok-luot nuoi acc`), việc cấu hình đối số dòng lệnh (CLI arguments) gặp 2 rủi ro phổ biến:
1. **Thiếu CLI Argument được truyền từ Orchestrator:** Khi caller (ví dụ `multi_machine_feed_session`) truyền thêm flags (như `--video-source-root`, `--allow-device-reboot-recovery`), nếu parser consumer chưa khai báo, argparse có thể gán nhầm vào positional arguments (như `command`) hoặc văng lỗi unrecognized arguments.
2. **Inline ArgumentParser trong `main()`:** Khai báo toàn bộ parser bên trong `def main():` khiến việc viết unit test độc lập (focused pytest) cho CLI args trở nên khó khăn và dễ gây side-effects khi test phải import/mock `sys.argv` và `main()`.

## 2. Quy Tắc Chuẩn (Contract Invariants)
### 2.1. Tách Biệt `build_parser()`
Luôn tách việc dựng `argparse.ArgumentParser` thành hàm riêng:
```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(...)
    parser.add_argument("--config", required=True, help="Path to config file")
    parser.add_argument("--workflow-workbook", help="Override config workflow_workbook")
    parser.add_argument("--video-source-root", help="Override video source root directory")
    ...
    return parser

def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    ...
```

### 2.2. Kiểm Tra CLI Arguments qua Focused Tests
Khi cập nhật hoặc sửa parser, tạo test độc lập kiểm tra trực tiếp qua `build_parser().parse_args(...)`:
- Kiểm tra các cờ override (`--video-source-root`, `--workflow-workbook`) parse đúng giá trị string.
- Đảm bảo các positional args hoặc `command` không bị gán nhầm (`args.command is None`).
- Kiểm tra validation logic (báo lỗi stderr và return code 1 nếu giá trị override rỗng/blank).
