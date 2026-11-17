"""One-shot repair of cp1252/latin1 mojibake in Hermes state.db.

Usage:
  python scripts/repair_mojibake_db.py [--db PATH] [--since EPOCH] [--apply]

Without --apply it is a dry run.  With --apply, every original value is first
written to a JSONL backup (id, table, column, old) so the change is reversible.
FTS (messages_fts / messages_fts_trigram) is refreshed by the existing
AFTER UPDATE triggers on messages.content/tool_calls.
"""
import argparse, json, os, sqlite3, sys, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.mojibake import repair_mojibake  # noqa: E402

def repair_value(val):
    """Repair plain text, and also mojibake hidden behind JSON unicode escapes
    (tool_calls / tool results stored with ensure_ascii=True)."""
    new = repair_mojibake(val)
    if new != val:
        return new
    st = val.lstrip()
    if st[:1] in "[{" and r"\u00" in val:
        try:
            obj = json.loads(val)
        except ValueError:
            return val
        def walk(o):
            if isinstance(o, str):
                fixed = repair_mojibake(o)
                if fixed != o:
                    return fixed
                s2 = o.lstrip()
                if s2[:1] in "[{":  # nested JSON string, e.g. function.arguments
                    try:
                        inner = json.loads(o)
                    except ValueError:
                        return o
                    w = walk(inner)
                    if w != inner:
                        return json.dumps(w, ensure_ascii=not any(ord(c) > 127 for c in o))
                return o
            if isinstance(o, list):
                return [walk(x) for x in o]
            if isinstance(o, dict):
                return {k: walk(v) for k, v in o.items()}
            return o
        fixed = walk(obj)
        if fixed != obj:
            return json.dumps(fixed, ensure_ascii=not any(ord(c) > 127 for c in val))
    return val


MSG_COLS = ("content", "tool_calls", "api_content", "reasoning", "reasoning_content")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.expandvars(r"%LOCALAPPDATA%\hermes\state.db"))
    ap.add_argument("--since", type=float, default=0.0)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--verbose", type=int, default=0, help="print N earliest changes")
    a = ap.parse_args()

    # Step 1: open the DB and collect every value that needs repair.
    con = sqlite3.connect(a.db, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    have = {r[1] for r in con.execute("PRAGMA table_info(messages)")}
    cols = [c for c in MSG_COLS if c in have]
    changes = []  # (table, id, col, old, new)
    q = f"SELECT id, {', '.join(cols)} FROM messages WHERE timestamp >= ?"
    for row in con.execute(q, (a.since,)):
        for col, val in zip(cols, row[1:]):
            if isinstance(val, str) and val:
                new = repair_value(val)
                if new != val:
                    changes.append(("messages", row[0], col, val, new))
    scols = {r[1] for r in con.execute("PRAGMA table_info(sessions)")}
    if "title" in scols:
        tcol = "started_at" if "started_at" in scols else None
        sq = "SELECT id, title FROM sessions" + (f" WHERE {tcol} >= ?" if tcol else "")
        for sid, title in con.execute(sq, (a.since,) if tcol else ()):
            if isinstance(title, str) and title:
                new = repair_mojibake(title)
                if new != title:
                    changes.append(("sessions", sid, "title", title, new))

    # Step 2: report (dry run stops here).
    rows = {(t, i) for t, i, *_ in changes}
    print(f"{len(changes)} values in {len(rows)} rows need repair")
    if a.verbose:
        tmap = dict(con.execute("SELECT id, timestamp FROM messages WHERE id IN (%s)" % ",".join(str(i) for t, i, *_ in changes if t == "messages") or "0").fetchall()) if changes else {}
        for t, i, col, old, new in sorted(changes, key=lambda c: tmap.get(c[1], 0))[:a.verbose]:
            print(time.strftime("%m-%d %H:%M:%S", time.localtime(tmap.get(i, 0))), t, i, col, repr(old[:100]))
    if not a.apply or not changes:
        return
    # Step 3: back up the originals, then apply in one transaction.
    backup = os.path.join(os.path.dirname(os.path.realpath(a.db)),
                          f"mojibake_backup_{int(time.time())}.jsonl")
    with open(backup, "w", encoding="utf-8") as f:
        for t, i, col, old, _ in changes:
            f.write(json.dumps({"table": t, "id": i, "column": col, "old": old}, ensure_ascii=False) + "\n")
    with con:
        for t, i, col, _, new in changes:
            con.execute(f"UPDATE {t} SET {col} = ? WHERE id = ?", (new, i))
    print(f"applied; backup: {backup}")


if __name__ == "__main__":
    main()
