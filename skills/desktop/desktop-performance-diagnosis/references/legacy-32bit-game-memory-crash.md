# Legacy 32-bit Game Memory Crash Diagnosis & 4GB/LAA Patching

## Context
Diagnosing crashes/disconnections in legacy 32-bit Windows games (e.g. Warcraft III 1.26a, older DirectX 8/9 titles) on modern 64-bit Windows hosts (e.g. `admin-farm` with 64GB RAM).

---

## Symptom: "Not enough memory resources are available to process this command"

Common error signatures:
- Error modal / popup: `Not enough memory resources are available to process this command.`
- Object: `Handle2AgentReg (.?AUHandle2AgentReg@@)`
- File crash reference: `.\cmemblock.cpp (Line 372)` or `FATAL ERROR 0xC0000005 (ACCESS_VIOLATION)`.
- Crash log location: `<GameDir>\Errors\<timestamp> Error.txt` (or `.dmp`, `Crash.txt`).

---

## Root Cause: 2 GB Virtual Address Space (VAS) Ceiling

1. **32-bit Process Architecture:**
   On Windows 64-bit, a standard 32-bit process is limited to **2,048 MB (2 GB)** of virtual address space by default.
   Physical host RAM (e.g. 32 GB or 64 GB) is irrelevant when the process VAS limit is reached.
2. **Usable Memory Degradation:**
   GPU user-mode drivers (e.g. `nvd3dum.dll`, `nvgpucomp32.dll`), DirectX/Miles audio DLLs, and system runtimes map into the process's 2 GB address space first, leaving only ~1.4 GB – 1.6 GB for game assets and heap allocations.
3. **Trigger / Object Leak (Custom Maps):**
   Heavy custom maps (e.g. DotA IMBA, complex AoS/RPGs) leak handles (`Handle2AgentReg`), spell effects, floating text, and unit data.
   High in-game video settings (`particles: 2`, `spellfilter: 2`) accelerate buffer exhaustion during multi-player teamfights, exhausting the remaining address space and triggering an immediate crash.

---

## Inspection One-Liners (PowerShell / Remote SSH)

### 1. Check PE Header for Large Address Aware (LAA) Flag
Reads PE header `Characteristics` offset (`e_lfanew + 4 + 18 = offset 0x16 in COFF File Header`):
Bit `0x0020` (`IMAGE_FILE_LARGE_ADDRESS_AWARE`) enables up to 4 GB VAS on Windows x64.

```powershell
& {
    param([string]$f)
    $b = [System.IO.File]::ReadAllBytes($f)
    $o = [BitConverter]::ToInt32($b, 0x3C)
    $c = [BitConverter]::ToUInt16($b, $o + 22)
    $laa = ($c -band 0x20) -ne 0
    Write-Output ("{0}: Characteristics=0x{1:X4}, LAA={2}" -f [System.IO.Path]::GetFileName($f), $c, $laa)
} "C:\Program Files (x86)\Tocbien.com Forum\Warcraft III\war3.exe"
```
*If `LAA: False` (e.g. `Characteristics: 0x0103`), the executable cannot access >2 GB VAS.*

### 2. Read Crash Logs
```powershell
Get-ChildItem -Path "<GameDir>\Errors" -Filter "*.txt" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 3 FullName, LastWriteTime
Get-Content -Path "<LatestCrashFile>" | Select-Object -First 40
```

### 3. Check In-Game Video Settings (Registry)
```powershell
Get-ItemProperty -Path "HKCU:\Software\Blizzard Entertainment\Warcraft III\Video" |
    Select-Object reswidth, resheight, texquality, particles, animquality, lights, spellfilter
```
*(Values: 0 = Low, 1 = Medium, 2 = High)*

---

## Safe Fix Procedures

### Option 1: Apply Large Address Aware (4GB Patch) via PowerShell
Modifies the PE Characteristics flag to add `0x0020` without corrupting file alignment or digital signatures on legacy games.

```powershell
$target = "C:\Program Files (x86)\Tocbien.com Forum\Warcraft III\war3.exe"
$backup = "$target.bak"

# 1. Backup if not already backed up
if (-not (Test-Path $backup)) {
    Copy-Item -Path $target -Destination $backup
}

# 2. Read, patch, and write
$bytes = [System.IO.File]::ReadAllBytes($target)
$peOffset = [BitConverter]::ToInt32($bytes, 0x3C)
$charOffset = $peOffset + 22
$characteristics = [BitConverter]::ToUInt16($bytes, $charOffset)

if (($characteristics -band 0x20) -eq 0) {
    $newChar = $characteristics -bor 0x20
    $newCharBytes = [BitConverter]::GetBytes([uint16]$newChar)
    $bytes[$charOffset] = $newCharBytes[0]
    $bytes[$charOffset + 1] = $newCharBytes[1]
    [System.IO.File]::WriteAllBytes($target, $bytes)
    Write-Output "Patched successfully: 0x$($characteristics.ToString('X4')) -> 0x$($newChar.ToString('X4'))"
} else {
    Write-Output "Already LAA patched."
}
```

### Option 2: Lower Particle & Spell FX
Set `particles` and `spellfilter` to `0` (Low) or `1` (Medium) via Options -> Video or registry to reduce memory pressure during combat:
```powershell
Set-ItemProperty -Path "HKCU:\Software\Blizzard Entertainment\Warcraft III\Video" -Name "particles" -Value 1
Set-ItemProperty -Path "HKCU:\Software\Blizzard Entertainment\Warcraft III\Video" -Name "spellfilter" -Value 1
```

### Option 3: Custom Map Sanitization
Identify leaky maps (e.g. older DotA IMBA builds) and recommend newer revisions or clean maps with trigger cleanup routines (`DestroyGroup`, `RemoveLocation`, `DestroyEffect`).
