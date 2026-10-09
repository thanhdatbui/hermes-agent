# Hermes Shell PYTHONPATH Isolation & Execution Rules for Feed Session

## Vấn đề
Khi chạy commands từ môi trường shell của Hermes Agent trên Windows:
Hermes session tự động inject `PYTHONPATH` trỏ vào virtual environment của chính Hermes:
`C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages`

Khi chạy script PowerShell (`run-feed-session.ps1`) hoặc trực tiếp Python farm (`D:\Taadaa\python-envs\automation\Scripts\python.exe`):
Nếu `PYTHONPATH` được kế thừa, Python sẽ ưu tiên nạp các package C-extension (như `PIL` / Pillow) từ venv của Hermes thay vì venv của farm.
Dẫn đến lỗi fatal ngay khi khởi động:
```text
ImportError: cannot import name '_imaging' from 'PIL' (C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages\PIL\__init__.py)
```

## Giải pháp bắt buộc
Luôn cô lập biến môi trường `PYTHONPATH` trước khi gọi PowerShell hoặc Python farm bằng `env -u PYTHONPATH` hoặc `unset PYTHONPATH`:

### 1. Chạy PowerShell runner:
```bash
env -u PYTHONPATH powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Python "D:\Taadaa\python-envs\automation\Scripts\python.exe" -Machines 5 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```

### 2. Chạy trực tiếp Python farm:
```bash
env -u PYTHONPATH "D:/Taadaa/python-envs/automation/Scripts/python.exe" python_runner/run_tiktok.py ...
```

## Cảnh báo quét đĩa và log
Repo `tiktok-luot nuoi acc` chứa thư mục `.ai-runs` với hàng ngàn screenshots và UI dumps nặng hàng chục GB.
- **CẤM TUYỆT ĐỐI** dùng `grep -rn` hoặc recursive search trên thư mục gốc repo hoặc `.ai-runs` vì sẽ gây timeout 900s và treo terminal.
- Để kiểm tra log sau khi chạy:
  Trỏ thẳng vào artifact folder mới nhất được in ra ở cuối summary:
  `D:\Taadaa\tiktok-luot nuoi acc\.ai-runs\<TIMESTAMP>\summary.txt`
  hoặc
  `D:\Taadaa\tiktok-luot nuoi acc\.ai-runs\<TIMESTAMP>\machines\machine_<N>\<TIMESTAMP>\log.jsonl`
