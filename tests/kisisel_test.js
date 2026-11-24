// node tests/kisisel_test.js — personal settings (B5): normalize, settings code, digest ordering
const assert = require("assert");
const K = require("../piyasa/kisisel.js");
const d = K.defaults();
assert.ok(K.isDefault(d));
assert.strictEqual(K.encode(d), "1-01234-0n1n2n3n4n5n6n7n");
// round trip
const p = K.normalize({ sections: [{ id: "ozet" }, { id: "tl" }, { id: "daha", hide: true }],
  topics: [{ k: "Kripto", m: "on" }, { k: "Altın ve emtia", m: "on" }, { k: "Asya", m: "gizle" }] });
assert.deepStrictEqual(p.sections.map(s => s.id), ["ozet", "tl", "daha", "makro", "sorular"]);
assert.strictEqual(p.topics.length, 8);
const code = K.encode(p);
assert.strictEqual(code, "1-104h23-4o3o6g0n1n2n5n7n");
assert.deepStrictEqual(K.decode(code), p);
assert.ok(!K.isDefault(p));
// junk is rejected or cleaned
assert.strictEqual(K.decode("x"), null);
assert.strictEqual(K.decode("1-<script>-0o"), null);
const n = K.normalize({ sections: [{ id: "yok" }, { id: "tl" }, { id: "tl" }], topics: [{ k: "Kripto", m: "bilinmez" }] });
assert.deepStrictEqual(n.sections.map(s => s.id), ["tl", "ozet", "makro", "sorular", "daha"]);
assert.strictEqual(n.topics[0].m, "normal");
// at least one section always visible
const all = K.normalize({ sections: K.SECTIONS.map(s => ({ id: s.id, hide: true })) });
assert.strictEqual(all.sections.filter(s => !s.hide).length, 1);
// digest ordering: önde topics first in the visitor's order, then normal in their order, hidden apart
const items = [{ konu: "Türkiye", n: 1 }, { konu: "Asya", n: 2 }, { konu: "Altın ve emtia", n: 3 },
  { konu: "Kripto", n: 4 }, { konu: "Merkez bankaları", n: 5 }, { konu: "Bilinmeyen", n: 6 }, { konu: "Kripto", n: 7 }];
const r = K.sortItems(items, p);
assert.deepStrictEqual(r.shown.map(x => x.n), [4, 7, 3, 1, 5, 6]);
assert.deepStrictEqual(r.hidden.map(x => x.n), [2]);
// with defaults ozet.js does not sort at all (isDefault); sortItems itself groups by topic list order
assert.deepStrictEqual(K.sortItems(items, d).shown.map(x => x.n), [1, 5, 3, 4, 7, 2, 6]);
console.log("kisisel: ok");
