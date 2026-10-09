# PowerShell Switch Argument Trap (Hit 2026-09-11)

## 1. Triệu chứng
Khi chạy `run_tiktok_upload_avatar.ps1`, script gọi `run_tiktok_upload_batch.ps1` qua subprocess:
```powershell
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $batchLauncher @splat
```
Trong đó `@splat` là hashtable chứa `AvatarOnly = $true`.

Lỗi nhận được:
```
Cannot process argument transformation on parameter 'AvatarOnly'. 
Cannot convert value "System.String" to type "System.Management.Automation.SwitchParameter".
Boolean parameters accept only Boolean values and numbers, such as $True, $False, 1 or 0.
```

## 2. Nguyên nhân
- `run_tiktok_upload_batch.ps1` khai báo tham số: `[switch]$AvatarOnly`.
- Khi PowerShell serialize hashtable `@splat` thành CLI args, nó chuyển thành chuỗi `"-AvatarOnly True"`.
- `[switch]` parameter **không nhận giá trị string "True"** — nó chỉ nhận bare flag `-AvatarOnly` (không kèm value) hoặc giá trị boolean `$true`/`$false` khi gọi trong cùng process.

## 3. Giải pháp chuẩn
Không dùng splatting qua `powershell.exe -File`, mà build mảng argument thủ công:

```powershell
$batchArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $batchLauncher,
    "-Tik", $Tik,
    "-MaxParallel", $MaxParallel,
    "-HostConfigPath", $HostConfigPath,
    "-AvatarOnly",           # bare switch, KHÔNG kèm value
    "-ForceAvatarMachineList", $ForceAvatarMachineList,
    "-MachineStartStaggerMs", $MachineStartStaggerMs
)
if ($AssignmentManifest -and $WorkerId) {
    $batchArgs += @("-AssignmentManifest", $AssignmentManifest, "-WorkerId", $WorkerId)
}

& powershell.exe @batchArgs
```

## 4. Quy tắc bắt buộc cho mọi launcher PowerShell
1. **Không bao giờ** splatting hashtable chứa `[switch]` parameter qua `powershell.exe -File`.
2. **Luôn** build mảng args (`@(...)`) với bare switch cho các `[switch]` param.
3. **Test bằng** `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& 'script.ps1' -SwitchParam"` trước khi deploy cron.