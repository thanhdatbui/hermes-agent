---
title: Machine Diagnostic Pattern - Direct Artifact Access (Hard Rule)
date: 2026-09-02
repo: tiktok-luot nuoi acc
status: ENFORCED
---

## Rule: CẤM TUYỆT ĐỐI dùng grep/find quét đệ quy để tra cứu lỗi máy

Khi có alert `[MÁY N]` từ Telegram/Farm Alerts:
- **SAI:** `grep -rn "pattern" "D:/Taadaa/tiktok-luot nuoi acc" "D:/Taadaa/automation-core"` hoặc quét `.ai-runs`
- **ĐÚNG:** Vào thẳng thư mục artifact của máy đó:

```
D:\Taadaa\runtime\kibe\live\<date>\row-<X>-<timestamp>\<run-id>\machines\machine_<N>\<run-id>\
```

### Files phải đọc trong artifact máy:
1. `summary.txt` — trạng thái cuối, final_status, stop_reason, chi tiết steps
2. `log.jsonl` — dòng cuối cho thấy error/chặn ở step nào
3. `artifacts/device_<serial>/account_<id>/feed-session-smoke/<step>/ui.xml` — XML màn hình tại thời điểm lỗi
4. `artifacts/.../screen.png` — screenshot để vision analyze nếu cần

### Pattern tra cứu chuẩn (Python):
```python
import os, glob

# Tìm artifact của máy N hôm nay
live_base = f'D:/Taadaa/runtime/kibe/live/{today_date}'
for row_dir in sorted(os.listdir(live_base), reverse=True):
    for run_dir in sorted(os.listdir(os.path.join(live_base, row_dir)), reverse=True):
        m_path = os.path.join(live_base, row_dir, run_dir, 'machines', f'machine_{machine_num}')
        if os.path.exists(m_path):
            # Đọc summary.txt trước
            summary = os.path.join(m_path, run_dir, 'summary.txt')
            if os.path.exists(summary):
                print(open(summary, encoding='utf-8').read())
            break
```

### Tại sao cấm grep đệ quy:
- `.ai-runs` chứa hàng nghìn folder, quét mất 30+ phút, treo terminal
- Repo code to lớn, grep trên toàn bộ trả kết quả rác
- Thông tin chính xác CHỈ ở artifact của MÁY ĐÓ LÚC ĐÓ

### Khi nào dùng grep:
- Tìm code fix trong repo (biết chính xác file/function)
- KHI ĐÃ XÁC ĐỊNH NGUYÊN NHÂN từ artifact rồi mới tìm chỗ sửa