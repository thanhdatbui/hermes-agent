# DONE_WITHOUT_CHATGPT_REG Telemetry Warning Triage Runbook

## 1. Triệu chứng & Nhận diện
Trong báo cáo định kỳ 6h (`cron_hotmail_gpm_lifecycle_6h_report.py`), xuất hiện dòng cảnh báo:
```text
⚠️ Dữ liệu có 1 cảnh báo (DONE_WITHOUT_CHATGPT_REG) - correlation_id=<hex>
```

## 2. Nguyên nhân Gốc rễ Hiện trường
- Khi script chạy `normalize_profiles()`, trường `has_chatgpt` chỉ được đánh dấu là `True` khi trường timestamp `chatgpt_registered_at` tồn tại và parse thành công datetime UTC.
- Với các tài khoản đã hoàn tất toàn bộ chu kỳ (`bucket == STAGE_DONE`, đổi pass và bật 2FA thành công) từ các phiên bản supervisor cũ trước đây:
  - Bản ghi state JSON (`batch_gpm_5profiles_supervisor_state.json`) có `"has_chatgpt": true` và `"chatgpt_password": "..."`.
  - Tuy nhiên, bản ghi KHÔNG có trường `chatgpt_registered_at`.
- Bộ đếm `aggregate_records()` kích hoạt cảnh báo audit:
  ```python
  if rec["bucket"] == STAGE_DONE and not rec.get("has_chatgpt"):
      done_without_chatgpt.append(rec["key"])
  ```

## 3. Quy trình Triage O(1) & Đánh giá Rủi ro
1. **Lệnh trích xuất kiểm chứng nhanh (không scan toàn đĩa):**
   ```bash
   python -c "
   import json
   p = 'D:/Taadaa/runtime/kibe/cron-state/batch_gpm_5profiles_supervisor_state.json'
   data = json.load(open(p, encoding='utf-8'))
   profs = data.get('profiles', {})
   done_no_ts = [k for k, v in profs.items() if (v.get('stage') == 'DONE' or v.get('status') == 'DONE') and not v.get('chatgpt_registered_at')]
   print(f'Done without timestamp: {len(done_no_ts)} accounts')
   if done_no_ts:
       print('Sample:', done_no_ts[:3])
       print('Sample detail:', json.dumps(profs[done_no_ts[0]], indent=2))
   "
   ```
2. **Đánh giá ảnh hưởng số liệu:**
   - Hàm `_is_chatgpt_registered(rec)` đã có điều kiện bao bọc:
     ```python
     def _is_chatgpt_registered(rec: dict[str, Any]) -> bool:
         return rec.get("stage") not in REGISTRATION_VOID_STAGES and (
             bool(rec.get("has_chatgpt")) or rec.get("bucket") == STAGE_DONE
         )
     ```
   - Do đó, toàn bộ số nick này **vẫn được tính hợp lệ 100% vào chỉ số `Toàn Farm Đã Reg Thành Công (chatgpt_ok)`**.
   - Cảnh báo hoàn toàn mang tính audit telemetry (truy nguyên dữ liệu lịch sử thiếu timestamp).

## 4. Kỷ luật Vận hành (Invariants)
- **CẤM reset/chuyển ngược stage:** Tuyệt đối không chuyển các nick `DONE` này về lại `CHATGPT_REG` để ép lấy timestamp, vì tài khoản đã đổi mật khẩu và bảo mật hoàn tất.
- **Không nhầm lẫn với lỗi kẹt:** Phân biệt rõ cảnh báo audit telemetry với lỗi nghẽn supervisor hoặc rớt proxy. Nếu `warning_count > 0` do `DONE_WITHOUT_CHATGPT_REG` nhưng các chỉ số khác tăng đều thì hệ thống đang vận hành bình thường.
