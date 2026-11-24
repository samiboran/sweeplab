/* Piyasa Hava Durumu — "Kişisel ayar" (B5). No accounts: the visitor's choice of section order and
   news-topic priority is stored only in this browser (localStorage, try/catch) and never sent anywhere.
   An "ayar kodu" (short code / #k= link; the hash never reaches a server) moves the settings to another device.
   Used by index.html (reorders sections, ozet.js sorts the digest) and ayarlar.html (the editor).
   DOM APIs only; no HTML parsing. Pure helpers are exported for node tests (tests/kisisel_test.js). */
(function (root) {
  "use strict";
  var KEY = "phd-kisisel-v1";
  // home-page sections the visitor can order or hide (ids of the wrappers in index.html)
  // listed in the page's default order; n = fixed digit in the ayar kodu (never reuse or renumber)
  var SECTIONS = [
    { id: "tl", n: 0, el: "s-tl", tr: "TL tarafı", en: "The lira side" },
    { id: "zincir", n: 5, el: "s-zincir", tr: "Zincir (petrolden bitcoine)", en: "The chain (oil to bitcoin)" },
    { id: "ozet", n: 1, el: "s-ozet", tr: "Günün özeti", en: "Today's digest" },
    { id: "makro", n: 2, el: "s-makro", tr: "Makro hava ve kurallar", en: "Macro weather and rules" },
    { id: "sorular", n: 3, el: "s-sor", tr: "Sorular", en: "Questions" },
    { id: "daha", n: 4, el: "s-daha", tr: "Daha fazlası", en: "More" }
  ];
  function secByN(n) { return SECTIONS.filter(function (x) { return x.n === n; })[0]; }
  // fixed digest topics (docs/OZET_SCHEMA.md)
  var TOPICS = [
    { k: "Türkiye", en: "Türkiye" },
    { k: "Merkez bankaları", en: "Central banks" },
    { k: "Dünya ekonomisi", en: "World economy" },
    { k: "Altın ve emtia", en: "Gold and commodities" },
    { k: "Kripto", en: "Crypto" },
    { k: "Şirketler", en: "Companies" },
    { k: "Asya", en: "Asia" },
    { k: "Latin Amerika", en: "Latin America" }
  ];
  var MODES = ["on", "normal", "gizle"];          // önde / normal / gizle
  var MCH = { on: "o", normal: "n", gizle: "g" };
  var CHM = { o: "on", n: "normal", g: "gizle" };

  function defaults() {
    return {
      v: 1,
      sections: SECTIONS.map(function (s) { return { id: s.id, hide: false }; }),
      topics: TOPICS.map(function (t) { return { k: t.k, m: "normal" }; })
    };
  }
  // keep known ids once each, in the given order; append anything missing with its default
  function normalize(p) {
    var d = defaults();
    if (!p || typeof p !== "object") return d;
    var out = { v: 1, sections: [], topics: [] }, seen = {};
    (Array.isArray(p.sections) ? p.sections : []).forEach(function (s) {
      if (!s || seen["s" + s.id] || !SECTIONS.some(function (x) { return x.id === s.id; })) return;
      seen["s" + s.id] = 1; out.sections.push({ id: s.id, hide: s.hide === true });
    });
    d.sections.forEach(function (s) { if (!seen["s" + s.id]) out.sections.push(s); });
    (Array.isArray(p.topics) ? p.topics : []).forEach(function (t) {
      if (!t || seen["t" + t.k] || !TOPICS.some(function (x) { return x.k === t.k; })) return;
      seen["t" + t.k] = 1; out.topics.push({ k: t.k, m: MODES.indexOf(t.m) >= 0 ? t.m : "normal" });
    });
    d.topics.forEach(function (t) { if (!seen["t" + t.k]) out.topics.push(t); });
    if (out.sections.every(function (s) { return s.hide; })) out.sections[0].hide = false;   // never an empty page
    return out;
  }
  function isDefault(p) { return encode(normalize(p)) === encode(defaults()); }

  // ayar kodu: "1-" + sections (index digit, "h" if hidden) + "-" + topics (index digit + o/n/g)
  function encode(p) {
    p = normalize(p);
    var s = p.sections.map(function (x) {
      var n = SECTIONS.filter(function (y) { return y.id === x.id; })[0].n;
      return n + (x.hide ? "h" : "");
    }).join("");
    var t = p.topics.map(function (x) {
      var i = TOPICS.map(function (y) { return y.k; }).indexOf(x.k);
      return i + MCH[x.m];
    }).join("");
    return "1-" + s + "-" + t;
  }
  function decode(code) {
    var m = /^1-((?:[0-9]h?){1,10})-((?:[0-9][ong]){1,20})$/.exec(String(code || "").trim());
    if (!m) return null;
    var sections = [], topics = [];
    m[1].replace(/([0-9])(h?)/g, function (_, i, h) {
      var sec = secByN(+i);
      if (sec) sections.push({ id: sec.id, hide: h === "h" });
      return "";
    });
    m[2].replace(/([0-9])([ong])/g, function (_, i, c) {
      if (TOPICS[+i]) topics.push({ k: TOPICS[+i].k, m: CHM[c] });
      return "";
    });
    return normalize({ sections: sections, topics: topics });
  }

  // digest items -> { shown: [...] (önde first, then normal; each by the visitor's topic order), hidden: [...] }
  function sortItems(items, p) {
    p = normalize(p);
    var rank = {}, mode = {};
    p.topics.forEach(function (t, i) { rank[t.k] = i; mode[t.k] = t.m; });
    var shown = [], hidden = [];
    (items || []).forEach(function (it, i) {
      var k = it && it.konu, m = mode[k] || "normal";
      var row = { it: it, i: i, g: m === "on" ? 0 : 1, r: k in rank ? rank[k] : 99 };
      (m === "gizle" ? hidden : shown).push(row);
    });
    shown.sort(function (a, b) { return a.g - b.g || a.r - b.r || a.i - b.i; });
    hidden.sort(function (a, b) { return a.r - b.r || a.i - b.i; });
    return { shown: shown.map(function (x) { return x.it; }), hidden: hidden.map(function (x) { return x.it; }) };
  }

  function load() {
    var raw = null;
    try { raw = root.localStorage && root.localStorage.getItem(KEY); } catch (e) { raw = null; }
    if (!raw) return null;
    try { return normalize(JSON.parse(raw)); } catch (e) { return null; }
  }
  function save(p) {
    try { root.localStorage.setItem(KEY, JSON.stringify(normalize(p))); return true; } catch (e) { return false; }
  }
  function clear() {
    try { root.localStorage.removeItem(KEY); return true; } catch (e) { return false; }
  }

  var API = { KEY: KEY, SECTIONS: SECTIONS, TOPICS: TOPICS, MODES: MODES, defaults: defaults, normalize: normalize,
    isDefault: isDefault, encode: encode, decode: decode, sortItems: sortItems, load: load, save: save, clear: clear };
  if (typeof module !== "undefined" && module.exports) { module.exports = API; return; }
  root.PHD_KISISEL = API;

  // ---- home page: reorder sections (only when the visitor saved settings) ----
  var doc = root.document;
  var main = doc && doc.getElementById("main");
  if (!main || !doc.getElementById("s-makro")) return;
  var p = load();
  var EN = !!(root.PHD_I18N && root.PHD_I18N.en);
  function L(tr, en) { return EN ? en : tr; }
  function el(tag, cls, text) {
    var e = doc.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = String(text);
    if (EN) e.setAttribute("data-noi18n", "");
    return e;
  }
  if (!p || isDefault(p)) return;          // default page: nothing changes (link lives in nav + "Daha fazlası")
  var bar = el("p", "kis-bar mute small");
  {
    var hidden = [];
    p.sections.forEach(function (s) {
      var spec = SECTIONS.filter(function (x) { return x.id === s.id; })[0];
      var node = spec && doc.getElementById(spec.el);
      if (!node) return;
      if (s.hide) hidden.push(node); else main.appendChild(node);
    });
    if (hidden.length) {
      var det = el("details", "detail kis-gizli");
      det.id = "s-gizli";
      det.appendChild(el("summary", null, L("Gizlediğin bölümler (" + hidden.length + ")", "Sections you hid (" + hidden.length + ")")));
      hidden.forEach(function (n) { det.appendChild(n); });
      main.appendChild(det);
    }
    bar.appendChild(doc.createTextNode(L("Sayfa senin sıranla gösteriliyor (yalnız bu cihazda). ", "This page follows your order (on this device only). ")));
  }
  var a = el("a", null, L("Sayfanı düzenle", "Edit your page"));
  a.href = "ayarlar.html" + (EN ? "?lang=en" : "");
  bar.appendChild(a);
  var top = doc.getElementById("macro-line");
  if (top && top.nextSibling) main.insertBefore(bar, top.nextSibling); else main.insertBefore(bar, main.firstChild);
})(typeof window !== "undefined" ? window : this);
