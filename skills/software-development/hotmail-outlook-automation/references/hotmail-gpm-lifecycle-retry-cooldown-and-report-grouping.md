# Hotmail GPM Lifecycle Cooldown & Grouped Reporting

## 1. Hotmail Login Auto-Unblock & Cooldown Pattern (Supervisor Level)

Khi supervisor quản lý vòng đời nhiều giai đoạn (`HOTMAIL_LOGIN` -> `CHATGPT_REG` -> `CODEX_OAUTH` -> `WAIT_7D` -> `CHANGE_INFO` -> `DONE`), nếu một giai đoạn thất bại và gán `status = "BLOCKED"`, quy tắc mặc định `if status in {"BLOCKED", "FAILED"}: continue` sẽ khiến các tài khoản bị kẹt vĩnh viễn trong hàng đợi.

### Giải pháp Cooldown 48h (2 ngày):
- Microsoft rate limit hoặc suspicious challenge trên Hotmail thường tự nhả sau 24-48 giờ.
- Không thử lại ngay lập tức (tránh Microsoft lock cứng IP/account), nhưng cũng không được để kẹt vĩnh viễn.
- Trong `select_candidates()`:
  ```python
  # Auto-unblock failed Hotmail login after 48h (2 days) cooldown for periodic retry
  elif stage == "HOTMAIL_LOGIN" and status in {"BLOCKED", "FAILED", "ERROR"}:
      fail_time = parse_time((info.get("last_result") or {}).get("at") or info.get("updated_at"))
      if not fail_time or (now_dt and (now_dt - fail_time).total_seconds() >= 2 * 86400):
          stage = info["stage"] = "HOTMAIL_LOGIN"
          status = info["status"] = "PENDING"
  ```
- Khi reset về `PENDING`, tài khoản được xếp lại vào hàng đợi FIFO, chạy theo proxy 4G của đúng máy farm, đảm bảo an toàn IP. Nếu tiếp tục thất bại, mốc thời gian `last_result.at` được cập nhật mới, tự động bắt đầu chu kỳ ngâm 48h tiếp theo.

---

## 2. Tránh Bẫy Nuốt Lỗi Trong Báo Cáo Vòng Đời (Report Truncation Trap)

Nếu gom toàn bộ tài khoản lỗi vào 1 danh sách phẳng `failed_profiles` rồi chỉ in `[:15]` kèm thông báo `... và N tài khoản khác`:
- Khi một giai đoạn (ví dụ `CODEX_OAUTH`) có số lượng lỗi áp đảo (hàng trăm nick), top 15 sẽ bị chiếm trọn bởi giai đoạn đó.
- Các giai đoạn khác (như `HOTMAIL_LOGIN`, `CHATGPT_REG`) bị nuốt chửng vào phần ẩn, khiến User tưởng rằng script không bắt lỗi hoặc các giai đoạn đó không hề có lỗi.

### Chuẩn hóa phân nhóm theo Stage:
Bắt buộc phân nhóm lỗi theo từng giai đoạn trước khi hiển thị mẫu:
```python
if failed_profiles:
    print(f"\n🔴 DANH SÁCH {len(failed_profiles)} TÀI KHOẢN GẶP LỖI CẦN XỬ LÝ (THEO GIAI ĐOẠN):")
    grouped_fails = {}
    for fp in failed_profiles:
        grouped_fails.setdefault(fp["stage"], []).append(fp)
        
    for failed_st, items in sorted(grouped_fails.items()):
        print(f"\n  📌 [{failed_st}] ({len(items)} tài khoản):")
        for fp in items[:5]:
            m_str = f"M{int(fp['machine']):02d}" if fp.get('machine') is not None else "M??"
            print(f"    • {m_str} | {fp['email']} ({fp['detail']})")
        if len(items) > 5:
            print(f"    • ... và {len(items) - 5} tài khoản khác.")
```

### Đồng bộ trạng thái DONE:
Trong state machine, khi hoàn thành chu kỳ cuối cùng, trạng thái có thể được lưu là `status: "DONE"` ở giai đoạn cuối (ví dụ `stage: "CHANGE_INFO"`). Bộ đếm báo cáo bắt buộc kiểm tra cả hai:
```python
if st == "DONE" or status == "DONE":
    done += 1
```
