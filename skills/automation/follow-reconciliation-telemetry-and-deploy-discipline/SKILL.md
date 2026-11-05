---
name: follow-reconciliation-telemetry-and-deploy-discipline
description: Kỷ luật đối soát số liệu follow chéo, chống ảo giác tự suy diễn follow tự nhiên và fix lỗi Join-Path PowerShell 5.1.
---

# Follow Reconciliation Telemetry & Deploy Discipline

## 1. Ground Truth Invariant: Chống Bịa Đặt / Suy Diễn Lượt Follow Tự Nhiên
- **Cạm bẫy:** Khi đối soát TikTok Web thấy delta tăng nhiều hơn số lượt follow chéo script báo cáo (ví dụ: script báo 12 lượt, nhưng Web tăng 17 lượt so với baseline cũ):
  - **CẤM TUYỆT ĐỐI** Coordinator tự đoán mò hoặc bịa đặt lý do "acc có follow tự nhiên khi lướt feed" nếu không có bằng chứng rõ ràng trong `log.jsonl`.
  - Trên thực tế, cấu hình lướt feed thường kiểm tra xác suất và bỏ qua (`'action': 'follow_video', 'result': 'skipped', 'error': 'roll skipped by follow rate percent'`).
  - **Bản chất kỹ thuật:** TikTok CDN/Web áp dụng mô hình **Eventual Consistency**. Khi tài khoản thực hiện batch follow mới, máy chủ TikTok mới flush và đồng bộ hiển thị các action follow cũ hoặc pending follow bị delay từ các phiên trước lên Web profile.

## 2. Invariant Đối Soát Khi Baseline Cũ (`is_stale_baseline = True`)
- **Vấn đề cũ (Khóa cứng equality):** Watchdog kiểm tra `latest_fl - prev_fl == expected_delta`. Khi delta trên web lớn hơn số lượt script báo (do gom flush trễ), điều kiện bị `False` và nick bị dán nhãn `UNPROVEN` oan uổng.
- **Quy tắc chuẩn hóa (Tolerant Lower Bound):**
  ```python
  stale_matches_expected = (
      bool(baseline_row)
      and is_stale_baseline
      and expected_delta > 0
      and (int(latest_row[0] or 0) - int(baseline_row[0] or 0)) >= expected_delta
  ) if latest_row else False
  ```
  - Khi Web ghi nhận delta $\ge$ `expected_delta` > 0: Xác nhận thành quả thực tế trên Web đã chứng minh script đã follow thành công tối thiểu số lượng đã báo.
  - Ghi nhận `script X lượt - web Y lượt - lệch (+diff) [baseline cũ (...)]`, TUYỆT ĐỐI KHÔNG dán nhãn `UNPROVEN`.
  - Chỉ dán nhãn `UNPROVEN` khi `web_delta < expected_delta` hoặc hoàn toàn thiếu snapshot.

## 3. PowerShell 5.1 `Join-Path` Positional Parameter Bug
- Trên Windows PowerShell 5.1 mặc định, `Join-Path` chỉ nhận tối đa 2 tham số vị trí: `Path` và `ChildPath`.
- Lệnh 3 tham số: `Join-Path $RepoRoot 'scripts' 'hermes_cron'` sẽ văng:
  `ParameterBindingException: A positional parameter cannot be found that accepts argument 'hermes_cron'`
  khiến các script deploy wrapper bị gãy ngầm mà không báo lỗi ra ngoài.
- **Sửa chuẩn:**
  ```powershell
  # Cách 1: Lồng Join-Path
  $SourceDir = Join-Path (Join-Path $RepoRoot 'scripts') 'hermes_cron'
  
  # Cách 2: Sử dụng .NET System.IO.Path
  $SourceDir = [System.IO.Path]::Combine($RepoRoot, 'scripts', 'hermes_cron')
  ```
