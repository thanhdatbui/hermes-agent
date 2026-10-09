# Case 183: Creator Lifecycle Upload Gate — Tách Biệt Dưỡng Sinh Tăng Trưởng vs Đăng Video Nuôi Nick

## 1. Bối cảnh & Băn khoăn của Người Vận Hành
Khi áp dụng cơ chế Dưỡng Sinh Ngẫu Nhiên (Per-Account Organic Rest 1/3), logic cũ định nghĩa:
`Dưỡng sinh = 0 Follow + 0 Đăng video`.

**Hậu quả toán học:**
- Mỗi nick chạy theo lịch so-le Chẵn/Lẻ (1 tuần chỉ lên máy 3.5 ngày).
- Khi lên máy lại dính tiếp 1/3 ngày nghỉ không đăng video $\to$ Thực tế 1 tuần chỉ đăng được ~2.3 video.
- Để tích lũy đủ mốc 10 video "tốt nghiệp" đi follow, 1 nick mất tới:
  $$10 \div 2.3 \approx 4.3\text{ tuần} \approx 30\text{ ngày}$$
Quá trình này kéo dài thời gian ươm mầm quá mức cần thiết, làm chậm tiến độ bung pool follow của farm.

---

## 2. Phán Quyết Kiến Trúc Từ Sol (Lead AI Architect)
- **Bản chất người dùng thật (Creator Persona):** Hành vi "vào app đăng 1 clip, lướt xem vài video giải trí rồi thoát, không đi kết bạn/follow ai" là hành vi cực kỳ phổ biến và lành mạnh.
- **Phân định rủi ro:** Thuật toán chống spam của TikTok soi xét hành vi kết bạn/follow dồn dập (quota-driven growth). Hành vi đăng video đều đặn là hành vi nền tảng khuyến khích.
- **Định nghĩa chuẩn mới:**
  > **Dưỡng sinh = Nghỉ hành động tăng trưởng ngoại vi (0 Follow). Upload video creator hợp lệ VẪN ĐƯỢC PHÉP.**
- **Hiệu quả:** Rút ngắn thời gian tích lũy 10 video từ 30 ngày xuống đúng **20 ngày** ($10 \div 3.5 \approx 2.8\text{ tuần} \approx 20\text{ ngày}$).

---

## 3. Thực Thi Code Surgery (`multi_machine_feed_session.py`)
Tại hàm `_run_upload_hook`:
- Gỡ bỏ khối `if is_organic: return payload (skipped, organic-rest-day-no-upload)`.
- Chuyển sang ghi nhận cờ telemetry và event JSONL nhưng cho phép luồng tiếp tục đi vào `upload_preflight`:
```python
    # Quy tắc Sol (Lifecycle): Dưỡng sinh = 0 Follow (nghỉ tương tác ngoại vi).
    # Upload là hành vi Creator lành mạnh, VẪN CHO ĐĂNG VIDEO BÌNH THƯỜNG để nick tích lũy đủ mốc.
    # Khi is_organic = True: ghi nhận telemetry flag rõ ràng vào child_ctx để downstream/audit theo dõi.
    if is_organic and isinstance(child_ctx.config, dict):
        child_ctx.config["_upload_in_organic_rest"] = True
        logger_inst = getattr(child_ctx, "logger", None)
        if logger_inst and hasattr(logger_inst, "log"):
            try:
                logger_inst.log(
                    step="upload-hook",
                    action="organic_rest_upload_permitted",
                    result="permitted",
                    machine=getattr(account, "machine", 0),
                    row=upload_row,
                )
            except Exception as log_err:
                sys.stderr.write(f"[WARN] Failed to write organic rest upload telemetry log: {log_err}\n")
```

---

## 4. Kiểm Thử & Thẩm Định Closeout Gate
- Viết test suite chuyên dụng `python_runner/tests/test_organic_rest_upload_gate.py`:
  1. `test_organic_rest_allows_upload_end_to_end`: Verify hook vượt qua gate và ghi log JSONL schema chuẩn.
  2. `test_non_organic_rest_day_preserves_standard_upload_path`: Regression test bảo đảm ngày thường không dính flag.
  3. `test_is_account_organic_rest_day_deterministic`: Deterministic MD5 hash.
  4. `test_is_account_organic_rest_day_distribution_multi_dates`: Thống kê tỷ lệ phân bổ ~33% trên 80 máy qua nhiều ngày.
- **Closeout Gate:** Sol Reviewer chấm **86/100 (APPROVED)**, test pass 4/4. Commit `80d4be3` đẩy lên master `tiktok-luot-nuoi-acc`.
