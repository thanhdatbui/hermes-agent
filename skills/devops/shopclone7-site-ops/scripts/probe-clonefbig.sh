#!/bin/bash
# Probe clonefbig API (doravo supplier id=1) và in sp khớp keyword — chạy TRÊN VPS (152.42.187.200).
# Không in api_key. Cách dùng: scp lên /tmp + ssh chạy, hoặc đặt sẵn trên VPS.
#   scp -i "$HOME/.ssh/doravo_deploy" probe-clonefbig.sh root@152.42.187.200:/tmp/ &&
#   ssh -i "$HOME/.ssh/doravo_deploy" root@152.42.187.200 'bash /tmp/probe-clonefbig.sh instagram; rm -f /tmp/probe-clonefbig.sh'
# Output: id<TAB>price<TAB>amount<TAB>category_id<TAB>name  (price = $ nguồn, amount = stock)
KW="${1:-}"
export MYSQL_PWD="$(awk -F= '/^DB_PASSWORD=/{print $2}' /root/.shopclone7_db_credentials)"
DB_HOST="$(awk -F= '/^DB_HOST=/{print $2}' /root/.shopclone7_db_credentials)"
DB_USER="$(awk -F= '/^DB_USER=/{print $2}' /root/.shopclone7_db_credentials)"
DB_NAME="$(awk -F= '/^DB_NAME=/{print $2}' /root/.shopclone7_db_credentials)"
KEY=$(mysql -h"$DB_HOST" -u"$DB_USER" "$DB_NAME" -N -e "SELECT api_key FROM suppliers WHERE id=1;")
curl -sS "https://clonefbig.com/api/products.php?api_key=$KEY" -o /tmp/cfb.json
python3 - "$KW" <<'PYEOF'
import json, sys
kw = sys.argv[1].lower()
d = json.load(open('/tmp/cfb.json'))
print("status:", d.get("status"), "| msg:", d.get("msg"))
for cat in d.get("categories", []):
    for p in cat.get("products", []):
        name = p.get("name","")
        if kw and kw not in name.lower():
            continue
        print(f"{p.get('id')}\t{p.get('price')}\t{p.get('amount')}\t{cat.get('id')}\t{name}")
PYEOF
rm -f /tmp/cfb.json
