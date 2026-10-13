# Windows iCloud Photos Storage Relocation & Album Handling

## Problem & Background
Modern versions of **iCloud for Windows** (distributed via Microsoft Store, integrating with the Windows 10/11 Microsoft Photos app) do not expose a "Change..." folder button for iCloud Photos in the "Photo Settings" dialog, unlike iCloud Drive.
The photo download and sync path is hardcoded to:
`%USERPROFILE%\Pictures\iCloud Photos\Photos`

On systems where drive C (system SSD) has limited capacity (e.g. < 50 GB) while a secondary drive (e.g. drive D) has 1+ TB, syncing a large iCloud Photo library directly onto drive C causes rapid disk exhaustion and system instability.

## Technical Root Cause
Inspection of `C:\Program Files\WindowsApps\AppleInc.iCloud_*\iCloud\CloudPhotosProvider.dll` shows that iCloud queries the Windows Shell Known Folder subsystem for `FOLDERID_Pictures` (`{33E28130-4E1E-4676-835A-98395C3BC3BB}`). It binds its virtual sync root directly under whatever folder Windows identifies as the user's primary `Pictures` location.

## Reliable Relocation Workflow
To redirect iCloud Photos to a secondary drive (e.g. `D:\Pictures`), relocate the Windows `Pictures` Known Folder programmatically or via Registry + Shell API.

### Python / Win32 Automation Recipe
```python
import os, winreg, ctypes
from ctypes import wintypes

class GUID(ctypes.Structure):
    _fields_ = [
        ('Data1', ctypes.c_ulong),
        ('Data2', ctypes.c_ushort),
        ('Data3', ctypes.c_ushort),
        ('Data4', ctypes.c_ubyte * 8)
    ]

# FOLDERID_Pictures: {33E28130-4E1E-4676-835A-98395C3BC3BB}
FOLDERID_Pictures = GUID(
    0x33E28130, 0x4E1E, 0x4676,
    (ctypes.c_ubyte * 8)(0x83, 0x5A, 0x98, 0x39, 0x5C, 0x3B, 0xC3, 0xBB)
)

target_dir = r'D:\Pictures'
os.makedirs(target_dir, exist_ok=True)

# 1. Update Registry User Shell Folders
reg_path = r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE) as key:
    winreg.SetValueEx(key, 'My Pictures', 0, winreg.REG_EXPAND_SZ, target_dir)
    winreg.SetValueEx(key, '{0DDD015D-B061-47D5-852C-F0D1E46E3A6F}', 0, winreg.REG_EXPAND_SZ, target_dir)

# 2. Update Shell Folders (legacy compatibility)
try:
    reg_path2 = r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path2, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, 'My Pictures', 0, winreg.REG_SZ, target_dir)
except Exception:
    pass

# 3. Call Win32 SHSetKnownFolderPath
SHSetKnownFolderPath = ctypes.windll.shell32.SHSetKnownFolderPath
SHSetKnownFolderPath.argtypes = [
    ctypes.POINTER(GUID),
    wintypes.DWORD,
    wintypes.HANDLE,
    wintypes.LPCWSTR
]
SHSetKnownFolderPath.restype = ctypes.c_long
hr = SHSetKnownFolderPath(ctypes.byref(FOLDERID_Pictures), 0, None, target_dir)

# 4. Broadcast Shell Change Notifications
SHCNE_ASSOCCHANGED = 0x08000000
SHCNE_UPDATEITEM = 0x00002000
ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, 0, None, None)
ctypes.windll.shell32.SHChangeNotify(SHCNE_UPDATEITEM, 0, None, None)

# 5. Verification
SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
SHGetKnownFolderPath.argtypes = [
    ctypes.POINTER(GUID),
    wintypes.DWORD,
    wintypes.HANDLE,
    ctypes.POINTER(wintypes.LPWSTR)
]
SHGetKnownFolderPath.restype = ctypes.c_long

path_ptr = wintypes.LPWSTR()
hr_get = SHGetKnownFolderPath(ctypes.byref(FOLDERID_Pictures), 0, None, ctypes.byref(path_ptr))
if hr_get == 0:
    assert path_ptr.value == target_dir
    ctypes.windll.ole32.CoTaskMemFree(path_ptr)
```

## Postconditions & Verification
- After setting Known Folder to `D:\Pictures`, any newly initialized iCloud Photos sync creates its root at `D:\Pictures\iCloud Photos\Photos`.
- Existing photos already downloaded on C can be migrated or left as-is, saving system drive storage while directing future large downloads exclusively to D:.

## iCloud Photos Album Visibility & Fast Media Filtering in Windows File Dialogs
- **Limitation in File Pickers:** In standard Windows File Open Dialogs (`Chọn tài nguyên phương tiện`) or File Explorer, the `iCloud Photos\Photos` directory is completely flat. It dumps thousands of photos and videos into a single folder using hash/UUID filenames (e.g., `0F29741D-9A81-4194-A506-3360C1ED8557.mp4`). Apple Albums (such as "Ảnh bé", "Gia đình") exist only as cloud metadata tags, not physical subdirectories on NTFS.
- **Fast Album Selection Workflows:**
  1. **Web iCloud (`icloud.com/photos`)**: Browse directly to the specific Album on the web, select the required assets, and download them as a zip/batch into a dedicated local folder (e.g. `D:\Anh_Be`). Standard file dialogs can then point directly to this folder for instant selection.
  2. **Microsoft Photos App (`Microsoft.Windows.Photos`)**: Apple officially integrates album indexing with the Windows Photos app. The sidebar features an "iCloud Photos" section showing native albums, favorites, and timeline views.
