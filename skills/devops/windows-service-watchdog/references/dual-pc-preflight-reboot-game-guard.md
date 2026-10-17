# Dual-PC Preflight Reboot & Game Guard (Kibe PC & Admin PC)

## Bối Cảnh Sự Cố (17:20:01)
Hệ thống farm Taadaa cấu hình Windows Task Scheduler tự động reboot 3 ca (05:20, 11:20, 17:20) trên cụm PC điều phối (Kibe PC và Admin PC qua `farm_preflight_daily_reset.py`).
Một lỗi nghiêm trọng xảy ra khi người vận hành đang chơi game rank Đấu Trường Chân Lý (TFT) trên máy Admin (`admin-farm`):
1. **Lỗi chỉ quét cục bộ (Local-Only Probe):** Script chỉ chạy `psutil` trên máy Kibe, hoàn toàn không kiểm tra máy Admin trước khi gửi lệnh reboot remote qua SSH (`ssh admin-farm shutdown /r /t 2`).
2. **Lỗi thu hẹp danh sách tiến trình:** Code chỉ tìm kiếm chuỗi `league of legends.exe` mà bỏ sót tiến trình trận đấu của client TFT PC Standalone (`tftclient-win64-shipping.exe`).
3. **Hậu quả:** Máy Kibe thấy rảnh, lập tức SSH tắt máy Admin sau 2 giây, làm sập ván cờ rank của người dùng.

---

## Nguyên Tắc Phân Loại Tiến Trình Game (Game Guard Contract)

Người vận hành quy định rõ ràng:
- **Đang ở Client / Sảnh chờ (Lobby / Client) -> ĐƯỢC PHÉP REBOOT:**
  - `LeagueClient.exe`
  - `LeagueClientUx.exe`
  - `TFTClient.exe` (khi chưa tải 3D engine trận đấu)
  - `RiotClientServices.exe`
  - `TFTAcademy.exe`
- **Đang trong trận đấu thực sự (In-Match 3D Engine) -> TUYỆT ĐỐI CẤM REBOOT:**
  - `league of legends.exe` (Engine trận đấu truyền thống qua LeagueClient)
  - `tftclient-win64-shipping.exe` (Engine trận đấu TFT PC Client / PBE)

---

## Chuẩn Triển Khai Kiểm Tra Kép (Dual-Host Preflight Check)

### 1. Quét tiến trình local (Kibe PC):
```python
TFT_ACTIVE_MATCH_PROCESSES = {
    "league of legends.exe",
    "tftclient-win64-shipping.exe",
}

def is_tft_match_in_progress() -> tuple[bool, list[str]]:
    names = _running_image_names() # psutil -> tasklist fallback
    running = sorted({name for name in names if name in TFT_ACTIVE_MATCH_PROCESSES})
    return bool(running), running
```

### 2. Quét tiến trình remote (Admin PC qua SSH):
```python
def is_admin_tft_match_in_progress() -> tuple[bool, list[str]]:
    """Kiểm tra tasklist trên Admin PC qua SSH. Lỗi kết nối -> Fail-Safe coi như đang in-match."""
    try:
        cmd = ["ssh", "-o", "ConnectTimeout=5", ADMIN_SSH_HOST, "tasklist /FO CSV /NH"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode != 0:
            log_message(f"[WARN] Khong lay duoc tasklist tu Admin PC (exit {res.returncode}). An toan: coi nhu in-match.")
            return True, ["admin:unknown (detection failed)"]
        rows = [row[0].lower() for row in csv.reader(io.StringIO(res.stdout)) if row]
        if not rows:
            return True, ["admin:unknown (empty tasklist)"]
        running = sorted({name for name in rows if name in TFT_ACTIVE_MATCH_PROCESSES})
        return bool(running), [f"admin:{n}" for n in running]
    except Exception as exc:
        log_message(f"[WARN] Exception khi kiem tra Admin PC: {exc}. An toan: coi nhu in-match.")
        return True, [f"admin:unknown ({exc})"]
```

### 3. Quy trình điều phối trong `main()`:
1. Kiểm tra local (Kibe PC) -> Có trận -> Abort, thoát 1.
2. Kiểm tra remote (Admin PC) -> Có trận -> Abort, thoát 1.
3. Kiểm tra device locks (`has_active_device_locks()`) -> Đang chạy ca -> Skip, thoát 0.
4. Chỉ khi CẢ 2 MÁY đều không có trận đấu và không vướng ca farm -> Mới thực hiện tuần tự: SSH reboot Admin PC -> Chờ 3s -> Lưu session Hermes -> Ghi sentinel -> Reboot Kibe PC.
