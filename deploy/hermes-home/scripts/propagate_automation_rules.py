import os
import sys
import time
import hashlib
import shutil
import subprocess
from pathlib import Path

targets = [
    r'D:\Taadaa\automation-core\AGENTS.md',
    r'D:\Taadaa\tiktok-luot nuoi acc\AGENTS.md',
    r'D:\Taadaa\tiktok-luot nuoi acc\PROJECT_RULES.md',
    r'D:\Taadaa\tiktok-follow\AGENTS.md',
    r'D:\Taadaa\tiktok-follow\PROJECT_RULES.md',
    r'D:\Taadaa\tiktok-log-in\AGENTS.md',
    r'D:\Taadaa\tiktok-log-in\PROJECT_RULES.md',
    r'D:\Taadaa\Tiktok-video\AGENTS.md',
    r'D:\Taadaa\Tiktok-video\PROJECT_RULES.md',
    r'D:\Taadaa\Tiktok_Reg\AGENTS.md',
    r'D:\Taadaa\Tiktok_Reg\PROJECT_RULES.md',
    r'D:\Taadaa\tiktok-add-bao-mat-f2a\AGENTS.md',
    r'D:\Taadaa\tiktok-add-bao-mat-f2a\PROJECT_RULES.md',
    r'D:\Taadaa\Hotmail\AGENTS.md',
    r'D:\Taadaa\Hotmail\PROJECT_RULES.md',
    r'D:\Taadaa\register gmail\AGENTS.md',
    r'D:\Taadaa\register gmail\PROJECT_RULES.md',
    r'D:\Taadaa\gan-proxy\AGENTS.md',
    r'D:\Taadaa\gan-proxy\PROJECT_RULES.md',
    r'D:\Taadaa\GPM auto\AGENTS.md',
    r'D:\Taadaa\GPM auto\PROJECT_RULES.md',
]

ts = time.strftime('%Y%m%d_%H%M%S')
backup_dir = Path(r'C:\Users\Kibe\AppData\Local\hermes\backups') / f'rule-merge-automation-{ts}'
backup_dir.mkdir(parents=True, exist_ok=True)

BLOCK_TEXT = """## Quy Tắc Định Tuyến Log Theo Máy & Chống Timeout Khi Điều Tra Lỗi (Bắt buộc)

- **Định tuyến log O(1) từ Alert Banner [MAY N]:**
  Khi nhận ảnh/screenshot hoặc thông báo có thanh đỏ `[MAY <N>]` (hoặc nêu đích danh Máy N):
  1. Tra ngay Serial của máy từ `D:\\Taadaa\\machine-config\\kibe.yaml` theo số máy `<N>`.
  2. Truy cập THẲNG vào thư mục log/artifact riêng của máy đó:
     - `D:\\Taadaa\\runtime\\kibe\\live\\<ngày>\\*\\machines\\machine_<N>\\`
     - `D:\\Taadaa\\runtime\\kibe\\artifacts\\alert_machine_<N>.png`
     - Lấy XML/screenshot hiện trường trực tiếp: `adb -s <serial> ...`
  3. **TUYỆT ĐỐI CẤM** chạy lệnh tìm kiếm quét mù đệ quy (`grep -rn`, `find`) trên toàn bộ thư mục `.ai-runs/` hoặc `D:\\Taadaa\\runtime\\` gây tắc nghẽn I/O và treo timeout 900s.

- **Quy Tắc Timeout & Focused Test:**
  - Khi test code/fix bug, **CHỈ chạy focused test** theo đúng file/class/chức năng vừa sửa (thời gian chạy < 30s).
  - **CẤM chạy full test suite** toàn repo (hàng nghìn test) trong các lượt debug hoặc chốt phiên gây nghẽn tiến trình.
  - Các lệnh terminal dài phải đặt timeout hợp lý (30-60s) để fail-fast, không để lệnh treo quá 120s.
"""

results = []

for t_str in targets:
    p = Path(t_str)
    if not p.exists():
        results.append((t_str, 'NOT_FOUND', 0, False))
        continue
    
    # Backup
    rel_name = p.relative_to(Path(r'D:\Taadaa')).as_posix().replace('/', '__')
    bak_path = backup_dir / f'{rel_name}.bak'
    raw_data = p.read_bytes()
    bak_path.write_bytes(raw_data)
    
    # Check if already present
    if 'Quy Tắc Định Tuyến Log Theo Máy' in raw_data.decode('utf-8', errors='ignore'):
        results.append((t_str, 'ALREADY_PRESENT', len(raw_data), True))
        continue

    # Determine EOL
    crlf_count = raw_data.count(b'\r\n')
    lf_count = raw_data.count(b'\n') - crlf_count
    eol = b'\r\n' if crlf_count >= lf_count else b'\n'
    
    # Format block
    block_lines = BLOCK_TEXT.strip().split('\n')
    block_bytes = eol.join(line.encode('utf-8') for line in block_lines) + eol
    
    # Ensure separator
    if raw_data.endswith(b'\r\n\r\n') or raw_data.endswith(b'\n\n'):
        to_append = block_bytes
    elif raw_data.endswith(b'\r\n') or raw_data.endswith(b'\n'):
        to_append = eol + block_bytes
    else:
        to_append = eol + eol + block_bytes
        
    new_data = raw_data + to_append
    
    # Clear readonly if any
    try:
        subprocess.run(['attrib', '-R', '-H', str(p)], capture_output=True, check=False)
    except Exception:
        pass
        
    p.write_bytes(new_data)
    
    # Verify
    verify_data = p.read_bytes()
    ok = verify_data.startswith(raw_data) and verify_data.endswith(block_bytes)
    results.append((t_str, 'APPENDED', len(verify_data), ok))

print(f'Backup directory: {backup_dir}')
for t, status, size, ok in results:
    print(f'[{status}] (verified={ok}) {t}')
