# Cơ Chế Protection Regression Gate Cho Hạ Tầng Hermes & OmniRoute (26/10/2026)

## 1. Bối Cảnh & Nhu Cầu Bắt Buộc (User Mandate)
- Trong các đợt sự cố hạ tầng (OmniRoute treo, bão rớt proxy, gateway timeout), Agent thường có xu hướng "sửa nhanh theo triệu chứng" (symptom fix):
  - Tăng vọt `api_max_retries` lên 6–8 lần để kéo dài thời gian chờ.
  - Hạ trần `$MaxDeadlockFailures` của Watchdog xuống 2–3 lần để restart nhanh hơn.
  - Hạ `compression.threshold` xuống 0.12 để giảm tải proxy.
- **Hậu quả nghiêm trọng:** Những thay đổi chắp vá này trực tiếp phá vỡ các bản vá ổn định trước đó (gây bão tải Thundering Herd sập heap 7.1GB ngày 02/10, hoặc kích hoạt vòng lặp nén liên tục ngày 03/10, hoặc bắn nhầm tiến trình hợp lệ ngày 05/10).
- **Chỉ thị của User (26/10/2026):** *Từ giờ mọi fix hạ tầng Hermes và OmniRoute bắt buộc phải có cơ chế Protection Regression Gate để chặn đứng tái phát lỗi cũ.*

---

## 2. Kiến Trúc 6 Invariant Bất Biến Của Hạ Tầng

| Thành Phần | Invariant Khóa Cứng | Ngưỡng An Toàn | Sự Cố Lịch Sử Tương Ứng |
|---|---|---|---|
| `compression.threshold` | Cấm < 0.28 và cấm > 0.35 | **`0.30`** | **03/10/2026:** Hạ xuống 0.12 khiến session 120k tokens bị nén liên tục.<br>**11/08/2026:** Nâng lên 0.45 khiến context chạm 372k trước khi nén làm GPT worker ngọng. |
| `agent.api_max_retries` | Cấm > 4 và cấm < 3 | **`4`** (kết hợp delay 6s) | **02/10/2026:** Đặt 5–6 retries gây bão 50 req/phút khi dính 503 Heap Pressure.<br>**26/10/2026:** Đặt < 3 khiến Hermes bỏ cuộc trước khi OmniRoute restart xong. |
| `agent.api_retry_delay` | Cấm < 5.0s và cấm > 12.0s | **`6.0s`** | **26/10/2026:** Delay ngắn 2s–3s đốt sạch retries trong 15s trước khi port 20129 kịp bind. |
| **Retry Headroom** | Tổng chờ `sum(delay * 2^i)` | **`[70s, 130s]`** | Đủ đón cửa sổ chết OmniRoute restart (25s–111s), không vượt quá hạn Telegram timeout. |
| `fallback_providers` | Cấm chứa port 20129 | Không self-loop | **26/10/2026:** Fallback sang chính cổng 20129 đang sập, gây connection refused kép. |
| `$MaxDeadlockFailures` | Cấm < 4 và cấm > 6 | **`[4, 6]`** | **05/10/2026:** < 4 gây False-Kill khi prompt 300k+ tokens đang prefill, kích hoạt anti-flapping khóa 15m.<br>> 6 (như 12) khiến hệ thống đơ cứng 6 phút mới restart. |

---

## 3. Triển Khai Cơ Giới Hóa (Mechanical Enforcement)

### A. Công Cụ Độc Lập `infra_regression_gate.py`
- Đường dẫn: `D:/Taadaa/tools/infra_regression_gate.py`.
- Tự động quét và đối soát `config.yaml` và `omniroute_watchdog.ps1`.
- Trả về exit code 0 nếu đạt 100% Invariants; exit code 1 kèm báo cáo chi tiết vi phạm.
- Hỗ trợ cờ `--json` cho CI/CD và pipeline.

### B. Chốt Chặn Trực Tiếp Tại `manage_hermes_config.py`
- Tích hợp chốt chặn tự động trước khi ghi cấu hình:
  ```python
  from infra_regression_gate import validate_hermes_config_invariants
  ok_gate, gate_violations = validate_hermes_config_invariants(data)
  if not ok_gate and not getattr(args, "force_regression", False):
      print("❌ REGRESSION GATE BLOCKED: Mutation violates infrastructure invariant(s):")
      for v in gate_violations:
          print(f"  * {v}")
      sys.exit(4)
  ```
- Nếu Agent cố ý đặt `api_max_retries = 6` hoặc `compression.threshold = 0.12`: Tool lập tức hủy lệnh và in lý do chặn kèm sự cố lịch sử tương ứng.

### C. Bộ Unit Test Tự Động (8/8 Passed)
- Đường dẫn: `D:/Taadaa/tools/tests/test_infra_regression_gate.py`.
- Kiểm chứng toàn bộ ma trận vi phạm: Thundering herd, premature fail, short delay, threshold out of range, fallback loop.
- Chạy kiểm tra: `pytest D:/Taadaa/tools/tests/test_infra_regression_gate.py`.
