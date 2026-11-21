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
