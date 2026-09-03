# Swipe Timeout Resilience & Dynamic Bounds (2026-08-22)

## 1. Triệu chứng & Nguyên nhân Lỗi Swipe Timeout (Máy 32)
- **Triệu chứng**: Phiên nuôi acc dừng ngang báo alert Telegram `[MÁY 32] DỪNG PHIÊN • Lý do: adb command timed out: ('...adb.exe', '-s', '<serial>', 'shell', 'input', 'swipe', '435', '1545', '442', '611', '1085')`.
- **Nguyên nhân**:
  1. Khi TikTok đang giải mã video nặng hoặc máy Samsung S7 bị nghẽn I/O, lệnh `input swipe` với duration dài (ví dụ `1085ms`) chiếm thread input của Android lâu, dẫn tới vượt quá timeout mặc định 15 giây của `ctx.adb.shell(...)`.
  2. Không có cơ chế bắt ngoại lệ `ADBError` / retry khiến toàn bộ flow unroll và dừng phiên.

## 2. Giải pháp kỹ thuật chuẩn hóa (`_perform_feed_swipe`)
- **Tăng timeout ADB cho Swipe**: `swipe_timeout = max(25.0, ctx.timeout("adb_seconds", 15))`.
- **Thêm cơ chế retry an toàn**:
  ```python
  swipe_timeout = max(25.0, ctx.timeout("adb_seconds", 15))
  cmd = ["input", "swipe", str(start[0]), str(start[1]), str(end[0]), str(end[1]), str(duration_ms)]
  try:
      result = ctx.adb.shell(cmd, timeout=swipe_timeout)
  except ADBError as exc:
      ctx.logger.log(
          device_id=ctx.device_id,
          account=ctx.account,
          step=f"{artifact_prefix}/swipe_{swipe_count}",
          action="feed_swipe",
          selector=selector,
          result="retry",
          error=f"first swipe attempt timed out: {exc}",
      )
      time.sleep(1.0)
      try:
          result = ctx.adb.shell(cmd, timeout=swipe_timeout)
      except ADBError as exc2:
          ctx.logger.log(
              device_id=ctx.device_id,
              account=ctx.account,
              step=f"{artifact_prefix}/swipe_{swipe_count}",
              action="feed_swipe",
              selector=selector,
              result=ExitStatus.FAIL.value,
              error=f"swipe failed after retry: {exc2}",
          )
          return False
  ```
- **Chuẩn hóa Duration**: Điều chỉnh cấu hình `min_swipe_duration_ms: 450`, `max_swipe_duration_ms: 700` (thay vì 800-1200ms) để các thao tác vuốt kết thúc nhanh và mượt mà hơn.

## 3. Bản chất cơ chế Click tọa độ vs UI XML
- **Không hardcode tọa độ nút**: Toàn bộ các thao tác click (chọn nick, thích, follow, chuyển tab) đều đọc UI XML qua ATX-agent (port 7912), parse selector theo `text`/`content-desc`/`resource-id`, lấy `bounds="[left,top][right,bottom]"` thực tế và tính tâm động `((left + right) // 2, (top + bottom) // 2)`.
- Chỉ có thao tác vuốt feed (Swipe) mới dùng tọa độ ngẫu nhiên kèm jitter ($\pm 15-30$px) để tạo tính tự nhiên.
