# Bài Học Vận Hành & Khắc Phục Lỗi Auto-Recovery Agent (Argparse & Refine Patch Signature) (20/08/2026)

## 1. Bối cảnh & Hiện tượng
- **Hiện tượng**: Trên nhóm Telegram "Farm Alerts", các máy dừng phiên (Máy 71, 74 báo lỗi `MissingVpnRecoveryError` do timeout kết nối proxy) nhưng hoàn toàn **không thấy tin nhắn 2 (Auto-Recovery) phản hồi**.
- **User chất vấn**: *"lại k thấy auto recovery chạy (chiều ms fix đc xong h lại lỗi)"* và *"review trc khi commit chưa"*.

---

## 2. Nguyên nhân Gốc rễ (Root Cause)

### A. Sót import `argparse` trong `python_runner/ai_recovery/agent.py`
- Trong quá trình refactor thêm type guard và strict schema validation lúc chiều, dòng `import argparse` bị sót ở đầu file.
- Khi `alerts.py` kích hoạt `subprocess.Popen([sys.executable, "agent.py", ...])`, tiến trình con bị crash ngay lập tức ở dòng khởi tạo CLI:
  ```python
  parser = argparse.ArgumentParser(description="AI Auto-Recovery Agent for TikTok Farm")
  # NameError: name 'argparse' is not defined
  ```
- Do chạy ở chế độ subprocess `stdout/stderr=DEVNULL`, lỗi diễn ra trong im lặng và không tạo ra bất kỳ tin nhắn xử lý nào.

### B. Lệch tham số (Signature Mismatch) ở `vision_client.refine_patch`
- Nhờ bước **Review độc lập qua Model `ag/claude-opus-4-6-thinking` (9Router)** trước khi chốt commit, reviewer đã chỉ ra lỗi mismatch:
  - `agent.py` gọi: `vision_client.refine_patch(alert_img_path=..., current_patch=..., handler_name=...)`
  - Trong khi định nghĩa thật trong `vision_client.py` là:
    ```python
    def refine_patch(
        img_bytes: bytes,
        ui_xml_summary: str,
        error_reason: str,
        machine: int,
        target_file: str,
        original_patch: str,
        audit_feedback: str,
        attempt: int = 1,
        runner_snippets: dict[str, str] | None = None,
    ) -> dict[str, Any]:
    ```
- Nếu không có bước Model Review độc lập, khi gặp lỗi audit rejection, vòng lặp `refine_patch` sẽ bị TypeError tại runtime.

---

## 3. Cách khắc phục & Bài học kỹ thuật

1. **Fix `agent.py`**:
   - Bổ sung `import argparse`.
   - Nạp ảnh `_img_bytes` từ `alert_img_path` (hoặc `live_before`), cắt ngắn `ui_xml_summary = (ui_xml or "")[:1500]`, truyền đúng keyword arguments cho `vision_client.refine_patch`.
2. **Lock Isolation trong Pytest**:
   - Khi chạy test các hàm `agent.run()`, cần patch mock `recovery_lock.acquire(return_value=True)` để tránh tình trạng test trước tạo file lock trên đĩa (`D:\Taadaa\runtime\kibe\recovery_locks\m1.lock`) làm test sau bị chặn nhầm.
3. **Quy tắc Pre-Commit Review**:
   - Bất kỳ thay đổi nào dù nhỏ (kể cả 1 dòng import) đều phải chạy pytest xanh và gọi model AI review diff độc lập (`ag/claude-opus-4-6-thinking` / `gpt-5.6-terra` qua 9Router) trước khi `git commit` & `git push`.
