# Sol Auditor Remediation: State Migration, Telemetry & Test Coverage (Score >= 85)

## Bối Cảnh Thực Tế (Case Study `GPM auto` - 16/10/2026)
Trong phiên closeout, khi patch thêm logic auto-heal / migration trạng thái trong `load_state()` (ví dụ di dời tài khoản kẹt `HOTMAIL_LOGIN` có `chatgpt_registered_at` sang `WAIT_7D` và reset `BLOCKED`/`FAILED`), lượt review đầu tiên của Sol Auditor (:20129) chấm **78/100 (REJECTED)** dù 39/39 test cũ đều passed.

### Các Điểm Trừ Điểm Của Sol Auditor:
1. **Thiếu Telemetry Sự Kiện (Telemetry & Obs bị chấm 8/15):**
   - Migration thay đổi trạng thái nhưng chạy âm thầm trong `load_state`, không phát ra event telemetry ghi nhận thực thể bị tác động.
2. **Thiếu Test Trực Tiếp Cho Nhánh Migration Mới (Test Evidence bị chấm 21/25):**
   - Bộ test cũ pass 39/39 nhưng diff không có test nào trực tiếp cấp input có `chatgpt_registered_at` để assert output chuyển sang `WAIT_7D`.
3. **Chưa Bao Phủ Hết Các Trạng Thái Biên (Edge Statuses):**
   - Chỉ test cho 1 nhánh trạng thái đơn lẻ (như `BLOCKED`) mà bỏ sót nhánh `FAILED` hoặc các trường bị xóa (`error`, `last_result`).

---

## Công Thức Khắc Phục Để Vượt Ngưỡng (Score 78 ➔ 88 APPROVED)

### 1. Bổ Sung Dedicated Telemetry Event
Khi thực hiện migration hoặc auto-heal state, BẮT BUỘC phát sự kiện telemetry có cấu trúc với đầy đủ metadata:
```python
log_telemetry_event("migrated_to_wait_7d", {
    "email": info.get("email"),
    "machine": info.get("machine"),
    "stage": "WAIT_7D",
    "status": info.get("status"),
})
```

### 2. Viết Test Focused Trực Tiếp Bao Phủ Cả 2 Trạng Thái Biên
Trong file test, tạo fixture state chứa cả 2 profile ở 2 trạng thái lỗi khác nhau (`BLOCKED` và `FAILED`), sau đó kiểm chứng cả:
- Stage được chuyển sang `WAIT_7D`.
- Status được reset về `WAITING`.
- Các trường lỗi cũ `error` và `last_result` bị dọn sạch.
- Khẳng định event telemetry xuất hiện trong stdout qua `capsys`:
```python
def test_load_state_migrates_hotmail_login_with_chatgpt_to_wait_7d(tmp_path, monkeypatch, capsys):
    import json
    import scripts.batch_gpm_5profiles_supervisor as mod
    p = tmp_path / "state.json"
    p.write_text(json.dumps({
        "profiles": {
            "M01:u@hotmail.com": {
                "stage": "HOTMAIL_LOGIN",
                "status": "BLOCKED",
                "chatgpt_registered_at": "2026-10-15T00:00:00Z",
                "error": "some old error",
                "last_result": {"status": "FAILED"}
            },
            "M02:f@hotmail.com": {
                "stage": "HOTMAIL_LOGIN",
                "status": "FAILED",
                "chatgpt_registered_at": "2026-10-15T00:00:00Z"
            }
        }
    }), encoding="utf-8")
    monkeypatch.setattr(mod, "STATE_PATH", p)
    monkeypatch.setattr(mod, "get_oauth_emails", lambda: set())
    st = mod.load_state([], {})
    prof1 = st["profiles"]["M01:u@hotmail.com"]
    assert prof1["stage"] == "WAIT_7D" and prof1["status"] == "WAITING"
    assert "error" not in prof1 and "last_result" not in prof1
    prof2 = st["profiles"]["M02:f@hotmail.com"]
    assert prof2["stage"] == "WAIT_7D" and prof2["status"] == "WAITING"
    assert "migrated_to_wait_7d" in capsys.readouterr().out
```

---

## Kỷ Luật Vận Hành Terminal Cho Closeout Gate
- **Foreground Timeout Ceiling (<= 60s):**
  Lệnh `closeout_gate.py` trong session chính của Coordinator trên Windows có guard áp trần foreground 60s. Không bao giờ truyền `--timeout` cho terminal > 60s (ví dụ 90s sẽ bị `GUARD_FOREGROUND_TIMEOUT_EXCEEDED`). Thiết lập chuẩn: `timeout: 50`.
