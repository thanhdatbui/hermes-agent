# SHOPCLONE7 Deploy & Edit Topology

## File map (source: `D:\Taadaa\site ban hang clone\SHOPCLONE7`)
- Product auto-visibility on insert (NEW products): `cron/suppliers/xscr.php` (2 sites), `shopclone7.php` (2 sites), `shopmail.php` (2 sites). The gate:
  `$product_status = (isset($supplier['isAutoShow']) && $supplier['isAutoShow'] == 1) ? 1 : 0;`
  Set to `1` to always show new API products. Update path does NOT touch `status` (preserves existing).
- Telegram notifications (all 4 types): `libs/stock_alert.php`, called from `cron/cron.php` (lines ~83-92):
  `stockAlertCheck`, `sourcePriceAlertCheck`, `newApiProductAlertCheck`, `supplierBalanceAlertCheck`.
  Each builds an HTML-escaped `sprintf` body + a header. Fix un-accented Vietnamese there.
- Config that matters: `config.php` (role/perm maps, supplier-type list), `.env` (DB creds), `cron/cron.php` (orchestrates alert checks).

## Secret-safe `.env` handling on Windows (no credential leak)
- Print ONLY variable names: `grep -oE '^[A-Z_]+=' .env`
- Read a value into a shell var WITHOUT echoing it:
  `DBUSER=$(grep -i '^DB_USERNAME' .env | cut -d= -f2)` then use `$DBUSER` (never `echo` it).
- `python -m pip install pymysql` works if internet is up, but the VPS MySQL is firewalled — only useful if the DB is actually reachable.

## VPS access notes (this environment)
- `known_hosts` had `45.76.187.121` (host key changed → likely decommissioned/reinstalled) and `152.42.187.200` (reachable, `Permission denied` = no key). No SSH key/agent on dev machine.
- Deploy scripts (run ON the VPS): `scripts/deploy_shopclone7.sh`, `scripts/prepare_vps_ubuntu.sh`.
- To execute DB/code changes you need SSH to the VPS, OR hand the user the SQL (above) + @BotFather `/setname` for bot rename.

## Verify a deploy took effect
- Cron runs ~every 5 min. After deploy, a new API product gets `status=1`; the new-product alert shows `Trạng thái: Hiển thị`.
- Confirm live copy by matching the Telegram alert body text against the edited `libs/stock_alert.php`.
