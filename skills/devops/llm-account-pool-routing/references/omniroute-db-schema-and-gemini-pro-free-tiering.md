# OmniRoute DB Schema & Gemini Pro/Free 5-Tier Worker Routing

## 1. SQLite Database Schema & Common Pitfalls
- **Database Path**: `C:/Users/Kibe/.omniroute/storage.sqlite` (or `~/.omniroute/storage.sqlite`).
- **Table Name Pitfall**: The table storing account connections is **`provider_connections`**, NOT `connections`. Querying `connections` directly throws `sqlite3.OperationalError: no such table: connections`.
- **Key Columns**:
  - `id`: UUID string identifying the connection (used in combo model configurations as `connectionId`).
  - `provider`: Provider identifier (e.g. `'antigravity'`, `'chatgpt-web'`, `'codex'`).
  - `name`: Display name or alias.
  - `email`: Associated account email.
  - `is_active`: 1 if active, 0 if disabled.
  - `provider_specific_data`: JSON payload for account metadata.
- **Active Connection Query**:
  ```sql
  SELECT id, provider, name, email, is_active 
  FROM provider_connections 
  WHERE provider = 'antigravity' AND is_active = 1;
  ```

---

## 2. Antigravity Account Tiering (16 Pro vs 87 Free)
Total active Antigravity connections: **103 accounts**.

### The 16 Pro Accounts
These 16 accounts form the primary tier (`ag-gemini-pool-3`):
1. `daa143cd-d115-4e27-ac8c-e4c8c2285992` (dokieu04092004@gmail.com)
2. `46f4803e-099b-4d1c-8300-1a879bbc76be` (marcusephillips52sns@gmail.com)
3. `651baa3b-14d6-42b7-ad95-c5232038f069` (dinhlan24072000@gmail.com)
4. `d8e4ee62-36c8-44d4-aed1-4cd253149860` (thanhdatbui19951@gmail.com)
5. `08f05410-4835-4299-95e5-a9aabb4deda2` (toloan12091999@gmail.com)
6. `76c815a9-7145-4a69-9a91-0b0b90a594bc` (jinrakal@gmail.com)
7. `d46fc313-a151-409e-acb3-d97ef4bcf24d` (minhan2745@gmail.com)
8. `e39362f2-c9db-4a21-9387-c3444d5cd056` (dangmy30011996@gmail.com)
9. `51b0d5b9-0f21-4ac4-b34c-65be588008f4` (dangmai31011996@gmail.com)
10. `f32bdf6d-c8a0-41d6-8423-57ac4267d963` (hoangthibaoanh300920023009@gmail.com)
11. `218efa02-dea2-4e3d-a856-ed7eff9600b9` (bobbyxruizz0s0o@gmail.com)
12. `29841101-4da0-4782-90aa-812dee3e9d9f` (duongkien12022001@gmail.com)
13. `2299f622-37d0-4f7b-8802-ec85555e9889` (phungthibichngoc180920011809@gmail.com)
14. `128db7e6-1ae9-4f05-9028-7c3f14fb6079` (lelinh09111997@gmail.com)
15. `db7adf17-10af-4141-b217-dcfb2efe3dad` (benghowelltpkf1@gmail.com)
16. `3ba9ae17-9365-488e-ae88-fd4c7dea0841` (nguyenkhoi14031998@gmail.com)

### The 87 Free Accounts
All other 87 active Antigravity accounts are standard/free accounts, designated for `ag-gemini-free-pool`.

---

## 3. 5-Tier Architecture in `omni-worker`
Instead of mixing Pro and Free into a flat round-robin (which causes quota dilution and early exhaustion of Pro slots), structure `omni-worker` into a 5-tier priority combo:

1. **Tier 1 (`ag-gemini-pool-3`)**: 16 Pro Accounts. Fast, high-quota Gemini 3.8 Flash tiered.
2. **Tier 2 (`ag-gemini-free-pool`)**: 87 Free Accounts. Handles burst volume when Tier 1 encounters temporary throttling.
3. **Tier 3 (`chatgpt-web-pool`)**: 12–16 live ChatGPT Web Accounts.
4. **Tier 4 (`omni-free`)**: Omni Free Tier safety net.
5. **Tier 5 (`ag-claude`)**: AG Claude Sonnet 4.6 ultimate fallback.

### Combo-Ref Element Format
```json
{
  "id": "omni-worker-ref-ag-gemini-free-pool",
  "kind": "combo-ref",
  "comboName": "ag-gemini-free-pool",
  "weight": 0,
  "label": "Tier 2: AG Gemini Free Pool (87 Accs Fallback)"
}
```

---

## 4. Verification and Backup Contract
Whenever updating combos:
1. Ensure `stickyRoundRobinLimit == 1` and `disableSessionStickiness == false` in all active combos.
2. Synchronize changes to `D:/Taadaa/AI-Tools/tools/omniroute/combos_backup.json`.
3. Verify test suite:
   ```bash
   python -m pytest "D:/Taadaa/AI-Tools/tests/test_omniroute_combos.py" -v
   ```
   Must pass 5/5.
