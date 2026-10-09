# Automation-Core 0.4.45 Version Preflight & Profile Grid Character Matching (2026-10-09)

## 1. Pitfall: Automation-Core Version Mismatch (0.4.44 vs 0.4.45)
### Hiện tượng
Khi chạy launcher `run_tiktok_upload_avatar.ps1` (hoặc `run_tiktok_upload_batch.ps1`), tiến trình ném exception ngay ở preflight:
```
automation-core version mismatch: expected=0.4.44; actual=0.4.45; runtime=D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe; reason=metadata version did not match expected contract
```

### Nguyên nhân
- Trong `run_tiktok_upload_batch.ps1`:
  ```powershell
  $defaultAutomationCoreVersion = "0.4.44"
  $configuredAutomationCoreVersion = [string]$env:TIKTOK_VIDEO_AUTOMATION_CORE_VERSION
  if ([string]::IsNullOrWhiteSpace($configuredAutomationCoreVersion)) {
      $expectedAutomationCoreVersion = $defaultAutomationCoreVersion
  } else {
      $expectedAutomationCoreVersion = $configuredAutomationCoreVersion.Trim()
  }
  ```
- Khi môi trường ảo (`venv-core024` hoặc `automation`) đã được nâng cấp lên `automation-core 0.4.45` mà caller không truyền biến môi trường `$env:TIKTOK_VIDEO_AUTOMATION_CORE_VERSION`, launcher mặc định đòi `0.4.44` và ném lỗi dừng chạy.

### Giải pháp chuẩn khi invoke launcher qua Python wrapper / subprocess:
```python
env = os.environ.copy()
env["TIKTOK_VIDEO_AUTOMATION_CORE_VERSION"] = "0.4.45"
env["TAADAA_HOST_CONFIG"] = r"D:\Taadaa\machine-config\kibe.yaml"
env.pop("PYTHONPATH", None)  # Bắt buộc dọn PYTHONPATH tránh xung đột module

cmd = [
    "powershell.exe",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", r"D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1",
    "-Tik", str(tik),
    "-MaxParallel", "1",
    "-HostConfigPath", r"D:\Taadaa\machine-config\kibe.yaml",
    "-ForceAvatarMachineList", str(machine)
]
```

---

## 2. Kỹ thuật Đối khớp Video Grid với File Media trên Đĩa (Channel Character Matching)
### Bối cảnh
Khi Operator gửi ảnh màn hình Profile TikTok từ điện thoại cá nhân (ví dụ `@thachkieu05`, `@laquyen2601`):
1. **Đối soát 8 video đã đăng trên Profile:**
   - So sánh các thumbnail trên lưới video (3 cột) với các video `1.mp4 .. 8.mp4` trong `D:\TIKTOK-videonuoinick\<folder>\` tại timestamp `0.5s`.
   - Ví dụ:
     * `@thachkieu05`: Video 2 là clip cởi trần gập bắp tay khoe hình xăm, khớp 100% với thumbnail góc dưới bên trái của Profile grid. Xác nhận nhân vật chính của kênh là YouTuber/VĐV vật tay Hải Phệt.
     * `@laquyen2601`: Video 1 là clip VĐV nam áo cờ Việt Nam mỉm cười selfie tại giải đấu, khớp với thumbnail góc dưới bên phải. Xác nhận kênh thể thao/vật tay nam giới.
2. **Loại bỏ avatar rác / lệch vibe:**
   - File avatar cũ bị cắt trúng video tin tức ("24h NEWS" logo dính mặt em bé) hoặc ảnh hot girl cho kênh vật tay nam.
3. **Trích xuất chân dung cận cảnh chuẩn (Close-up Portrait):**
   - Dùng OpenCV Haar Cascade tìm khuôn mặt nhân vật chính trong các video 1, 2, 7.
   - Headroom `0.5 - 0.55`, `box_mult = 2.1 - 2.2`.
   - Soi mắt và chấm điểm qua 9Router Vision API (`ag/gemini-3.7-flash-high`) đạt $\ge 7.5/10$ (mặt sáng, nụ cười tự tin, không dính chữ/phụ đề che mặt).
4. **Đồng bộ triệt để 2 đầu kho & SQLite Queue:**
   - Copy file avatar vào `D:\video goc\<Folder Video>\avatar.jpg` và `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg`.
   - `UPDATE avatar_replace_queue SET status='PENDING', last_error=NULL, updated_at=datetime('now','localtime') WHERE username='...';`
