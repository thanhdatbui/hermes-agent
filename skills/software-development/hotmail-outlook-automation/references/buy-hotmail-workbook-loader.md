# Hotmail OAuth2 Purchasing & Workbook Auto-Loader

## Scripts
- Canonical script: `D:\Taadaa\tools\buy_hotmail.py`
- Mirrored copy: `D:\Taadaa\AI-Tools\tools\buy_hotmail.py` (always sync after modifying the canonical script)

## Target Workbooks & Machine Ranges
- **Admin Workbook**: `D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx`
  - CLI flag: `--append-admin N`
  - Machine range: `201..280` (auto-balances to machines with fewest accounts)
- **Kibe Workbook**: `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`
  - CLI flag: `--append-kibe N`
  - Machine range: `1..80` (auto-balances to machines with fewest accounts)
  - Explicit machine targeting: `--target-machines "1,2,5"` overrides automatic balancing and assigns accounts to specified machines in order.

## Provider Architecture & Fallback
- Providers: `boxtaikhoan` (priority) -> `clonefbig` (fallback).
- Default mode: `--provider auto` (handles out of stock / insufficient balance / maintenance automatically).
- Verification: Verifies Microsoft Graph OAuth2 token validity by default before saving (disable with `--no-verify`).
