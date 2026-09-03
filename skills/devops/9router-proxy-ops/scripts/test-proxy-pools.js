// Test all 9Router proxy pools for liveness via curl -x, SEQUENTIAL.
// PITFALL (2026-08-14): use the RAW proxyUrl from DB verbatim. Do NOT normalize,
// decode, or re-encode — URLs are already percent-encoded (e.g. admin%401) and
// re-encoding mangles the password -> curl 56 connection reset -> false "DEAD".
// Run from C:\Users\Kibe\AppData\Roaming\npm\node_modules\9router\app so
// better-sqlite3 resolves, or require() the absolute module path.
// Usage: node test_proxy_pools.js
const { execFile } = require('child_process');
const Database = require('better-sqlite3'); // resolve from 9router app dir
const db = new Database('C:/Users/Kibe/AppData/Roaming/9router/db/data.sqlite', { readonly: true });

function curlTest(rawProxyUrl) {
  return new Promise((resolve) => {
    const c = execFile('curl', ['-s', '-x', rawProxyUrl, '--max-time', '15', 'https://api.ipify.org'],
      { encoding: 'utf8', maxBuffer: 1e6 }, (e, stdout) => {
        if (e) return resolve({ ok: false, err: e.code || 'ERR' });
        const s = (stdout || '').trim();
        if (/^\d+\.\d+\.\d+\.\d+/.test(s)) return resolve({ ok: true, ip: s });
        return resolve({ ok: false, err: 'no-ip:' + s.slice(0, 30) });
      });
    setTimeout(() => { c.kill(); resolve({ ok: false, err: 'timeout' }); }, 18000);
  });
}

(async () => {
  const rows = db.prepare('SELECT id, data FROM proxyPools').all();
  const jobs = rows.map(r => {
    let d = {}; try { d = JSON.parse(r.data); } catch (e) {}
    return { id: r.id, name: d.name || '?', raw: d.proxyUrl };
  });
  const alive = [], dead = [];
  // SEQUENTIAL — parallel testing trips the farm's rate limits (mass 503/429).
  for (let i = 0; i < jobs.length; i++) {
    const j = jobs[i];
    const res = await curlTest(j.raw);
    if (res.ok) { alive.push(j); console.log('ALIVE  ' + j.name + ' (' + j.raw + ') -> ' + res.ip); }
    else { dead.push({ ...j, err: res.err }); console.log('DEAD   ' + j.name + ' -> ' + res.err); }
    await new Promise(r => setTimeout(r, 300));
  }
  console.log('\n=== SUMMARY: ALIVE ' + alive.length + ' / DEAD ' + dead.length + ' ===');
  dead.forEach(d => console.log('  DEAD ' + d.name + ' | ' + d.raw + ' | ' + d.err));
  console.log('\ncurl exit-code legend: 56=connection reset (proxy down/refused), 28=timeout, 5=URL parse fail (BAD FORMAT, not dead proxy)');
})();
