# OmniRoute Combo Patch API

Port `:20129`. All combo management via REST, not the browser UI (`/admin/combos` returns 404).

## Endpoints

| Action | Method | URL |
|--------|--------|-----|
| List all combos | GET | `/api/combos` |
| Get one combo | GET | `/api/combos/<id>` |
| Update combo (full replace) | PUT | `/api/combos/<id>` |
| Update combo (partial) | PATCH | `/api/combos/<id>` |

## Response shape

```json
{
  "id": "...",
  "name": "ag-gemini-pool-3",
  "models": [...],
  "strategy": "...",
  "isActive": true,
  "isHidden": false,
  "sortOrder": 0,
  "createdAt": "...",
  "updatedAt": "...",
  "version": 1
}
```

## Model entry shape (kind=model)

```json
{
  "id": "<combo-name>-model-N-<provider>-<model-slug>-<connectionId>",
  "kind": "model",
  "model": "antigravity/gemini-3.7-flash-high",
  "providerId": "antigravity",
  "connectionId": "<uuid>",
  "weight": 0,
  "label": "pool-1"
}
```

## Patch a combo's model strings (bulk sed pattern)

```bash
COMBO_ID="<uuid>"
curl -s "http://localhost:20129/api/combos/$COMBO_ID" | python -c "
import sys, json
d = json.load(sys.stdin)
for m in d.get('models', []):
    if isinstance(m, dict) and 'model' in m:
        m['model'] = m['model'].replace('OLD_MODEL', 'NEW_MODEL')
print(json.dumps(d))
" | curl -s -X PUT "http://localhost:20129/api/combos/$COMBO_ID" \
  -H "Content-Type: application/json" \
  -d @- | python -c "
import sys, json
d = json.load(sys.stdin)
print('isActive:', d.get('isActive'))
bad = [m['model'] for m in d.get('models',[]) if 'OLD_MODEL' in m.get('model','')]
print('Still old:', bad or 'None — OK')
"
```

## Activate / deactivate

PUT replaces the full document and can change `isActive` together with other fields.
PATCH does partial updates — use it when only toggling `isActive`:

```bash
curl -s -X PATCH "http://localhost:20129/api/combos/$COMBO_ID" \
  -H "Content-Type: application/json" \
  -d '{"isActive": true}' | python -c "import sys,json; print(json.load(sys.stdin).get('isActive'))"
```

Note: `/api/combos/<id>/activate` does NOT exist (returns `unknown_route` 404).

## Find combo ID by name

```bash
curl -s http://localhost:20129/api/combos | python -c "
import sys, json
d = json.load(sys.stdin)
for c in d['combos']:
    if 'gemini' in c.get('name','').lower():
        print(c['id'], c['name'])
"
```

## Pitfalls

- `GET /api/combos` returns `{"combos": [...], "total": N}`, not a bare array.
- PUT with `isActive` field in the body is IGNORED sometimes (returns `isActive: None`). Use PATCH separately if PUT does not stick.
- After a bulk model-string replace via PUT, verify with a fresh GET — the response from PUT may lag.
- Combos that are `combo-ref` (kind=combo-ref) reference other combos by name, not by model string. No model-string patching needed for those — fix the referenced combo and they pick it up automatically.
- `ag-claude` and `ag-opus` both use `ag-gemini-pool-3` as a fallback via `combo-ref` — fixing the pool combo fixes all consumers automatically.
