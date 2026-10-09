# Chẩn đoán lỗi MANIFEST_IDENTITY_MISMATCH (TikTok Hermes-Cron)

## Hiện tượng
Cron `phase9-watcher-tiktok-feed` (job `7890172324ca`) hoặc runner báo lỗi:
```text
File "python_runner/hermes_cron/manifest.py", line 304, in validate_manifest
  raise ValueError(ReasonCode.MANIFEST_IDENTITY_MISMATCH.value)
ValueError: MANIFEST_IDENTITY_MISMATCH
```

## Cơ chế phát sinh
1. **Lệch Revision giữa Manifest và Source Config**:
   - Manifest active của ngày (`manifests/<day>/ACTIVE.json` -> `assignment-v1-...`) được tạo bởi `tiktok_picker.py` vào lúc 06:00 sáng, đóng băng `source_revision` tại thời điểm đó.
   - Khi có thay đổi trong ngày (ví dụ cron sync `taikhoan-run-safe-sync` cập nhật `taikhoan_run_safe.xlsx` hoặc `hermes_cron_source_config.json`), file `source_config` trên đĩa mang hash `source_revision` mới.
2. **Fail-closed Seam F1 (Manifest Identity Guard)**:
   - `hermes_cron_watcher.py` và `hermes_cron_runner.py` gọi `load_active(paths, args.day, expected_source=source)`.
   - `validate_manifest` so sánh `payload["source_revision"] != source.source_revision`. Nếu khác nhau, hệ thống dừng khẩn cấp fail-closed để chống drift cấu hình mid-day.

## Quy trình kiểm tra nhanh
```bash
# Kiểm tra hash giữa source_config hiện tại và active manifest
/d/Taadaa/python-envs/automation/Scripts/python.exe -c "
import json
from python_runner.hermes_cron.source_config import SourceConfig
with open('D:/Taadaa/runtime/kibe/cron-source/hermes_cron_source_config.json', 'r', encoding='utf-8') as f:
    src = SourceConfig.from_dict(json.load(f))
print('Current Source Revision:', src.source_revision)
"
```

## Hướng xử lý & Vận hành
- **Silent Window**: Khung giờ `02:00 - 05:59` là silent window (exit 0, không tác vụ).
- **Rollover tự nhiên**: Lúc `06:00` sáng mỗi ngày, `tiktok_picker.py` tự động nhặt `source_config` mới nhất và tạo manifest active mới cho ngày hôm đó.
- **Nếu cần đồng bộ ngay trong ngày**: Chạy picker với `--force-regenerate` để tạo lại manifest mới khớp với `source_config` đã cập nhật.
