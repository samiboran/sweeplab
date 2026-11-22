// node tests/i18n_test.js — English formatting/translation of i18n.js (no browser needed)
const fs = require("fs"), vm = require("vm"), assert = require("assert");
const src = fs.readFileSync(__dirname + "/../piyasa/i18n.js", "utf8");
function load(search) {
  const ctx = { location: { search, pathname: "/piyasa/index.html", href: "http://x/piyasa/index.html" + search },
    document: { documentElement: { lang: "" }, querySelector: () => null, addEventListener: () => {} },
    MutationObserver: function () { this.observe = () => {}; }, WeakMap, Set, Object, RegExp, String, Array, URL };
  ctx.window = ctx;
  vm.runInNewContext(src, ctx);
  return ctx;
}
const tr = load("");
assert.strictEqual(tr.PHD_I18N.lang, "tr");
assert.strictEqual(tr.PHD_I18N.t("Kurallar"), "Kurallar");              // Turkish mode: untouched
const en = load("?lang=en");
const t = en.PHD_I18N.t;
assert.strictEqual(en.document.documentElement.lang, "en");
assert.strictEqual(t("Kurallar"), "Rules");
assert.strictEqual(t("−%4,4"), "−4.4%");
assert.strictEqual(t("5.715 TL"), "5,715 TL");
assert.strictEqual(t("4,2×"), "4.2×");
assert.strictEqual(t("19 Kasım 2026 — Makro hava: KIRMIZI"), "19 November 2026 — Macro weather: RED");
assert.strictEqual(t("Veri: 19 Kasım 2026 kapanışı · Kural sürümü v1 · Kayıt: canlı"), "Data: 19 November 2026 close · Rules v1 · Record: live");
assert.strictEqual(t("Hacim 20 günlük ortalamanın 4,2 katı"), "Volume 4.2× its 20-day average");
assert.strictEqual(t("Endeks −%2,0 iken +%11,0 (ters yön, 13,0 puan fark)"), "Index −2.0%, this name +11.0% (opposite direction, 13.0 pt gap)");
assert.strictEqual(t("Türkiye: 5 varlığın 1 tanesi 200 günlük ortalamasının üstünde."), "Türkiye: 1 of 5 assets are above their 200-day average.");
assert.strictEqual(t("20 Kas"), "20 Nov");
assert.strictEqual(t("v1.1"), "v1.1");                                    // versions untouched
assert.strictEqual(t("2026-11-22 06:27:32 UTC"), "2026-11-22 06:27:32 UTC"); // ISO dates untouched
// no recommendation words slipped into the English dictionary
const words = /\b(buy|sell|opportunity|cheap|target|don't miss|recommend(ed|ation)?)\b/i;
const strings = (src.match(/"(?:[^"\\]|\\.)*"/g) || []).join(" ").replace(/Not a ranking or a recommendation/g, "");
assert.ok(!words.test(strings), "action word in i18n.js strings");
console.log("i18n: ok");
