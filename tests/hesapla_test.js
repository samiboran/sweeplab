// node tests/hesapla_test.js — position calculator unit tests (S4d)
const assert = require("assert");
const C = require("../piyasa/hesapla-core.js");
const close = (a, b, eps) => assert.ok(Math.abs(a - b) < eps, `${a} != ${b}`);

// spec: cost 102 TL/gram silver -> breakeven ounce at USDTRY 50.58 ≈ $62.7, at 60 ≈ $52.9
close(C.breakevenOunceUsd(102, 50.58), 62.7, 0.05);
close(C.breakevenOunceUsd(102, 60), 52.9, 0.05);

const p = { usdtry: 50.58, gram_gumus_tl: 85, gram_altin_tl: 6000, btc_usd: 60000, bist100_tl: 10000 };
const r = C.compute("gram_gumus", 102, "TL", 10, p);
close(r.plPct, (85 / 102 - 1) * 100, 1e-9);
close(r.toBreakevenPct, (102 / 85 - 1) * 100, 1e-9);
close(r.value, 850, 1e-9);
close(r.scenarios[0].breakevenUsd, 62.72, 0.01);
assert.strictEqual(r.scenarios[0].breakevenUsdUnit, "ons");
close(r.scenarios[2].usdtry, 50.58 * 1.2, 1e-9);
// TL value with silver USD price unchanged and +10% USDTRY -> +10%
close(r.scenarios[1].valueTl, 850 * 1.1, 1e-6);

// BTC priced in USD, cost entered in USD
const b = C.compute("btc", 50000, "USD", 0.5, p);
close(b.plPct, 20, 1e-9);
close(b.scenarios[1].breakevenTl, 50000 * 50.58 * 1.1, 1e-6);
// BTC with TL cost
const bt = C.compute("btc", 3000000, "TL", 1, p);
close(bt.price, 60000 * 50.58, 1e-6);

// dolar and BIST 100 are TL-only
assert.strictEqual(C.compute("dolar", 40, "USD", 100, p).ccy, "TL");
assert.strictEqual(C.compute("bist100", 9000, "TL", 1, p).scenarios[1].valueTl, null);

// invalid input
assert.strictEqual(C.compute("gram_altin", 0, "TL", 1, p), null);
assert.strictEqual(C.compute("gram_altin", 100, "TL", -1, p), null);
assert.strictEqual(C.compute("yok", 100, "TL", 1, p), null);
assert.strictEqual(C.compute("eth", 100, "TL", 1, p), null); // no ETH price
console.log("hesapla: ok");

// spread (makas): sell 3000, buy 2940 -> 2%
close(C.spreadFromPrices(3000, 2940), 2, 1e-9);
assert.strictEqual(C.spreadFromPrices(2940, 3000), null);
const rs = C.compute("gram_altin", 5800, "TL", 10, { usdtry: 50, gram_altin_tl: 6000 }, 2);
close(rs.netValue, 60000 * 0.98, 1e-6);
close(rs.netPl, 58800 - 58000, 1e-6);
close(rs.netBreakeven, 5800 / 0.98, 1e-9);
close(rs.netToBreakevenPct, (5800 / 0.98 / 6000 - 1) * 100, 1e-9);
assert.strictEqual(C.compute("gram_altin", 5800, "TL", 10, { usdtry: 50, gram_altin_tl: 6000 }).spreadPct, undefined);
console.log("hesapla spread: ok");

// several purchases: 5 g @ 5000 + 3 g @ 6000 -> 8 g @ 5375
const av = C.averageLots([[5, 5000], [3, 6000], [0, 999], ["x", 1]]);
assert.strictEqual(av.amount, 8); close(av.cost, 5375, 1e-9); assert.strictEqual(av.rows, 2);
assert.strictEqual(C.averageLots([]), null);
// custom asset (çeyrek): user-entered price, TL only, no TL scenario values
const cq = C.compute("diger", 9000, "USD", 2, { usdtry: 50, custom_tl: 9900 });
assert.strictEqual(cq.ccy, "TL"); close(cq.plPct, 10, 1e-9); assert.strictEqual(cq.scenarios[1].valueTl, null);
assert.strictEqual(C.compute("diger", 9000, "TL", 2, { usdtry: 50 }), null);
console.log("hesapla lots/custom: ok");

// saved positions: v2 single object -> list of one; v3 kept; junk dropped; cur clamped
let st = C.normalizeStore({ v: 2, a: "gram_altin", m: 5000, q: 2 });
assert.strictEqual(st.list.length, 1); assert.strictEqual(st.cur, 0);
st = C.normalizeStore({ v: 3, list: [{ a: "dolar" }, { a: "nope" }, { a: "gram_gumus" }], cur: 7 });
assert.deepStrictEqual(st.list.map(x => x.a), ["dolar", "gram_gumus"]); assert.strictEqual(st.cur, 0);
assert.strictEqual(C.normalizeStore(null).list.length, 0);
console.log("hesapla store: ok");

