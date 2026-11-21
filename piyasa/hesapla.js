/* Piyasa Hava Durumu — position calculator UI (S4c).
   User input never leaves the device: the only request is the public tl.json (no user data).
   localStorage only when "Bu cihazda hatırla" is ticked. DOM APIs only. */
(function () {
  "use strict";
  var C = window.PHDCalc;
  var RAW = "https://raw.githubusercontent.com/samiboran/sweeplab/data-feed/data/site/";
  var DATA = /\.github\.io$/.test(location.hostname) ? RAW : "data/site/";
  var KEY = "phd-hesapla-v1";
  var MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
  var P = null;

  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = String(text);
    return e;
  }
  function num(v, nd) {
    if (typeof v !== "number" || !isFinite(v)) return "—";
    return v.toLocaleString("tr-TR", { minimumFractionDigits: nd, maximumFractionDigits: nd });
  }
  function signedPct(v) { return (v > 0 ? "+" : v < 0 ? "−" : "") + "%" + num(Math.abs(v), 2); }
  function parse(s) {
    s = String(s || "").trim().replace(/\s/g, "");
    if (/,/.test(s)) s = s.replace(/\./g, "").replace(",", ".");   // 1.234,56 -> 1234.56
    var v = parseFloat(s);
    return isFinite(v) ? v : NaN;
  }
  function trDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
    return m ? (+m[3]) + " " + MONTHS[+m[2] - 1] + " " + m[1] : "—";
  }
  function ccy() {
    var r = document.querySelector('input[name="ccy"]:checked');
    return r ? r.value : "TL";
  }
  function money(v, c) { return num(v, Math.abs(v) < 10 ? 4 : 2) + (c === "USD" ? " $" : " TL"); }

  function row(tb, label, value, cls) {
    var tr = el("tr");
    tr.appendChild(el("th", null, label));
    var td = el("td", cls || null, value);
    tr.appendChild(td);
    tb.appendChild(tr);
  }

  function save() {
    try {
      if ($("hatirla").checked) {
        localStorage.setItem(KEY, JSON.stringify({ a: $("varlik").value, c: ccy(), m: $("maliyet").value, q: $("miktar").value }));
      } else {
        localStorage.removeItem(KEY);
      }
    } catch (e) { /* storage unavailable: ignore */ }
  }
  function load() {
    try {
      var s = JSON.parse(localStorage.getItem(KEY) || "null");
      if (!s) return;
      if (C.ASSETS[s.a]) $("varlik").value = s.a;
      Array.prototype.forEach.call(document.querySelectorAll('input[name="ccy"]'), function (r) { r.checked = r.value === s.c; });
      $("maliyet").value = String(s.m || "").slice(0, 32);
      $("miktar").value = String(s.q || "").slice(0, 32);
      $("hatirla").checked = true;
    } catch (e) { /* ignore */ }
  }

  function update() {
    var a = $("varlik").value, A = C.ASSETS[a];
    var tlOnly = !!(A && A.tlOnly);
    $("ccy-set").hidden = tlOnly;
    var c = tlOnly ? "TL" : ccy();
    $("maliyet-label").textContent = "Ortalama maliyet (" + (c === "USD" ? "dolar" : "TL") + " / " + A.unit + ")";
    $("miktar-label").textContent = "Miktar (" + A.unit + ")";
    save();
    var out = $("sonuc");
    out.textContent = "";
    if (!P) return;
    var r = C.compute(a, parse($("maliyet").value), c, parse($("miktar").value), P);
    if (!r) {
      if ($("maliyet").value || $("miktar").value) out.appendChild(el("p", "mute small", "Maliyet ve miktarı sıfırdan büyük sayı olarak gir. Bu varlık için güncel fiyat yoksa hesap yapılamaz."));
      return;
    }
    out.appendChild(el("p", "label", "Sonuç"));
    var pl = el("p", "big" + (r.plPct < 0 ? " neg" : ""), signedPct(r.plPct));
    out.appendChild(pl);
    var t = el("table"), tb = el("tbody");
    row(tb, "Güncel fiyat (" + r.unit + ")", money(r.price, r.ccy));
    row(tb, "Toplam maliyet", money(r.costTotal, r.ccy));
    row(tb, "Güncel değer", money(r.value, r.ccy));
    row(tb, "Kâr / zarar", (r.pl < 0 ? "−" : "+") + money(Math.abs(r.pl), r.ccy), r.pl < 0 ? "neg" : null);
    row(tb, "Başabaş fiyatı (" + r.unit + ")", money(r.breakeven, r.ccy));
    row(tb, "Başabaşa uzaklık", r.toBreakevenPct <= 0 ? "Başabaşın üzerinde" : signedPct(r.toBreakevenPct));
    t.appendChild(tb);
    out.appendChild(t);

    out.appendChild(el("p", "label kicker", "Dolar/TL senaryosu"));
    var t2 = el("table"), th = el("thead"), hr = el("tr");
    var cols = ["Dolar/TL"];
    if (r.ccy === "TL") cols.push("Başabaş (" + (r.scenarios[0].breakevenUsdUnit === "ons" ? "ons, $" : r.unit + ", $") + ")");
    else cols.push("Başabaş (TL / " + r.unit + ")");
    if (a !== "bist100") cols.push("Değer (TL)");
    cols.forEach(function (c) { hr.appendChild(el("th", null, c)); });
    th.appendChild(hr); t2.appendChild(th);
    var b2 = el("tbody");
    r.scenarios.forEach(function (s) {
      var tr = el("tr");
      tr.appendChild(el("th", null, num(s.usdtry, 2) + (s.shockPct ? " (+%" + s.shockPct + ")" : " (bugün)")));
      tr.appendChild(el("td", null, r.ccy === "TL" ? num(s.breakevenUsd, 2) : num(s.breakevenTl, 2)));
      if (a !== "bist100") tr.appendChild(el("td", null, s.valueTl == null ? "—" : num(s.valueTl, 0)));
      b2.appendChild(tr);
    });
    t2.appendChild(b2);
    out.appendChild(t2);
    var note = r.ccy === "TL"
      ? "Başabaş sütunu, TL maliyetinin karşılanması için varlığın dolar fiyatının ne olması gerektiğini gösterir" + (A.metal ? " (ons = 31,1035 gram)" : "") + ". Değer sütunu, dolar fiyatı bugünkü gibi kalırsa TL karşılığıdır."
      : "Maliyet dolar cinsinden; kur senaryosu yalnız TL karşılığını değiştirir. Değer sütunu, dolar fiyatı bugünkü gibi kalırsa TL karşılığıdır.";
    if (a === "bist100") note = "BIST 100 TL cinsinden izlenir; başabaş sütunu, endeksin dolar bazında karşılığını gösterir.";
    out.appendChild(el("p", "mute small", note));
  }

  function init(d) {
    P = d && d.prices ? d.prices : null;
    var meta = P ? "Dolar/TL " + num(+P.usdtry, 4) + " · fiyat tarihi " + trDate(P.usdtry_asof) : "Güncel fiyat alınamadı.";
    $("fiyat-meta").textContent = meta;
    $("foot-meta").textContent = "Fiyat tarihi: " + (P ? trDate(P.usdtry_asof) : "—") + " · Kaynak: Piyasa Hava Durumu türetilmiş verisi";
    update();
  }

  ["varlik", "maliyet", "miktar", "hatirla"].forEach(function (id) {
    $(id).addEventListener(id === "varlik" || id === "hatirla" ? "change" : "input", update);
  });
  Array.prototype.forEach.call(document.querySelectorAll('input[name="ccy"]'), function (r) { r.addEventListener("change", update); });
  $("calc").addEventListener("submit", function (e) { e.preventDefault(); });
  load();
  fetch(DATA + "tl.json", { cache: "no-cache", credentials: "omit", referrerPolicy: "no-referrer" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(init)
    .catch(function () { init(null); });
})();
