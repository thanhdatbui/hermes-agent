# Quy Chuẩn Đồng Bộ Config & Plugin Hermes Vào Git Repository

Tài liệu đúc kết từ phiên trực chiến ngày 05/09/2026 khi nâng cấp `farm-coordinator-guard` v2.0.

## 1. Cạm Bẫy Thực Tế: Sửa Runtime Quên Đồng Bộ Git Repo
- **Hiện tượng:** Khi nâng cấp plugin hoặc tinh chỉnh config của Hermes Agent, kỹ sư thường sửa trực tiếp trong thư mục runtime local `%LOCALAPPDATA%\hermes\plugins\<tên_plugin>\` hoặc `%LOCALAPPDATA%\hermes\config.yaml`.
- **Hậu quả nghiêm trọng:**
  1. **Mất trắng khi re-bootstrap:** Khi máy gặp sự cố cần chạy lại `setup-admin.ps1` hoặc máy Admin mới cần đồng bộ, script bootstrap sẽ kéo code từ Git repo và ghi đè hoặc bỏ sót plugin mới.
  2. **Báo cáo Chốt phiên sai lệch:** Báo cáo Gate 4 ghi nhận `Remote: Local-only runtime` do file chỉ nằm trên đĩa local mà không được commit/push vào repo chia sẻ của farm.
  3. **Không đồng bộ đa máy:** Máy Admin (`200+`) và các node vệ tinh không nhận được bản vá lỗi của Coordinator.

---

## 2. Danh Mục Các Nơi BẮT BUỘC Phải Đồng Bộ

Khi có bất kỳ thay đổi nào tại `%LOCALAPPDATA%\hermes\`:

| Thành phần sửa đổi | Vị trí Runtime Local | Đích đồng bộ trong Git Repo |
| :--- | :--- | :--- |
| **Custom Plugins** (như `farm-coordinator-guard`) | `%LOCALAPPDATA%\hermes\plugins\<name>\` (`__init__.py`, `plugin.yaml`) | `D:\Taadaa\Hermes\deploy\hermes-home\plugins\<name>\` |
| **Hermes Config** | `%LOCALAPPDATA%\hermes\config.yaml` | 1. `D:\Taadaa\Hermes\deploy\hermes-home\config.yaml`<br>2. `D:\Taadaa\AI-Tools\config\hermes\hermes_config_template.yaml` |
| **Installer / Bootstrap Script** | N/A | `D:\Taadaa\Hermes\deploy\setup-admin.ps1` (bổ sung bước robocopy `plugins/`) |
| **Cron Scripts & Watchdogs** | `%LOCALAPPDATA%\hermes\scripts\*.py` | `D:\Taadaa\Hermes\deploy\hermes-home\scripts\*.py` |
| **Cron Definitions** | `%LOCALAPPDATA%\hermes\cron\jobs.json` | `D:\Taadaa\Hermes\deploy\hermes-home\cron\jobs.json` |

---

## 3. Quy Trình Đồng Bộ An Toàn 4 Bước (Có Redact Bí Mật)

### Bước 1: Sao chép file Plugin & Script vào Bundle Repo
```bash
# Tạo thư mục plugin trong deploy bundle của Hermes repo
mkdir -p "D:/Taadaa/Hermes/deploy/hermes-home/plugins/<tên_plugin>"

# Copy __init__.py và plugin.yaml
cp "C:/Users/Kibe/AppData/Local/hermes/plugins/<tên_plugin>/__init__.py" "D:/Taadaa/Hermes/deploy/hermes-home/plugins/<tên_plugin>/"
cp "C:/Users/Kibe/AppData/Local/hermes/plugins/<tên_plugin>/plugin.yaml" "D:/Taadaa/Hermes/deploy/hermes-home/plugins/<tên_plugin>/"
```

### Bước 2: Cập nhật Config & REDACT BÍ MẬT 100%
- Khi cập nhật `deploy/hermes-home/config.yaml` và `AI-Tools/config/hermes/hermes_config_template.yaml`, **CẤM TUYỆT ĐỐI** copy paste nguyên văn file có chứa API key hay credential thực tế.
- **Bắt buộc:**
  ```yaml
  custom_providers:
    - api_key: «redacted:sk-…»  # HOẶC key placeholder, CẤM để lộ sk-247...
  ```
- Thêm block `plugins:` để kích hoạt plugin khi bootstrap:
  ```yaml
  plugins:
    enabled:
      - farm-coordinator-guard
    disabled: []
    entries:
      farm-coordinator-guard:
        allow_tool_override: false
  ```

### Bước 3: Cập nhật `setup-admin.ps1` (Tự Động Sync Plugin)
Trong file `D:\Taadaa\Hermes\deploy\setup-admin.ps1`, bổ sung block đồng bộ plugins:
```powershell
# Sync Plugins
$PluginsSrcDir = Join-Path $BundleHermes 'plugins'
if (Test-Path -LiteralPath $PluginsSrcDir -PathType Container) {
    Write-Host "Syncing plugins..." -ForegroundColor Yellow
    $PluginsDstDir = Join-Path $HermesHome 'plugins'
    New-Item -ItemType Directory -Force -Path $PluginsDstDir | Out-Null
    robocopy $PluginsSrcDir $PluginsDstDir /E /xo /njh /njs /ndl /nc /ns | Out-Null
}
```

### Bước 4: Kiểm tra Diff & Commit / Push
1. Chạy `python -m py_compile` trên các file Python trong repo bundle để đảm bảo không lỗi cú pháp.
2. Chạy `git diff` trên cả `D:/Taadaa/Hermes` và `D:/Taadaa/AI-Tools`. Soi từng dòng diff để đảm bảo không có token, password hay API key nào bị commit.
3. Commit và push lên Git remote (`fork main` hoặc `origin main`).
4. Trong báo cáo chốt phiên (Session Closeout), dẫn chứng rõ Commit SHA của `Hermes` và `AI-Tools`.
