# Batch Aggregator & Farm Alert Header Specification (Case 92 & Case 93)

## 1. Context & User Directives
- **Case 92 (11/09/2026):** Tránh hiểu lầm tỷ lệ lỗi toàn batch khi 100% số máy dừng/thất bại (ví dụ: 60 máy config-error và 20 máy proxy/vpn, nếu chỉ hiển thị signature cục bộ 75% sẽ khiến user tưởng batch còn 25% chạy được).
  - Bắt buộc hiển thị tổng tỷ lệ thất bại toàn batch ở header: `• Tổng tỷ lệ thất bại toàn batch: {overall_fail_rate:.1%} ({failed_count}/{total_machines} máy)`.
  - Signature chi tiết phải tách rõ: `Tỷ lệ trên toàn batch: ...` và `Tỷ lệ trong số máy lỗi: ...`.
- **Case 93 (12/09/2026):** User feedback trực tiếp: *"Sửa lại thông báo đầu tiên phải ghi rõ script lỗi lên trên đầu của farm alert"*.
  - Mọi thông báo Batch Alert gửi Telegram (`format_alert_message`) BẮT BUỘC phải đặt dòng định danh script/quy trình lên ngay dưới banner đỏ:
    `• Quy trình / Script: <b>{disp_script}</b>`
  - Ưu tiên phân giải alias sang tên tiếng Việt chuẩn hóa qua `_resolve_script_meta` từ `automation_core.alerts`.
  - Fallback an toàn: Tự động phát hiện từ `run_manifest.json` (`mode`, `account`, `script`, `pipeline`), `summary.txt`, hoặc từ khóa đường dẫn run directory qua hàm `detect_script_from_source(path)`.
  - CLI hỗ trợ tùy chọn tường minh `--script <name>`.

## 2. Standard Batch Alert Telegram Template
```html
🚨 <b>[BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG</b>
• Quy trình / Script: <b>Nuôi Acc / Lướt Feed (tiktok-luot nuoi acc)</b>
• Quy mô batch: <b>80 máy</b> | Thành công: 0 | Thất bại: 80
• Tổng tỷ lệ thất bại toàn batch: <b>100.0%</b> (80/80 máy)
• Số cụm lỗi hệ thống: <b>1</b>

📋 <b>CHI TIẾT LỖI VƯỢT NGƯỠNG KÉP (RATE & COUNT):</b>
❌ <b>Signature:</b> <code>script-blocker:account row 8 is empty (no username) for &lt;device&gt;, skipping</code>
   - Tỷ lệ trên toàn batch: <b>95.0%</b> (76/80 máy)
   - Tỷ lệ trong số máy lỗi: <b>95.0%</b> (76/80 máy lỗi)
   - Danh sách máy: <code>M1, M2, M3, M4, ...</code>

🎯 <b>CHỈ DẪN CANARY POLICY & RECOVERY:</b>
1. Khóa batch: Không can thiệp đồng loạt toàn bộ thiết bị.
2. Canary Test đại diện trên 1 máy: <code>python D:/Taadaa/tools/inspect_machine.py M1</code>
3. Ảnh hiện trường: ...
4. Sau khi kiểm chứng canary thành công mới mở lại toàn bộ fleet.
```

## 3. Implementation Rules
1. **`BatchAggregationReport` Data Model**:
   - Trường `script_name: Optional[str] = None` phải luôn có mặt trong `@dataclass` và serialize vào `to_dict()`.
2. **Backward Compatibility**:
   - Tất cả tham số `script_name` trên `format_alert_message` và `evaluate_batch` đều để default `None`.
   - Nếu không truyền `script_name`, hiển thị fallback `Chưa rõ quy trình`.
3. **Focused Testing Gate**:
   - Khi sửa `batch_aggregator.py`, chỉ chạy focused test suite:
     `pytest tests/test_batch_aggregator.py`
   - Đảm bảo kiểm thử đầy đủ các nhánh: alias đã biết, custom script, default unknown, và manifest detection.
