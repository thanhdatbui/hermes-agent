# Consumer Scheduler & CLI Orchestration Patterns

Khi các script runner / orchestrator PowerShell trong repo consumer (như `run_tiktok_upload_avatar.ps1`, `run_tiktok_upload_batch.ps1`) gọi chéo qua subprocess CLI `powershell.exe`:

### Pitfall: Splatting `[switch]` parameter qua Subprocess CLI
- Khi truyền hashtable `@splat` cho script in-process (ví dụ `& $scriptPath @splat`), PowerShell tự hiểu kiểu `[switch]` và xử lý `AvatarOnly = $true` thành bare switch `-AvatarOnly`.
- **TUY NHIÊN**, khi gọi qua subprocess CLI:
  ```powershell
  # ❌ SAI:
  $splat = @{
      Tik = $Tik
      AvatarOnly = $true
  }
  & powershell.exe -File $batchLauncher @splat
  ```
  PowerShell engine sẽ serialize cặp key-value thành argument CLI dạng `-AvatarOnly True` (chuỗi `"True"`).
- Target script khai báo `[switch]$AvatarOnly` sẽ quăng ngoại lệ:
  `ParameterArgumentTransformationError: Cannot convert value "System.String" to type "System.Management.Automation.SwitchParameter". Boolean parameters accept only Boolean values and numbers, such as $True, $False, 1 or 0.`

### Cách giải quyết chuẩn
Dùng mảng argument CLI (`$args = @(...)`) thay vì hashtable splatting khi gọi external process `powershell.exe`:
```powershell
# ✅ ĐÚNG:
$batchArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $batchLauncher,
    "-Tik", $Tik,
    "-MaxParallel", $MaxParallel
)
if ($AvatarOnly) {
    $batchArgs += "-AvatarOnly"
}
if ($ForceAvatarMachineList) {
    $batchArgs += @("-ForceAvatarMachineList", $ForceAvatarMachineList)
}

& powershell.exe @batchArgs
```
- Đối với `[switch]`, chỉ append flag string bare `"-AvatarOnly"`, tuyệt đối không truyền thêm giá trị chuỗi đằng sau khi forward sang CLI.
