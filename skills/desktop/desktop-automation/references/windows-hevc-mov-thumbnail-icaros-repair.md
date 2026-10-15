# Windows Explorer Thumbnail Fix for iPhone Media (.MOV HEVC, .HEIC, .M4V) via Icaros Shell Extensions

## Problem
Files recorded on modern iPhones (iOS) use HEVC (H.265) compression for `.MOV` videos and HEIF for `.HEIC` photos.
When synced to Windows via iCloud Photos, OneDrive, or USB cable, Windows Explorer displays generic blank or application icons (e.g., VLC, Windows Media Player) instead of video/photo preview thumbnails.

Root causes:
1. Windows 10/11 does not bundle a free HEVC hardware decode filter in Explorer.
2. The default Windows thumbnail provider (`{9DBD2C50-62AD-11D0-B806-00C04FD706EC}`) cannot parse HEVC streams inside QuickTime `.MOV` containers.
3. Third-party media players (like VLC) register file associations (`.mov -> VLC.mov`) but do NOT implement `IThumbnailProvider` (`{e357fccd-a995-4576-b01f-234630154e96}`) or `IExtractImage` (`{BB2E617C-0920-11D1-9A0B-00C04FC2D6C1}`), leaving thumbnail generation unhandled.

---

## Architecture: Icaros Shell Extensions

Icaros (`C:\Program Files\Icaros\` or bundled with K-Lite Codec Pack) is an FFmpeg-backed Windows Shell Extension framework.
- **CLSID:** `{c5aec3ec-e812-4677-a9a7-4fee1f9aa000}` (Icaros Thumbnail Provider)
- **64-bit DLL:** `C:\Program Files\Icaros\64-bit\IcarosThumbnailProvider.dll`
- **Supported Codecs/Containers:** HEVC/H.265, H.264, VP9, AV1, ProRes inside MOV, MP4, MKV, WebM, etc.

Often Icaros is already installed on Windows systems (e.g., when K-Lite Codec Pack is installed), but by default it is only registered for `.mkv;.mk3d;.webm;.ogm;.ogv;.flv;.rm;.rmvb`.

---

## Non-Admin User-Level Registration (HKCU Precedence)

Windows Explorer merges `HKEY_CURRENT_USER\Software\Classes` and `HKEY_LOCAL_MACHINE\Software\Classes` into `HKEY_CLASSES_ROOT` (`HKCR`).
**`HKCU` entries take strict precedence over `HKLM` entries.**

Therefore, any standard user process (no UAC / no Administrator elevation required) can override the thumbnail handler for any file extension by writing to `HKCU`.

### Registry Keys to Set
For each target extension (e.g. `.mov`, `.heic`, `.m4v`):

```
HKCU\Software\Classes\<ext>\ShellEx\{e357fccd-a995-4576-b01f-234630154e96}  = {c5aec3ec-e812-4677-a9a7-4fee1f9aa000}
HKCU\Software\Classes\<ext>\ShellEx\{BB2E617C-0920-11D1-9A0B-00C04FC2D6C1}  = {c5aec3ec-e812-4677-a9a7-4fee1f9aa000}
HKCU\Software\Classes\SystemFileAssociations\<ext>\ShellEx\{e357fccd-a995-4576-b01f-234630154e96} = {c5aec3ec-e812-4677-a9a7-4fee1f9aa000}
HKCU\Software\Classes\SystemFileAssociations\<ext>\ShellEx\{BB2E617C-0920-11D1-9A0B-00C04FC2D6C1} = {c5aec3ec-e812-4677-a9a7-4fee1f9aa000}
```

Also append the extension to:
`HKCU\Software\Icaros` -> `Thumbnail Extensions` (string, semicolon-separated).

---

## Automated Python Remediation Recipe

This script runs completely unelevated, requires no third-party Python packages, and takes effect instantly:

```python
import winreg
import ctypes

ICAROS_CLSID = "{c5aec3ec-e812-4677-a9a7-4fee1f9aa000}"
ITHUMBNAILPROVIDER = "{e357fccd-a995-4576-b01f-234630154e96}"
IEXTRACTIMAGE = "{BB2E617C-0920-11D1-9A0B-00C04FC2D6C1}"

EXTENSIONS = [".mov", ".heic", ".m4v"]

def set_val(root, subkey, name, val):
    with winreg.CreateKey(root, subkey) as k:
        winreg.SetValueEx(k, name, 0, winreg.REG_SZ, val)

for ext in EXTENSIONS:
    keys = [
        rf"Software\Classes\{ext}\ShellEx\{ITHUMBNAILPROVIDER}",
        rf"Software\Classes\{ext}\ShellEx\{IEXTRACTIMAGE}",
        rf"Software\Classes\SystemFileAssociations\{ext}\ShellEx\{ITHUMBNAILPROVIDER}",
        rf"Software\Classes\SystemFileAssociations\{ext}\ShellEx\{IEXTRACTIMAGE}",
    ]
    for key_path in keys:
        set_val(winreg.HKEY_CURRENT_USER, key_path, "", ICAROS_CLSID)

# Update Icaros config in HKCU
try:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Icaros") as k:
        try:
            curr, _ = winreg.QueryValueEx(k, "Thumbnail Extensions")
        except FileNotFoundError:
            curr = ""
        items = set(x.strip().lower() for x in curr.split(";") if x.strip())
        items.update(EXTENSIONS)
        winreg.SetValueEx(k, "Thumbnail Extensions", 0, winreg.REG_SZ, ";".join(sorted(items)))
except Exception as e:
    print(f"Warning updating Icaros list: {e}")

# Broadcast association update to Windows Shell (SHCNE_ASSOCCHANGED = 0x08000000)
ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
print("Successfully registered Icaros thumbnail provider and notified Windows Explorer!")
```

---

## Verification
1. Check `HKCR\.mov\ShellEx\{e357fccd-a995-4576-b01f-234630154e96}`: confirms value is `{c5aec3ec-e812-4677-a9a7-4fee1f9aa000}`.
2. Open target directory (e.g. `Pictures\iCloud Photos\Photos`) in Windows Explorer or press F5: thumbnails render immediately from the first video frame.
