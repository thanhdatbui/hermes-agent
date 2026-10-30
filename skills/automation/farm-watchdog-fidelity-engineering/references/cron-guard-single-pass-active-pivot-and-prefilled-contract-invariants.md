# Cron Guard Single-Pass Active Pivot & Pre-filled Contract Invariants

## 1. Context & Problem (391 Block Death Spiral)
Trong các phiên giám sát tuân thủ 6h (`farm-gate-compliance-6h-report`), Gate G8 (`Cronjob Window Guard`) ghi nhận tới **391 lượt vi phạm** dồn cục:
- `CRON_AGENT_POLICY`: 103 lần
- `FARM_CONTRACT_INVALID`: 99 lần
- `WORKER_CAP_EXCEEDED`: 63 lần
- `NO_AGENT_REQUIRED`: 45 lần
- `FARM_CONTRACT_MISSING_KEYS`: 36 lần
- `FARM_CONTRACT_MISMATCH`: 18 lần
- `FARM_CONTRACT_UNKNOWN_KEYS`: 9 lần
- `ROLLING_MODE_REQUIRED`: 9 lần

### Nguyên Nhân Gốc Rễ:
1. **Instruction Trống / Chung Chung:** Khi vi phạm các quy tắc trên, `guard_cronjob_safety.py` trả về `instruction` chung chung: *"Sửa đúng điểm vi phạm nêu trong message rồi gửi lại cronjob"* và trường `command` để rỗng `""`.
2. **Thiếu Schema Chuẩn Mẫu:** Agent/Subagent không có định nghĩa cấu trúc của `farm_contract` nên tự bịa các key lạ hoặc thiếu key bắt buộc, dẫn đến việc bị chặn lặp đi lặp lại hàng trăm lần (Block Death Spiral).
3. **Thiếu Tín Hiệu Dừng Thử Lại (Stop Retrying Original Payload):** Hook chỉ trả về `action: block` mà không có tín hiệu cơ học ép buộc agent chuyển hướng (Active Pivot) trong lần thử tiếp theo.

---

## 2. Invariants Kiến Trúc Guidance & Auto-Rewire Cho Cron Guard

### Invariant 1: Pre-filled Contract Schema Trong Mọi Phản Hồi Chặn
Mọi thông báo chặn thuộc nhóm `FARM_CONTRACT_*` và `CRON_AGENT_POLICY` BẮT BUỘC phải nhúng schema JSON mẫu hoàn chỉnh và copy-pasteable:
```python
CRON_INSTRUCTION = {
    "FARM_CONTRACT_INVALID": "AUTO-REWIRE & ACTIVE PIVOT O(1): Thay ngay farm_contract bằng schema chuẩn bên dưới trong 1 bước duy nhất, tránh lặp lại payload cũ gây death spiral. Mẫu JSON pre-filled: {'farm_contract': {'touches_device': True, 'device_lock': 'required', 'mode': 'rolling', 'max_workers': 3, 'release': 'per_device', 'lock_ttl_s': 300, 'on_device_fail': 'skip_continue'}, 'no_agent': True}. Nếu script không tương tác thiết bị Android, đặt touches_device=False.",
    # ...
    "CRON_AGENT_POLICY": "AUTO-REWIRE & ACTIVE PIVOT O(1): Dừng ngay lập tức việc retry payload cũ gây kẹt vòng lặp (death spiral). Áp dụng duy nhất một lần payload đã vá hoàn chỉnh bằng pre-filled schema mẫu: {'farm_contract': {'touches_device': True, 'device_lock': 'required', 'mode': 'rolling', 'max_workers': 3, 'release': 'per_device', 'lock_ttl_s': 300, 'on_device_fail': 'skip_continue'}, 'no_agent': True}."
}
```

### Invariant 2: Payload Cơ Học `auto_rewire` Kèm `single_pass_active_pivot`
Trong hàm `deny_cron_policy`, payload JSON trả về cho runtime BẮT BUỘC phải chứa metadata cơ giới hóa:
```python
payload["auto_rewire"] = {
    "enabled": True,
    "strategy": "single_pass_active_pivot",
    "max_attempts": 1,
    "action": "patch_only_violating_fields",
    "preserve_valid_fields": True,
    "stop_retrying_original_payload": True,
    "contract_template": {
        "touches_device": True,
        "device_lock": "required",
        "mode": "rolling",
        "max_workers": 3,
        "release": "per_device",
        "lock_ttl_s": 300,
        "on_device_fail": "skip_continue"
    },
    "policy_template": {"no_agent": True}
}
```

### Invariant 3: Kỷ Luật Điều Phối Coordinator — Cấm Đứng Im Xin Phép Khi Nhận Lệnh Nắn/Fix
- Khi User ra lệnh *"Nắn lại guidance auto rewire"*, *"Sửa đi"*, *"Fix đi"*:
- Coordinator BẮT BUỘC kích hoạt NGAY TRỌN GÓI `unified_patch_pipeline.py run` (Gates S0 $\to$ S5).
- TUYỆT ĐỐI CẤM Coordinator dừng lại để viết văn giải trình dài dòng rồi hỏi *"Anh duyệt phương án này để em triển khai nhé!"*. Đó là hành vi bại liệt vi phạm kỷ luật vận hành.
